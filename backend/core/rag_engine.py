
"""
RAG Engine:
- Ingests KB PDFs into ChromaDB (persistent, CPU)
- Hybrid retrieval: dense (ChromaDB cosine) + BM25 sparse
- Builds dynamic queries from resume + role
- Returns grounded context for question generation
"""
import re
import logging
import hashlib
from pathlib import Path
from typing import Optional
import fitz  # PyMuPDF
import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
from rank_bm25 import BM25Okapi
from backend.core.config import settings

logger = logging.getLogger(__name__)

_chroma_client = None
_embedding_fn = None
_bm25_index: dict = {}  # collection_name -> (BM25, chunks)


def _get_embedding_fn():
    global _embedding_fn
    if _embedding_fn is None:
        _embedding_fn = SentenceTransformerEmbeddingFunction(
            model_name="all-MiniLM-L6-v2",
            device="cpu",
        )
    return _embedding_fn


def _get_chroma_client():
    global _chroma_client
    if _chroma_client is None:
        persist_dir = Path(settings.chroma_persist_dir)
        persist_dir.mkdir(parents=True, exist_ok=True)
        _chroma_client = chromadb.PersistentClient(path=str(persist_dir))
    return _chroma_client


def _chunk_text(text: str, chunk_size: int = 500, overlap: int = 100) -> list[str]:
    """
    Recursive semantic chunking:
    1. Split on double newlines (paragraph boundaries)
    2. If chunk too big, split on single newline
    3. If still too big, split on sentence boundaries
    4. Fall back to word-level splitting
    """
    chunks = []
    paragraphs = re.split(r"\n\n+", text)

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        if len(para.split()) <= chunk_size:
            if len(para.split()) >= 20:  # skip tiny fragments
                chunks.append(para)
        else:
            # Split on sentences
            sentences = re.split(r"(?<=[.!?])\s+", para)
            current = []
            current_len = 0
            for sent in sentences:
                sent_words = len(sent.split())
                if current_len + sent_words > chunk_size and current:
                    chunks.append(" ".join(current))
                    # Overlap: keep last portion
                    overlap_words = " ".join(current).split()[-overlap:]
                    current = [" ".join(overlap_words)]
                    current_len = len(overlap_words)
                current.append(sent)
                current_len += sent_words
            if current and current_len >= 20:
                chunks.append(" ".join(current))

    return chunks


def _get_pdf_hash(path: Path) -> str:
    h = hashlib.md5()
    with open(path, "rb") as f:
        h.update(f.read(8192))  # hash first 8KB
    return h.hexdigest()[:12]


def ingest_pdf(pdf_path: Path, role: str) -> int:
    """Ingest a PDF into the ChromaDB collection for the given role."""
    collection_name = f"kb_{role.lower().replace('/', '_').replace(' ', '_')}"
    client = _get_chroma_client()
    ef = _get_embedding_fn()

    collection = client.get_or_create_collection(
        name=collection_name,
        embedding_function=ef,
        metadata={"hnsw:space": "cosine"},
    )

    # Check if already ingested (by PDF hash in metadata)
    pdf_hash = _get_pdf_hash(pdf_path)
    existing = collection.get(where={"source_hash": pdf_hash}, limit=1)
    if existing and existing["ids"]:
        logger.info(f"[RAG] Already ingested {pdf_path.name} for role {role}")
        return 0

    # Extract text
    doc = fitz.open(str(pdf_path))
    full_text = ""
    for page in doc:
        full_text += page.get_text() + "\n\n"
    doc.close()

    if len(full_text.strip()) < 100:
        logger.warning(f"[RAG] PDF {pdf_path.name} extracted very little text")
        return 0

    chunks = _chunk_text(full_text, chunk_size=400, overlap=80)
    logger.info(f"[RAG] {pdf_path.name}: {len(chunks)} chunks")

    # Batch upsert
    batch_size = 50
    total = 0
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i: i + batch_size]
        ids = [f"{pdf_hash}_{i + j}" for j in range(len(batch))]
        metadatas = [
            {
                "source": pdf_path.name,
                "source_hash": pdf_hash,
                "chunk_idx": i + j,
                "role": role,
            }
            for j in range(len(batch))
        ]
        collection.upsert(ids=ids, documents=batch, metadatas=metadatas)
        total += len(batch)

    logger.info(f"[RAG] Ingested {total} chunks from {pdf_path.name} into {collection_name}")
    return total


