"""
Interview Engine:
- Adaptive state machine: warmup → core → deep_dive → scenario → closing
- Grounded question generation from RAG context
- Answer evaluation with concept coverage + follow-up
- Session state tracking
"""
import logging
import json
import re
from typing import Optional
from backend.core.llm_client import chat_completion
from backend.core.rag_engine import retrieve, build_dynamic_query, format_context
from backend.core.config import INTERVIEW_STEPS, DIFFICULTY_LEVELS

logger = logging.getLogger(__name__)


QUESTION_COUNT_PER_STEP = {
    "warmup": 1,
    "core": 2,
    "deep_dive": 1,
    "scenario": 1,
    "closing": 0,
}

STEP_DIFFICULTY = {
    "warmup": "easy",
    "core": "medium",
    "deep_dive": "hard",
    "scenario": "hard",
    "closing": "medium",
}


def _get_step_system_prompt(step: str, role: str, candidate_name: str) -> str:
    base = f"""You are an expert technical interviewer conducting a {role} interview for {candidate_name}.
You are grounded: generate questions ONLY from the provided context. Do not hallucinate facts.
Be conversational, professional, and adapt to the candidate's level.
"""
    if step == "warmup":
        return base + "Start warm and friendly. Ask foundational conceptual questions."
    elif step == "core":
        return base + "Ask core technical questions directly relevant to the role and the candidate's skills."
    elif step == "deep_dive":
        return base + "Probe deeper on weaker areas. Ask precise, hard questions that test true understanding."
    elif step == "scenario":
        return base + "Present a realistic scenario or system design problem. Ask applied thinking questions."
    return base


def generate_question(
    session_state: dict,
    context: str,
    asked_topics: list[str],
) -> dict:
    """
    Generate next interview question.
    Returns: {question, topic, difficulty, expected_concepts, follow_up_hint}
    """
    step = session_state.get("current_step", "warmup")
    role = session_state.get("role", "AI/ML Engineer")
    candidate_name = session_state.get("candidate_name", "Candidate")
    skills = session_state.get("skills", [])
    weak_areas = session_state.get("weak_areas", [])
    difficulty = STEP_DIFFICULTY.get(step, "medium")

    asked_str = ", ".join(asked_topics[-5:]) if asked_topics else "none"
    skills_str = ", ".join(skills[:8]) if skills else "general ML/software topics"
    weak_str = ", ".join(weak_areas[:3]) if weak_areas else "none identified yet"

    system = _get_step_system_prompt(step, role, candidate_name)

    prompt = f"""Based on this knowledge base context, generate ONE interview question.

CONTEXT FROM KNOWLEDGE BASE:
{context}

CANDIDATE PROFILE:
- Skills: {skills_str}
- Weak areas so far: {weak_str}
- Recently asked topics: {asked_str}

REQUIREMENTS:
- Difficulty: {difficulty}
- Step: {step}
- Do NOT repeat topics already asked: {asked_str}
- The question must be grounded in the context above
- Be specific, not generic

Return ONLY a JSON object:
{{
  "question": "the interview question text",
  "topic": "single topic keyword",
  "difficulty": "{difficulty}",
  "expected_concepts": ["concept1", "concept2", "concept3"],
  "follow_up_hint": "what to probe if answer is shallow"
}}"""

    messages = [{"role": "user", "content": prompt}]
    try:
        response, provider = chat_completion(messages, system=system, temperature=0.7, max_tokens=600)
        clean = response.strip()
        if clean.startswith("```"):
            clean = re.sub(r"```[a-z]*\n?", "", clean).strip().rstrip("```")
        data = json.loads(clean)
        data["_provider"] = provider
        data["step"] = step
        return data
    except Exception as e:
        logger.error(f"[Interview] Question gen failed: {e}")
        return {
            "question": f"Can you explain a key concept from {skills_str.split(',')[0] if skills else role}?",
            "topic": "general",
            "difficulty": difficulty,
            "expected_concepts": ["understanding", "application"],
            "follow_up_hint": "Ask for an example",
            "step": step,
            "_provider": "fallback",
        }


def evaluate_answer(
    question: str,
    answer: str,
    expected_concepts: list[str],
    context: str,
) -> dict:
    """
    Evaluate candidate answer.
    Returns: {score, feedback, covered_concepts, missed_concepts, follow_up, quality}
    """
    if not answer or len(answer.strip()) < 5:
        return {
            "score": 0,
            "feedback": "No answer provided.",
            "covered_concepts": [],
            "missed_concepts": expected_concepts,
            "follow_up": "Please provide an answer.",
            "quality": "no_answer",
        }

    system = """You are a strict but fair technical interview evaluator.
Evaluate the candidate's answer against expected concepts and the knowledge base context.
Return ONLY valid JSON, no markdown."""

    prompt = f"""Evaluate this interview answer:

QUESTION: {question}

CANDIDATE ANSWER: {answer}

EXPECTED CONCEPTS: {', '.join(expected_concepts)}

KNOWLEDGE BASE CONTEXT (ground truth):
{context[:1500]}

Return JSON:
{{
  "score": <0-10 integer>,
  "feedback": "1-2 sentence constructive feedback",
  "covered_concepts": ["concepts the candidate mentioned"],
  "missed_concepts": ["expected concepts not mentioned"],
  "follow_up": "a follow-up question to probe deeper or clarify",
  "quality": "excellent|good|partial|poor|no_answer"
}}"""

    messages = [{"role": "user", "content": prompt}]
    try:
        response, _ = chat_completion(messages, system=system, temperature=0.2, max_tokens=500)
        clean = response.strip()
        if clean.startswith("```"):
            clean = re.sub(r"```[a-z]*\n?", "", clean).strip().rstrip("```")
        return json.loads(clean)
    except Exception as e:
        logger.error(f"[Interview] Evaluation failed: {e}")
        # Fallback: simple keyword check
        covered = [c for c in expected_concepts if c.lower() in answer.lower()]
        missed = [c for c in expected_concepts if c not in covered]
        score = int((len(covered) / max(len(expected_concepts), 1)) * 10)
        return {
            "score": score,
            "feedback": f"You covered {len(covered)}/{len(expected_concepts)} expected concepts.",
            "covered_concepts": covered,
            "missed_concepts": missed,
            "follow_up": "Can you elaborate further?",
            "quality": "good" if score >= 7 else "partial" if score >= 4 else "poor",
        }


