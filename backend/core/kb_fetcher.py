"""
Auto-fetches knowledge base PDFs on startup.
Downloads only if not already present.
"""
import os
import requests
import logging
from pathlib import Path
from backend.core.config import settings, KB_SOURCES

logger = logging.getLogger(__name__)


def fetch_kb_pdfs():
    """Download all KB PDFs that are missing."""
    kb_dir = Path(settings.kb_dir)
    kb_dir.mkdir(parents=True, exist_ok=True)

    fetched = []
    failed = []

    all_sources = {}
    for role, sources in KB_SOURCES.items():
        for src in sources:
            if src["name"] not in all_sources:
                all_sources[src["name"]] = src

    for name, src in all_sources.items():
        dest = kb_dir / name
        if dest.exists() and dest.stat().st_size > 10_000:
            logger.info(f"[KB] Already exists: {name}")
            fetched.append(name)
            continue

        logger.info(f"[KB] Fetching: {name} from {src['url']}")
        try:
            resp = requests.get(src["url"], timeout=120, stream=True)
            resp.raise_for_status()
            with open(dest, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    f.write(chunk)
            size_mb = dest.stat().st_size / 1_048_576
            logger.info(f"[KB] Downloaded {name} ({size_mb:.1f} MB)")
            fetched.append(name)
        except Exception as e:
            logger.warning(f"[KB] Failed to fetch {name}: {e}")
            # Try fallback if available
            fallback = src.get("fallback_url")
            if fallback:
                try:
                    resp = requests.get(fallback, timeout=120, stream=True)
                    resp.raise_for_status()
                    with open(dest, "wb") as f:
                        for chunk in resp.iter_content(chunk_size=8192):
                            f.write(chunk)
                    fetched.append(name)
                    logger.info(f"[KB] Fallback succeeded for {name}")
                except Exception as e2:
                    logger.error(f"[KB] Fallback also failed for {name}: {e2}")
                    failed.append(name)
            else:
                failed.append(name)

    return {"fetched": fetched, "failed": failed}


def get_kb_files_for_role(role: str) -> list[Path]:
    """Return paths of available KB PDFs for a role."""
    kb_dir = Path(settings.kb_dir)
    sources = KB_SOURCES.get(role, KB_SOURCES.get("AI/ML Engineer", []))
    paths = []
    for src in sources:
        p = kb_dir / src["name"]
        if p.exists() and p.stat().st_size > 1000:
            paths.append(p)
    # Fallback: use any available PDF
    if not paths:
        paths = list(kb_dir.glob("*.pdf"))
    return paths