def _build_bm25_index(collection_name: str):
    """Build in-memory BM25 index from ChromaDB collection."""
    global _bm25_index
    client = _get_chroma_client()
    ef = _get_embedding_fn()
    try:
        collection = client.get_collection(collection_name, embedding_function=ef)
        all_docs = collection.get()
        documents = all_docs["documents"] or []
        ids = all_docs["ids"] or []
        if not documents:
            return
        tokenized = [doc.lower().split() for doc in documents]
        bm25 = BM25Okapi(tokenized)
        _bm25_index[collection_name] = (bm25, documents, ids)
        logger.info(f"[RAG] BM25 index built for {collection_name}: {len(documents)} docs")
    except Exception as e:
        logger.warning(f"[RAG] BM25 index failed for {collection_name}: {e}")


def retrieve(
    query: str,
    role: str,
    n_results: int = 6,
    use_bm25: bool = True,
) -> list[dict]:
    """
    Hybrid retrieval: dense (ChromaDB) + BM25 sparse.
    Returns top chunks with scores.
    """
    collection_name = f"kb_{role.lower().replace('/', '_').replace(' ', '_')}"
    client = _get_chroma_client()
    ef = _get_embedding_fn()

    try:
        collection = client.get_collection(collection_name, embedding_function=ef)
    except Exception:
        logger.warning(f"[RAG] Collection {collection_name} not found. Ingestion may not have run.")
        return []

    # Dense retrieval
    dense_results = collection.query(
        query_texts=[query],
        n_results=min(n_results * 2, 20),
    )

    dense_docs = dense_results["documents"][0] if dense_results["documents"] else []
    dense_ids = dense_results["ids"][0] if dense_results["ids"] else []
    dense_metas = dense_results["metadatas"][0] if dense_results["metadatas"] else []
    dense_distances = dense_results["distances"][0] if dense_results["distances"] else []

    # Score map: id -> {doc, meta, dense_score}
    score_map = {}
    for doc, doc_id, meta, dist in zip(dense_docs, dense_ids, dense_metas, dense_distances):
        score_map[doc_id] = {
            "document": doc,
            "metadata": meta,
            "dense_score": 1.0 - dist,  # cosine similarity
            "bm25_score": 0.0,
        }

    # BM25 retrieval
    if use_bm25:
        if collection_name not in _bm25_index:
            _build_bm25_index(collection_name)

        if collection_name in _bm25_index:
            bm25, all_docs, all_ids = _bm25_index[collection_name]
            tokenized_query = query.lower().split()
            scores = bm25.get_scores(tokenized_query)

            top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[: n_results * 2]
            max_bm25 = max(scores) if max(scores) > 0 else 1.0

            for idx in top_indices:
                doc_id = all_ids[idx]
                normalized_score = scores[idx] / max_bm25
                if doc_id in score_map:
                    score_map[doc_id]["bm25_score"] = normalized_score
                # Don't add new docs from BM25 not in dense results to keep it tight

    # Combine scores: 0.7 dense + 0.3 BM25
    for doc_id, data in score_map.items():
        data["final_score"] = 0.7 * data["dense_score"] + 0.3 * data["bm25_score"]

    # Sort and filter
    ranked = sorted(score_map.values(), key=lambda x: x["final_score"], reverse=True)
    top = ranked[:n_results]

    # Filter low-confidence results
    threshold = 0.2
    filtered = [r for r in top if r["final_score"] >= threshold]

    return filtered if filtered else top[:3]  # Always return at least 3


def build_dynamic_query(
    role: str,
    skills: list[str],
    topic: Optional[str] = None,
    difficulty: str = "medium",
) -> str:
    """Build retrieval query from resume + role context."""
    base = f"{role} interview questions"
    if topic:
        base = f"{topic} concepts {role}"
    if skills:
        skill_str = ", ".join(skills[:5])
        base = f"{base} {skill_str}"
    if difficulty == "hard":
        base += " advanced theoretical"
    elif difficulty == "easy":
        base += " fundamentals basics"
    return base


def format_context(chunks: list[dict], max_chars: int = 3000) -> str:
    """Format retrieved chunks into context string for LLM."""
    context_parts = []
    total = 0
    for chunk in chunks:
        doc = chunk["document"]
        if total + len(doc) > max_chars:
            break
        context_parts.append(doc)
        total += len(doc)
    return "\n\n---\n\n".join(context_parts)