def advance_state(session_state: dict, evaluation: dict) -> dict:
    """
    Update session state based on evaluation result.
    Tracks weak areas, advances step when quota met.
    """
    step = session_state.get("current_step", "warmup")
    step_count = session_state.get("step_question_count", 0) + 1
    quota = QUESTION_COUNT_PER_STEP.get(step, 2)

    # Track weak areas
    missed = evaluation.get("missed_concepts", [])
    topic = session_state.get("last_topic", "")
    if evaluation.get("score", 10) < 5 and topic:
        weak_areas = session_state.get("weak_areas", [])
        if topic not in weak_areas:
            weak_areas.append(topic)
            session_state["weak_areas"] = weak_areas

    # Advance step?
    if step_count >= quota:
        step_idx = INTERVIEW_STEPS.index(step)
        if step_idx + 1 < len(INTERVIEW_STEPS):
            next_step = INTERVIEW_STEPS[step_idx + 1]
            if next_step == "closing":
                # Reached end — mark complete immediately, don't generate closing questions
                session_state["current_step"] = "closing"
                session_state["is_complete"] = True
            else:
                session_state["current_step"] = next_step
                session_state["step_question_count"] = 0
        else:
            session_state["current_step"] = "closing"
            session_state["is_complete"] = True
    else:
        session_state["step_question_count"] = step_count

    return session_state


def generate_summary(session_state: dict, qa_history: list[dict]) -> dict:
    """Generate final interview summary."""
    role = session_state.get("role", "Unknown")
    name = session_state.get("candidate_name", "Candidate")
    scores = [qa.get("evaluation", {}).get("score", 0) for qa in qa_history if qa.get("evaluation")]
    avg_score = sum(scores) / len(scores) if scores else 0
    strong = session_state.get("strong_areas", [])
    weak = session_state.get("weak_areas", [])

    system = "You are a technical interview summarizer. Be concise and fair."
    qa_text = "\n".join(
        [f"Q: {qa['question']}\nA: {qa['answer']}\nScore: {qa.get('evaluation', {}).get('score', 'N/A')}/10"
         for qa in qa_history[:10]]
    )

    prompt = f"""Summarize this {role} technical interview for {name}.

Q&A HISTORY:
{qa_text}

Average score: {avg_score:.1f}/10
Strong areas: {', '.join(strong) or 'None identified'}
Weak areas: {', '.join(weak) or 'None identified'}

Return JSON:
{{
  "overall_rating": "Excellent|Good|Average|Needs Improvement",
  "score_out_of_10": {round(avg_score, 1)},
  "strengths": ["3-4 specific strengths"],
  "improvements": ["3-4 specific areas to improve"],
  "recommendation": "Hire|Consider|Pass",
  "summary_paragraph": "2-3 sentence overall assessment"
}}"""

    messages = [{"role": "user", "content": prompt}]
    try:
        response, _ = chat_completion(messages, system=system, temperature=0.3, max_tokens=600)
        clean = response.strip()
        if clean.startswith("```"):
            clean = re.sub(r"```[a-z]*\n?", "", clean).strip().rstrip("```")
        result = json.loads(clean)
        result["total_questions"] = len(qa_history)
        result["candidate_name"] = name
        result["role"] = role
        return result
    except Exception as e:
        logger.error(f"[Interview] Summary generation failed: {e}")
        return {
            "overall_rating": "Average",
            "score_out_of_10": round(avg_score, 1),
            "strengths": strong or ["Participated in interview"],
            "improvements": weak or ["Practice more technical concepts"],
            "recommendation": "Consider" if avg_score >= 5 else "Pass",
            "summary_paragraph": f"{name} completed the {role} interview with an average score of {avg_score:.1f}/10.",
            "total_questions": len(qa_history),
            "candidate_name": name,
            "role": role,
        }


def get_next_question_with_rag(session_state: dict, asked_topics: list[str]) -> dict:
    """Full pipeline: build query → retrieve → generate question."""
    role = session_state.get("role", "AI/ML Engineer")
    skills = session_state.get("skills", [])
    weak_areas = session_state.get("weak_areas", [])
    step = session_state.get("current_step", "warmup")
    difficulty = STEP_DIFFICULTY.get(step, "medium")

    # Choose focus topic
    focus_topic = None
    if step == "deep_dive" and weak_areas:
        focus_topic = weak_areas[0]
    elif skills:
        # Rotate through skills
        idx = len(asked_topics) % len(skills)
        focus_topic = skills[idx]

    query = build_dynamic_query(role, skills, topic=focus_topic, difficulty=difficulty)
    chunks = retrieve(query, role, n_results=5)
    context = format_context(chunks) if chunks else f"General {role} technical concepts."

    question_data = generate_question(session_state, context, asked_topics)
    question_data["context_used"] = context[:500]  # Store abbreviated context for traceability
    return question_data
