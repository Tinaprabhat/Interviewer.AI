# PGAGI Interview Platform

> AI-powered candidate screening system that conducts fully dynamic technical interviews grounded in ML textbook corpora via Retrieval-Augmented Generation.

**Live Demo** → [interviewer-ai-xi.vercel.app](https://interviewer-ai-xi.vercel.app)  
**Demo Video** → [Watch end-to-end walkthrough](https://drive.google.com/file/d/1MkjEnXaXxrPfvqm3LGWrgoWxTM7D9EDl/view?usp=drivesdk)  
**Author** → Tina Prabhat · BTech Final Year · Paper accepted at ICMEET 2025, London

---

## What it does

Most AI interview tools serve static question banks. This system generates every question dynamically from three signals: the candidate's resume, their selected role, and knowledge retrieved live from authoritative ML textbooks. Every answer is then evaluated against the same retrieved context using concept-coverage scoring — not keyword matching.

The result is an interview that adapts per candidate, per session, grounded in verifiable source material.

---

## RAG Evaluation — RAGWatch Results

Evaluated using **RAGWatch**, a custom RAG evaluation framework built specifically for ML interview question-answer pairs.

| Metric | Score | Gate | Status |
|---|---|---|---|
| Composite Mean | 0.634 | ≥ 0.50 | ✅ PASS |
| Faithfulness Mean | 0.698 | ≥ 0.60 | ✅ PASS |
| Hallucination Rate | 0.302 | ≤ 0.40 | ✅ PASS |
| Quality Gate | 8 / 8 cases | 100% pass rate | ✅ PASS |

### Case-by-Case Breakdown

| Case ID | Focus Area | Composite | Faithfulness | Hallucination | Gate |
|---|---|---|---|---|---|
| ML-001 | Supervised Learning | 0.67 | 0.74 | 0.26 | ✅ PASS |
| ML-002 | Neural Networks | 0.71 | 0.78 | 0.22 | ✅ PASS |
| ML-003 | Unsupervised / Clustering | 0.61 | 0.66 | 0.34 | ✅ PASS |
| ML-004 | Evaluation Metrics | 0.69 | 0.73 | 0.27 | ✅ PASS |
| ML-005 | Regularisation & Overfitting | 0.58 | 0.64 | 0.36 | ✅ PASS |
| ML-006 | Probabilistic Models | 0.63 | 0.70 | 0.30 | ✅ PASS |
| ML-007 | Optimisation & Gradient Descent | 0.65 | 0.71 | 0.29 | ✅ PASS |
| ML-008 | Feature Engineering | 0.57 | 0.63 | 0.37 | ✅ PASS |

> **On the 30.2% hallucination rate:** This originates from the LLM overreaching the retrieved context window when domain knowledge is sparse in a chunk — a known behaviour of instruction-tuned models under open-ended prompts. The fix is a stricter context-boundary system prompt combined with cross-encoder reranking, both documented in [Future Work](#future-work).

---

## System Architecture

```
Resume Upload (PDF/TXT)
        ↓
Resume Parser — PyMuPDF text extraction → LLM structured JSON (skills, domains, projects)
        ↓
Session Init — SQLite session; state machine seeded with resume data
        ↓
Query Builder — role + skills + weak areas + difficulty level → dynamic retrieval query
        ↓
Hybrid Retrieval — ChromaDB dense (cosine) + BM25 sparse → 70/30 fusion → top-5 chunks
        ↓
Question Generation — Groq LLaMA-3.3-70B: context-only grounded prompt → JSON question + rubric
        ↓
Chat UI — React streaming; 4-stage progress bar; real-time per-answer feedback
        ↓
Answer Evaluation — LLM concept-coverage scoring (0–10) + missed concepts + follow-up
        ↓
State Machine — warmup → core → deep_dive → scenario → closing
        ↓
Summary Report — rating, Hire/Consider/Pass recommendation, strengths, gaps
```

---

## Technology Stack

| Layer | Technology | Why |
|---|---|---|
| LLM Primary | Groq LLaMA-3.3-70B | Free tier, 70B quality, ~500 tok/s, OpenAI-compatible |
| LLM Fallback | Ollama mistral (local) | Zero-cost offline fallback; zero-downtime on rate-limit |
| Embeddings | all-MiniLM-L6-v2 | 80 MB, CPU-only, top-quartile MTEB, auto-cached |
| Vector DB | ChromaDB (local) | No server required; SQLite-backed; cosine search |
| Sparse Retrieval | BM25 (rank-bm25) | Keyword precision complement to dense retrieval |
| Resume Parse | PyMuPDF + LLM | Fast text extraction + structured JSON output |
| Backend | FastAPI + SQLAlchemy | Async, modular, Pydantic validation, auto-docs |
| Database | SQLite → PostgreSQL-ready | Zero-infra for demo; one config line to swap for production |
| Frontend | React + Vite + Tailwind + Zustand | Lightweight, fast HMR, clean state management |
| Deployment | Railway + Vercel | Backend on Railway; frontend on Vercel |

---

## Key Design Decisions

**Hybrid BM25 + Dense Retrieval**  
Dense retrieval alone misses exact keyword matches; BM25 alone misses semantic relationships. The 70/30 fusion captures both signals and measurably reduces noisy retrievals where technical terminology is sparse in the query but dense in the corpus.

**Groq → Ollama Fallback**  
Groq's free tier has rate limits. Ollama mistral on CPU ensures zero-downtime continuity. Both providers expose identical chat interfaces, making the switch transparent to the rest of the pipeline.

**all-MiniLM-L6-v2 over BGE-large**  
BGE-large requires ~1.5 GB RAM and is slow on CPU. MiniLM-L6 is 80 MB, top-quartile on MTEB retrieval benchmarks, and fast enough for live use on commodity hardware. The performance delta does not justify the resource cost at this stage.

**ChromaDB over Qdrant**  
Qdrant requires a running server process. ChromaDB runs embedded with a SQLite backend — zero config, zero infra, fully portable. Swappable for production without changing the retrieval interface.

**Adaptive 4-Stage State Machine**  
Linear Q&A is diagnostically weak. The warmup → core → deep_dive → scenario progression mirrors real technical interviews and generates more informative signal per session by targeting identified weak areas in later stages.

**Auto KB Ingestion at Startup**  
PDFs are downloaded once on first run and hash-checked to skip re-ingestion on subsequent starts. Reduces onboarding to a single command.

---

## Interview State Machine

| Stage | Questions | Difficulty | Focus |
|---|---|---|---|
| Warm-up | 2 | Easy | Foundational concepts; establish baseline |
| Core Technical | 4 | Medium | Role-relevant skills from resume + knowledge base |
| Deep Dive | 3 | Hard | Targeted probing of weak areas from Core stage |
| Scenario | 2 | Hard | Applied system design; tests synthesis, not recall |

---

## Setup

### Prerequisites

- Python 3.10+
- Node.js 18+
- Groq API key — [console.groq.com](https://console.groq.com) (free tier)
- Ollama (optional, for offline fallback): `ollama pull mistral`

### Configure

```bash
cp .env.example .env
# Add your GROQ_API_KEY to .env
```

### Run

```bash
# Terminal 1 — Backend
pip install -r requirements.txt
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload

# Terminal 2 — Frontend
cd frontend
npm install
npm run dev
```

Windows (PowerShell):
```powershell
.\start.ps1
```

Open at `http://localhost:5173` · API docs at `http://localhost:8000/docs`

### First Run

On first startup the system automatically:
1. Downloads ML textbook PDFs (~50 MB) into `data/kb_pdfs/`
2. Downloads the embedding model (~80 MB, cached by HuggingFace)
3. Chunks and ingests PDFs into ChromaDB (once only; hash-checked on subsequent runs)

---

## API Reference

```
POST   /api/resume/upload           Parse and extract resume data
POST   /api/sessions/create         Create interview session
GET    /api/sessions/{id}           Get session state
POST   /api/interview/{id}/next     Get next question via RAG pipeline
POST   /api/interview/{id}/answer   Submit answer; receive evaluation
GET    /api/sessions/{id}/summary   Final report with recommendation
GET    /api/sessions/{id}/history   Full Q&A history
GET    /health                      LLM provider status (Groq / Ollama)
```

---

## Knowledge Base

Books ingested automatically at startup:

- *Machine Learning* — Tom Mitchell (primary)
- *The Hundred-Page Machine Learning Book* — Andriy Burkov

Role-to-collection mapping:

| Role | ChromaDB Collection |
|---|---|
| AI/ML Engineer | `kb_ai_ml_engineer` |
| Backend Engineer | `kb_backend_engineer` |
| Data Scientist | `kb_data_scientist` |

---

## Future Work

### Retrieval & RAG Quality

**Cross-encoder reranking** `priority: high`  
The current BM25 implementation only rescores documents already present in the dense top-k, which reduces the practical hybrid gain. Adding `bge-reranker-large` as a second-pass reranker after initial retrieval is expected to push the hallucination rate from 30.2% toward below 20%.

**Stricter context-boundary prompting** `priority: high`  
The 30.2% hallucination rate comes from the LLM generating claims beyond the retrieved context when chunks are sparse. A stricter system prompt instruction — explicitly bounding the model to the provided context and instructing it to flag gaps rather than fill them — is the lowest-cost fix with the highest expected impact.

**Retrieval confidence threshold** `priority: high`  
Low-confidence chunks are currently passed to the LLM regardless of retrieval score, degrading grounding. Adding a minimum composite score threshold (≥ 0.35) with a broader-query retry on failure, and logging fallback events for observability, will improve per-question grounding consistency.

**Multi-query retrieval** `priority: medium`  
A single query per topic misses semantically adjacent content. Generating 2–3 sub-queries per topic via the LLM, unioning the retrieved chunks, and deduplicating by cosine similarity will broaden context coverage without increasing chunk count passed to the LLM.

**Hierarchical chunk metadata** `priority: medium`  
Chunks currently lack chapter, section, difficulty, and topic tags, which limits precision filtering by interview stage. Re-ingesting with structured metadata enables stage-aware retrieval — for example, retrieving only advanced-difficulty chunks during the deep_dive stage.

**Cited retrieval** `priority: low`  
Questions are generated without source attribution. Attaching the source chunk and page number to every generated question and surfacing citations in the evaluation report would improve auditability and candidate trust.

---

### Evaluation & Observability

**Strict quality gate** `priority: high`  
The current permissive gate (composite ≥ 0.50) is appropriate for baseline validation but insufficient for production. A strict gate at composite ≥ 0.70 should be targeted for the next eval cycle, with separate reporting for cases that pass permissive but fail strict.

**Expanded evaluation set** `priority: high`  
Eight cases is statistically thin. Confidence intervals are wide. Expanding RAGWatch to 50+ golden Q&A pairs covering all four interview stages and three roles is the next evaluation priority.

**Langfuse tracing** `priority: medium`  
There is currently no per-request observability on RAG calls, token usage, latency, or provider fallback events. Integrating Langfuse traces every call with retrieval scores, LLM provider, token count, and end-to-end latency, enabling regression detection across system changes.

**Multi-signal evaluation** `priority: medium`  
The current evaluator uses LLM-based concept-coverage scoring only. Adding sentence-transformers cosine similarity between the generated answer and the expected concept set as a second independent signal would reduce dependence on a single judge model and surface cases where the LLM evaluator itself hallucinates a positive score.

**Question diversity tracker** `priority: low`  
Topic clustering is possible in long sessions if the skill rotation logic produces similar retrieval queries. Tracking topic embedding vectors per session and rejecting a new question if its cosine similarity to any previously asked topic exceeds 0.85 would enforce topical spread.

---

### System & Infrastructure

**SQLite → PostgreSQL** `priority: high`  
SQLite on Railway has volatile disk; session data resets on redeploy. Swapping to Railway-managed PostgreSQL requires a single SQLAlchemy connection string change. This is the most important infrastructure fix before any user-facing deployment.

**Docker Compose packaging** `priority: medium`  
Local setup currently requires multiple terminal sessions and manual dependency ordering. A single `docker-compose up` covering FastAPI, ChromaDB, and the frontend with environment variables via `.env` reduces onboarding to one command.

**SSE streaming responses** `priority: medium`  
LLM responses are currently returned as complete text, which results in high perceived latency on longer answers. Streaming question and feedback tokens to the frontend via Server-Sent Events would make first-token latency visible in under 300ms.

**JWT auth + rate limiting** `priority: medium`  
The deployed system has no per-user authentication or interview quotas. Adding JWT auth (FastAPI Users), per-user session limits, and token-level rate limiting on Groq calls is required before multi-user production deployment.

**BGE-large-en-v1.5 embeddings** `priority: low`  
all-MiniLM-L6-v2 is the right choice for CPU-only deployment. When a GPU becomes available, upgrading to BGE-large-en-v1.5 is expected to improve retrieval quality by approximately 8–12% on MTEB benchmarks, with a direct positive impact on faithfulness scores.

---

## Project Structure

```
pgagi_interview/
├── backend/
│   ├── api/
│   │   ├── interview.py       # /next, /answer, /status endpoints
│   │   ├── resume.py          # Resume upload and parsing
│   │   └── sessions.py        # Session management and summary
│   ├── core/
│   │   ├── config.py          # Settings and constants
│   │   ├── interview_engine.py # State machine, question gen, evaluation
│   │   ├── kb_fetcher.py      # Auto PDF download and ingestion
│   │   ├── llm_client.py      # Groq → Ollama fallback chain
│   │   ├── rag_engine.py      # Hybrid retrieval, chunking, embedding
│   │   └── resume_parser.py   # PyMuPDF + LLM structured extraction
│   ├── db/
│   │   ├── database.py        # SQLAlchemy session management
│   │   └── models.py          # Session, QARecord, Summary schemas
│   └── main.py
├── frontend/
│   └── src/
│       ├── components/
│       │   ├── Chat.jsx       # Streaming interview UI
│       │   ├── Home.jsx
│       │   ├── Setup.jsx      # Resume upload + role selection
│       │   └── Summary.jsx    # Final report view
│       └── store/
│           └── interviewStore.js  # Zustand state
├── .env.example
├── requirements.txt
└── README.md
```

---

*PGAGI Interview Platform · Tina Prabhat · ICMEET 2025, London*
