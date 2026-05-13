import copy
import json
import logging
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as DBSession
from sqlalchemy.orm.attributes import flag_modified
from pydantic import BaseModel
from backend.db.database import get_db
from backend.db.models import Session, QARecord, Summary
from backend.core.interview_engine import (
    get_next_question_with_rag,
    evaluate_answer,
    advance_state,
    generate_summary,
)
from backend.core.rag_engine import retrieve, format_context

router = APIRouter(prefix="/api/interview", tags=["interview"])
logger = logging.getLogger(__name__)

# In-memory cache: session_id -> question_data dict.
# Primary store for pending questions — avoids SQLAlchemy JSON-column
# mutation-tracking bugs with SQLite. Process-local; fine for single dev server.
_pending_questions = {}  # type: dict


class AnswerRequest(BaseModel):
    answer: str
    question_data: Optional[dict] = None  # sent by frontend as a second fallback


@router.post("/{session_id}/next")
def get_next_question(session_id: str, db: DBSession = Depends(get_db)):
    """Get the next interview question (grounded via RAG)."""
    logger.info("[Interview] /next requested for session_id=%s", session_id)
    session = db.query(Session).filter(Session.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    state = copy.deepcopy(session.state or {})

    if state.get("is_complete") or session.is_complete:
        return {
            "is_complete": True,
            "message": "Interview complete! Check /api/sessions/{session_id}/summary for results.",
        }

    asked_topics = state.get("asked_topics", [])

    # Generate next question via RAG
    question_data = get_next_question_with_rag(state, asked_topics)

    # Update state
    q_num = state.get("question_number", 0) + 1
    state["question_number"] = q_num
    state["last_topic"] = question_data.get("topic", "")
    asked_topics.append(question_data.get("topic", ""))
    state["asked_topics"] = asked_topics

    # --- Layer 1: in-memory cache (most reliable, no DB issues) ---
    _pending_questions[session_id] = question_data
    logger.info("[Interview] /next cached question in memory for session_id=%s", session_id)

    # --- Layer 2: dedicated TEXT column (DB backup) ---
    session.pending_question = json.dumps(question_data)

    # Also update the state blob (question_number, asked_topics, etc.)
    session.state = state
    flag_modified(session, "state")
    db.add(session)
    db.commit()

    return {
        "session_id": session_id,
        "question_number": q_num,
        "step": question_data.get("step"),
        "difficulty": question_data.get("difficulty"),
        "topic": question_data.get("topic"),
        "question": question_data.get("question"),
        "expected_concepts": question_data.get("expected_concepts", []),
        "llm_provider": question_data.get("_provider"),
        "is_complete": False,
    }


@router.post("/{session_id}/answer")
def submit_answer(session_id: str, req: AnswerRequest, db: DBSession = Depends(get_db)):
    """Submit answer to current question. Returns evaluation + follow-up."""
    logger.info(
        "[Interview] /answer requested for session_id=%s answer_length=%s",
        session_id,
        len(req.answer or ""),
    )
    session = db.query(Session).filter(Session.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    state = copy.deepcopy(session.state or {})

    # Resolve pending question — three independent layers:
    #   1. In-memory cache  (primary — avoids all DB/ORM issues)
    #   2. Frontend-sent question_data  (secondary — avoids DB reads)
    #   3. DB TEXT column  (tertiary — true persistence across restarts)
    pending: Optional[dict] = None

    if session_id in _pending_questions:
        pending = _pending_questions.pop(session_id)
        logger.info("[Interview] /answer using in-memory cache for session_id=%s", session_id)
    elif req.question_data:
        pending = req.question_data
        logger.info("[Interview] /answer using inline question_data for session_id=%s", session_id)
    else:
        pending_str = session.pending_question
        if pending_str:
            pending = json.loads(pending_str)
            logger.info("[Interview] /answer using DB pending_question for session_id=%s", session_id)

    if not pending:
        logger.warning(
            "[Interview] /answer rejected: all three pending-question sources empty for session_id=%s",
            session_id,
        )
        raise HTTPException(
            status_code=400,
            detail="No pending question found. Please call /next first.",
        )

    q_num = state.get("question_number", 1)
    question_text = pending.get("question", "")
    expected_concepts = pending.get("expected_concepts", [])
    role = state.get("role", "AI/ML Engineer")

    # Get context for evaluation (retrieve fresh for grounding)
    chunks = retrieve(pending.get("topic", question_text), role, n_results=4)
    context = format_context(chunks) if chunks else "General ML concepts."

    # Evaluate
    evaluation = evaluate_answer(
        question=question_text,
        answer=req.answer,
        expected_concepts=expected_concepts,
        context=context,
    )

    # Track strong areas
    if evaluation.get("score", 0) >= 7:
        strong_areas = state.get("strong_areas", [])
        topic = pending.get("topic", "")
        if topic and topic not in strong_areas:
            strong_areas.append(topic)
            state["strong_areas"] = strong_areas

    # Save QA record
    qa = QARecord(
        id=str(uuid.uuid4()),
        session_id=session_id,
        question_number=q_num,
        question=question_text,
        answer=req.answer,
        topic=pending.get("topic"),
        difficulty=pending.get("difficulty"),
        step=pending.get("step"),
        expected_concepts=expected_concepts,
        evaluation=evaluation,
        context_used=pending.get("context_used", "")[:500],
        llm_provider=pending.get("_provider"),
    )
    db.add(qa)

    # Advance state machine and clear pending question
    state = advance_state(state, evaluation)
    session.pending_question = None  # clear DB column
    session.state = state
    flag_modified(session, "state")
    session.is_complete = state.get("is_complete", False)
    db.add(session)

    # If complete, generate summary
    if session.is_complete:
        qa_records = (
            db.query(QARecord)
            .filter(QARecord.session_id == session_id)
            .order_by(QARecord.question_number)
            .all()
        )
        qa_history = [
            {
                "question": r.question,
                "answer": r.answer,
                "evaluation": r.evaluation,
            }
            for r in qa_records
        ]
        summary_data = generate_summary(state, qa_history)
        summary = Summary(
            id=str(uuid.uuid4()),
            session_id=session_id,
            data=summary_data,
        )
        db.add(summary)

    db.commit()

    response = {
        "session_id": session_id,
        "question_number": q_num,
        "evaluation": {
            "score": evaluation.get("score"),
            "feedback": evaluation.get("feedback"),
            "quality": evaluation.get("quality"),
            "covered_concepts": evaluation.get("covered_concepts", []),
            "missed_concepts": evaluation.get("missed_concepts", []),
        },
        "follow_up": evaluation.get("follow_up"),
        "is_complete": session.is_complete,
        "current_step": state.get("current_step"),
    }

    if session.is_complete:
        response["message"] = "Interview complete! Summary is ready."

    return response


@router.get("/{session_id}/status")
def get_status(session_id: str, db: DBSession = Depends(get_db)):
    session = db.query(Session).filter(Session.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    state = session.state or {}
    return {
        "session_id": session_id,
        "current_step": state.get("current_step"),
        "question_number": state.get("question_number", 0),
        "is_complete": session.is_complete,
        "weak_areas": state.get("weak_areas", []),
        "strong_areas": state.get("strong_areas", []),
    }
