from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from sqlalchemy.orm import Session as DBSession
from backend.db.database import get_db
from backend.db.models import ParsedResume
from backend.core.resume_parser import parse_resume

router = APIRouter(prefix="/api/resume", tags=["resume"])


@router.post("/upload")
async def upload_resume(file: UploadFile = File(...), db: DBSession = Depends(get_db)):
    """Parse uploaded resume (PDF or TXT) and return structured data."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    allowed = {".pdf", ".txt", ".md"}
    suffix = "." + file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if suffix not in allowed:
        raise HTTPException(status_code=400, detail=f"File type {suffix} not supported. Use PDF or TXT.")

    content = await file.read()
    if len(content) > 10 * 1024 * 1024:  # 10MB limit
        raise HTTPException(status_code=400, detail="File too large (max 10MB)")

    parsed = parse_resume(content, file.filename)
    resume = ParsedResume(
        filename=file.filename,
        candidate_name=parsed.get("name") or "Candidate",
        parsed_data=parsed,
    )
    db.add(resume)
    db.commit()
    db.refresh(resume)

    return {
        "success": True,
        "resume_id": resume.id,
        "filename": file.filename,
        "parsed": parsed,
    }


@router.get("/{resume_id}")
def get_parsed_resume(resume_id: str, db: DBSession = Depends(get_db)):
    """Fetch a previously parsed resume by id."""
    resume = db.query(ParsedResume).filter(ParsedResume.id == resume_id).first()
    if not resume:
        raise HTTPException(status_code=404, detail="Parsed resume not found")

    return {
        "resume_id": resume.id,
        "filename": resume.filename,
        "candidate_name": resume.candidate_name,
        "parsed": resume.parsed_data,
    }
