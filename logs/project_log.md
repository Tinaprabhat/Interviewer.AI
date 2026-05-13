# PGAGI Interview Platform - Project Log

## Project: AI/ML & Backend Intern Assignment - PGAGI
## Owner: Tina
## Started: 2026-05-12

---

## v1.0.0 - Initial Build (2026-05-12)

### Architecture
- Backend: FastAPI + SQLite + ChromaDB + sentence-transformers (all-MiniLM-L6-v2, CPU)
- LLM: Groq llama-3.3-70b-versatile → fallback Ollama mistral
- KB: Auto-fetch ML PDFs at startup (Tom Mitchell, Burkov, etc.)
- Frontend: React single-page chat UI
- Resume parsing: PyMuPDF

### Files Created
- backend/main.py — FastAPI app entry
- backend/core/config.py — env config
- backend/core/llm_client.py — Groq + Ollama fallback
- backend/core/kb_fetcher.py — auto PDF download
- backend/core/rag_engine.py — ChromaDB + retrieval + chunking
- backend/core/resume_parser.py — PDF resume extraction
- backend/core/interview_engine.py — adaptive state machine
- backend/db/database.py — SQLite setup
- backend/db/models.py — SQLAlchemy models
- backend/api/sessions.py — session endpoints
- backend/api/interview.py — interview endpoints
- backend/api/resume.py — resume upload endpoint
- frontend/src/App.jsx — root
- frontend/src/components/Chat.jsx — chat interface
- frontend/src/components/ResumeUpload.jsx
- frontend/src/components/RoleSelect.jsx
- frontend/src/components/Summary.jsx
- frontend/src/store/interviewStore.js — Zustand store
- requirements.txt
- frontend/package.json
- .env.example
- README.md
- start.sh / start.bat

### Key Decisions
- ChromaDB persistent local (no server needed, CPU-safe)
- all-MiniLM-L6-v2: 80MB, CPU-fast, top-quartile MTEB
- Groq free tier → Ollama fallback (no GPU needed)
- Auto KB fetch: wget PDFs from CDN URLs on first run
- SQLite: zero-infra, single file, sufficient for intern demo
- Adaptive interview: state machine tracks strong/weak areas

---
