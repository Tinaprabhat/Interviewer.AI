"""
LLM Client: Groq primary → Ollama (mistral) fallback.
Both expose identical chat interface.
"""
import logging
import httpx
from backend.core.config import settings

logger = logging.getLogger(__name__)


def _call_groq(messages: list[dict], system: str = None, temperature: float = 0.7, max_tokens: int = 1024) -> str:
    if not settings.groq_api_key:
        raise ValueError("Groq API key not configured")

    msgs = []
    if system:
        msgs.append({"role": "system", "content": system})
    msgs.extend(messages)

    payload = {
        "model": settings.groq_model,
        "messages": msgs,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    headers = {
        "Authorization": f"Bearer {settings.groq_api_key}",
        "Content-Type": "application/json",
    }

    with httpx.Client(timeout=30.0) as client:
        response = client.post(
            "https://api.groq.com/openai/v1/chat/completions",
            json=payload,
            headers=headers,
        )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]


def _call_ollama(messages: list[dict], system: str = None, temperature: float = 0.7, max_tokens: int = 1024) -> str:
    """Call local Ollama API."""
    url = f"{settings.ollama_base_url}/api/chat"

    msgs = []
    if system:
        msgs.append({"role": "system", "content": system})
    msgs.extend(messages)

    payload = {
        "model": settings.ollama_model,
        "messages": msgs,
        "stream": False,
        "options": {
            "temperature": temperature,
            "num_predict": max_tokens,
        },
    }

    with httpx.Client(timeout=30.0) as client:
        resp = client.post(url, json=payload)
        resp.raise_for_status()
        data = resp.json()
        return data["message"]["content"]


def chat_completion(
    messages: list[dict],
    system: str = None,
    temperature: float = 0.7,
    max_tokens: int = 1024,
) -> tuple[str, str]:
    """
    Returns (response_text, provider_used).
    Tries Groq first, falls back to Ollama.
    """
    # Try Groq
    if settings.groq_api_key:
        try:
            text = _call_groq(messages, system=system, temperature=temperature, max_tokens=max_tokens)
            return text, "groq"
        except Exception as e:
            logger.warning(f"[LLM] Groq failed: {e}. Falling back to Ollama.")

    # Fallback: Ollama
    try:
        text = _call_ollama(messages, system=system, temperature=temperature, max_tokens=max_tokens)
        return text, "ollama"
    except Exception as e:
        logger.error(f"[LLM] Ollama also failed: {e}")
        raise RuntimeError(f"Both LLM providers failed. Last error: {e}")


def check_ollama_available() -> bool:
    try:
        with httpx.Client(timeout=5.0) as client:
            resp = client.get(f"{settings.ollama_base_url}/api/tags")
            return resp.status_code == 200
    except Exception:
        return False


def check_groq_available() -> bool:
    return bool(settings.groq_api_key)
