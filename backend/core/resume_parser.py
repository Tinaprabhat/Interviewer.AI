"""
Resume parser: extracts skills, technologies, projects, experience from PDF/text.
Uses PyMuPDF for PDF, LLM for structured extraction.
"""
import re
import logging
from pathlib import Path
import fitz  # PyMuPDF
from backend.core.llm_client import chat_completion

logger = logging.getLogger(__name__)

SKILL_KEYWORDS = [
    "python", "javascript", "typescript", "java", "c++", "go", "rust",
    "tensorflow", "pytorch", "keras", "sklearn", "scikit-learn", "numpy", "pandas",
    "fastapi", "flask", "django", "node", "react", "nextjs",
    "docker", "kubernetes", "aws", "gcp", "azure",
    "sql", "postgresql", "mysql", "mongodb", "redis",
    "machine learning", "deep learning", "nlp", "computer vision",
    "rag", "langchain", "transformers", "huggingface",
    "git", "linux", "rest", "graphql", "microservices",
]


def extract_text_from_pdf(file_bytes: bytes) -> str:
    """Extract raw text from PDF bytes."""
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    text = ""
    for page in doc:
        text += page.get_text()
    doc.close()
    return text


def quick_skill_extract(text: str) -> list[str]:
    """Fast regex-based skill extraction."""
    text_lower = text.lower()
    found = []
    for skill in SKILL_KEYWORDS:
        if skill in text_lower:
            found.append(skill)
    return list(set(found))


def quick_structured_parse(resume_text: str) -> dict:
    """Fast deterministic resume parsing — fallback when LLM is unavailable."""
    lines = [line.strip() for line in resume_text.splitlines() if line.strip()]
    skills = quick_skill_extract(resume_text)

    name = "Candidate"
    for line in lines[:8]:
        if not re.search(r"@|http|www\.|skills?:|projects?:|education:|experience:", line, re.I):
            words = line.split()
            if 1 <= len(words) <= 5 and not any(char.isdigit() for char in line):
                name = line
                break

    projects = []
    education = ""
    for line in lines:
        if re.match(r"projects?:", line, re.I):
            projects.append(re.sub(r"^projects?:\s*", "", line, flags=re.I))
        elif re.match(r"education:", line, re.I):
            education = re.sub(r"^education:\s*", "", line, flags=re.I)

    return {
        "name": name,
        "skills": skills,
        "technologies": [],  # avoid duplicating skills into a second list
        "domains": _infer_domains(skills),
        "experience_years": "0",
        "projects": projects,
        "education": education,
        "strengths": skills[:5],
        "weak_areas": [],
        "_provider": "deterministic",
    }


def parse_resume_with_llm(resume_text: str) -> dict:
    """Use LLM to extract structured resume data."""
    system = """You are a resume parser. Extract structured information from the resume text.
Return ONLY a JSON object with these fields:
{
  "name": "candidate name or Unknown",
  "skills": ["list of technical skills"],
  "technologies": ["specific frameworks, libraries, tools"],
  "domains": ["ML, Backend, Frontend, DevOps, etc."],
  "experience_years": "estimated years or 0",
  "projects": ["brief project descriptions"],
  "education": "degree and institution",
  "strengths": ["inferred strong areas based on resume"],
  "weak_areas": []
}
Return only valid JSON, no markdown, no explanation."""

    messages = [{"role": "user", "content": f"Parse this resume:\n\n{resume_text[:4000]}"}]

    try:
        response, provider = chat_completion(messages, system=system, temperature=0.1, max_tokens=800)
        import json
        # Clean potential markdown
        clean = response.strip()
        if clean.startswith("```"):
            clean = re.sub(r"```[a-z]*\n?", "", clean).strip().rstrip("```")
        data = json.loads(clean)
        data["_provider"] = provider
        return data
    except Exception as e:
        logger.warning(f"[Resume] LLM parse failed: {e}. Using quick extraction.")
        return quick_structured_parse(resume_text)


def _infer_domains(skills: list[str]) -> list[str]:
    domains = []
    ml_skills = {"machine learning", "deep learning", "pytorch", "tensorflow", "sklearn", "nlp", "rag"}
    backend_skills = {"fastapi", "flask", "django", "postgresql", "redis", "docker"}
    if any(s in ml_skills for s in skills):
        domains.append("AI/ML")
    if any(s in backend_skills for s in skills):
        domains.append("Backend")
    return domains or ["General"]


def parse_resume(file_bytes: bytes, filename: str) -> dict:
    """Main entry: parse resume from uploaded file bytes."""
    if filename.lower().endswith(".pdf"):
        text = extract_text_from_pdf(file_bytes)
    else:
        text = file_bytes.decode("utf-8", errors="ignore")

    if len(text.strip()) < 50:
        return {
            "name": "Candidate",
            "skills": [],
            "technologies": [],
            "domains": [],
            "experience_years": "0",
            "projects": [],
            "education": "",
            "strengths": [],
            "weak_areas": [],
            "raw_text": text,
        }

    # LLM parser is primary; quick_structured_parse is its internal fallback.
    parsed = parse_resume_with_llm(text)
    parsed["raw_text"] = text[:3000]
    return parsed
