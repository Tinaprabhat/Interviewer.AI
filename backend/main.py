import logging
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Ensure project root on path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.core.config import settings, KB_SOURCES, ROLES
from backend.db.database import init_db
from backend.core.kb_fetcher import fetch_kb_pdfs, get_kb_files_for_role
from backend.core.rag_engine import ingest_pdf
from backend.core.llm_client import check_groq_available, check_ollama_available
from backend.api.resume import router as resume_router
from backend.api.sessions import router as sessions_router
from backend.api.interview import router as interview_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("=== PGAGI Interview Platform Starting ===")

    # Init DB
    init_db()
    logger.info("[Startup] Database initialized")

    # Fetch KB PDFs
    logger.info("[Startup] Fetching Knowledge Base PDFs...")
    result = fetch_kb_pdfs()
    logger.info(f"[Startup] KB fetch: {result}")

    # Ingest PDFs into ChromaDB for each role
    logger.info("[Startup] Ingesting KB into ChromaDB...")
    for role in ROLES:
        kb_files = get_kb_files_for_role(role)
        for pdf_path in kb_files:
            try:
                count = ingest_pdf(pdf_path, role)
                if count:
                    logger.info(f"[Startup] Ingested {count} chunks from {pdf_path.name} for {role}")
            except Exception as e:
                logger.error(f"[Startup] Ingestion failed for {pdf_path.name}: {e}")

    # Check LLM availability
    groq_ok = check_groq_available()
    ollama_ok = check_ollama_available()
    logger.info(f"[Startup] Groq available: {groq_ok}, Ollama available: {ollama_ok}")

    if not groq_ok and not ollama_ok:
        logger.warning("[Startup] WARNING: No LLM provider available! Set GROQ_API_KEY or start Ollama.")

    logger.info("=== PGAGI Interview Platform Ready ===")
    yield
    logger.info("=== PGAGI Interview Platform Shutting Down ===")


app = FastAPI(
    title="PGAGI Interview Platform",
    description="AI-powered role-based candidate screening system with RAG",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    allow_origins=[
   "https://interviewer-ai-xi.vercel.app/"
],
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(resume_router)
app.include_router(sessions_router)
app.include_router(interview_router)


@app.get("/")
def root():
    return {
        "service": "PGAGI Interview Platform",
        "version": "1.0.0",
        "status": "running",
    }


@app.get("/health")
def health():
    groq_ok = check_groq_available()
    ollama_ok = check_ollama_available()
    return {
        "status": "ok",
        "groq": groq_ok,
        "ollama": ollama_ok,
        "active_llm": "groq" if groq_ok else ("ollama" if ollama_ok else "none"),
    }


@app.get("/api/roles")
def get_roles():
    return {"roles": ROLES}
