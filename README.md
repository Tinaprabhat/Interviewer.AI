# PGAGI Interview Platform

AI-powered role-based candidate screening system with RAG-grounded technical interviews.

## Architecture

```
Resume Upload → Resume Parser (PyMuPDF + LLM)
                        ↓
              Session State Machine
                        ↓
          Dynamic Query Construction (skills + role + step)
                        ↓
         Hybrid Retrieval (ChromaDB dense + BM25 sparse)
                        ↓
     Grounded Question Generation (Groq LLaMA-3.3-70B → Ollama mistral fallback)
                        ↓
              Chat Interview UI (React)
                        ↓
         Answer Evaluation (concept coverage + LLM scoring)
                        ↓
              SQLite Storage → Summary Report
```

## Stack

| Layer | Tech |
|---|---|
| Backend | FastAPI + Python 3.10+ |
| Vector DB | ChromaDB (persistent, local, CPU) |
| Embeddings | all-MiniLM-L6-v2 (CPU, 80MB) |
| LLM Primary | Groq llama-3.3-70b-versatile |
| LLM Fallback | Ollama mistral (local) |
| Database | SQLite |
| Frontend | React + Vite + Tailwind + Zustand |
| PDF parsing | PyMuPDF |
| Sparse retrieval | BM25 (rank-bm25) |

## Setup

### 1. Prerequisites
- Python 3.10+
- Node.js 18+
- (Optional) Ollama with mistral pulled: `ollama pull mistral`
- Groq API key from https://console.groq.com (free tier)

### 2. Configure
```bash
cp .env.example .env
# Edit .env and add GROQ_API_KEY=your_key_here
```

### 3. Start (Windows PowerShell)
```powershell
.\start.ps1
```

Or manually:
```powershell
# Terminal 1 - Backend
pip install -r requirements.txt
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8001 --reload

# Terminal 2 - Frontend
cd frontend
npm install
npm run dev
```

### 4. Open
- App: http://localhost:5173
- API docs: http://localhost:8001/docs

## First Run

On first startup, the system automatically:
1. Downloads ML textbook PDFs (~50MB total) into `data/kb_pdfs/`
2. Downloads embedding model all-MiniLM-L6-v2 (~80MB, cached by HuggingFace)
3. Chunks and ingests PDFs into ChromaDB (once, persistent)

Subsequent runs are instant.

## Interview Flow

| Stage | Questions | Focus |
|---|---|---|
| Warm-up | 2 | Easy fundamentals |
| Core Technical | 4 | Resume skills + role |
| Deep Dive | 3 | Weak areas probing |
| Scenario | 2 | Applied problem-solving |

## Resume + Session Flow

The backend persists parsed resumes, so API testing does not require manually
copying parsed JSON between endpoints.

1. Upload and parse a resume: `POST /api/resume/upload`
2. Use the returned `resume_id` when creating a session:

```json
{
  "role": "AI/ML Engineer",
  "candidate_name": "Candidate",
  "resume_id": "resume-id-from-upload"
}
```

`resume_data` is still accepted for backwards compatibility, but the normal
backend/API flow should use `resume_id`.

## Key Design Decisions

1. **Hybrid Retrieval**: Dense (ChromaDB cosine) + BM25 sparse, combined 70/30 → better precision than either alone
2. **Adaptive State Machine**: Tracks weak/strong areas per session, adjusts question focus
3. **Groq → Ollama Fallback**: No downtime if rate-limited; seamless provider switch
4. **Grounded Generation**: LLM is forced to generate from retrieved context only; citation-aware prompts
5. **CPU-Safe**: all-MiniLM-L6-v2 on CPU, ChromaDB local, no GPU needed
6. **Auto KB Fetch**: PDFs downloaded at startup, no manual setup

## Knowledge Base

Books ingested automatically:
- Machine Learning — Tom Mitchell (primary)
- The Hundred-Page Machine Learning Book — Burkov

Role-to-collection mapping:
- `AI/ML Engineer` → `kb_ai_ml_engineer`
- `Backend Engineer` → `kb_backend_engineer`
- `Data Scientist` → `kb_data_scientist`

## API Endpoints

```
POST /api/resume/upload          → parse resume
GET  /api/resume/{id}            → fetch parsed resume
POST /api/sessions/create        → create interview session using resume_id
GET  /api/sessions/{id}          → get session state
POST /api/interview/{id}/next    → get next question (RAG)
POST /api/interview/{id}/answer  → submit answer + evaluate
GET  /api/sessions/{id}/summary  → final report
GET  /api/sessions/{id}/history  → full Q&A history
GET  /health                     → LLM provider status
```
