import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as DBSession
from pydantic import BaseModel
from typing import Optional
from backend.db.database import get_db
from backend.db.models import Session, QARecord, Summary, ParsedResume
from backend.core.config import ROLES, INTERVIEW_STEPS

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


class CreateSessionRequest(BaseModel):
    role: str
    candidate_name: Optional[str] = "Candidate"
    resume_id: Optional[str] = None
    resume_data: Optional[dict] = None


@router.post("/create")
def create_session(req: CreateSessionRequest, db: DBSession = Depends(get_db)):
    if req.role not in ROLES:
        raise HTTPException(status_code=400, detail=f"Invalid role. Choose from: {ROLES}")

    # Prefer inline resume_data; fall back to DB lookup via resume_id.
    # The frontend always sends both, so the DB lookup is a safety net.
    resume = req.resume_data or {}
    if not resume and req.resume_id:
        parsed_resume = db.query(ParsedResume).filter(ParsedResume.id == req.resume_id).first()
        if parsed_resume:
            resume = parsed_resume.parsed_data or {}

    session_id = str(uuid.uuid4())

    # Merge skills + technologies but deduplicate (LLM parser may return overlapping lists;
    # the deterministic fallback always returns technologies=[] so this is safe either way).
    raw_skills = resume.get("skills", []) + resume.get("technologies", [])
    merged_skills = list(dict.fromkeys(s for s in raw_skills if s))  # preserve order, drop dupes

    initial_state = {
        "current_step": "warmup",
        "step_question_count": 0,
        "question_number": 0,
        "role": req.role,
        "candidate_name": req.candidate_name or resume.get("name", "Candidate"),
        "skills": merged_skills,
        "domains": resume.get("domains", []),
        "weak_areas": [],
        "strong_areas": [],
        "asked_topics": [],
        "is_complete": False,
    }

    session = Session(
        id=session_id,
        role=req.role,
        candidate_name=initial_state["candidate_name"],
        resume_data=resume,
        state=initial_state,
        is_complete=False,
    )
    db.add(session)
    db.commit()

    return {
        "session_id": session_id,
        "candidate_name": initial_state["candidate_name"],
        "role": req.role,
        "status": "created",
        "message": f"Interview session created for {initial_state['candidate_name']} ({req.role})",
    }


@router.get("/{session_id}")
def get_session(session_id: str, db: DBSession = Depends(get_db)):
    session = db.query(Session).filter(Session.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return {
        "session_id": session.id,
        "role": session.role,
        "candidate_name": session.candidate_name,
        "state": session.state,
        "is_complete": session.is_complete,
    }


@router.get("/{session_id}/history")
def get_history(session_id: str, db: DBSession = Depends(get_db)):
    records = (
        db.query(QARecord)
        .filter(QARecord.session_id == session_id)
        .order_by(QARecord.question_number)
        .all()
    )
    return {
        "session_id": session_id,
        "total": len(records),
        "history": [
            {
                "question_number": r.question_number,
                "question": r.question,
                "answer": r.answer,
                "topic": r.topic,
                "difficulty": r.difficulty,
                "step": r.step,
                "evaluation": r.evaluation,
            }
            for r in records
        ],
    }


@router.get("/{session_id}/summary")
def get_summary(session_id: str, db: DBSession = Depends(get_db)):
    summary = db.query(Summary).filter(Summary.session_id == session_id).first()
    if not summary:
        raise HTTPException(status_code=404, detail="Summary not ready. Complete the interview first.")
    return summary.data


