"""Local LLM generation through the Ollama HTTP API.

Ollama is used rather than loading weights in-process so that model pulling,
quantisation and memory residency stay outside the application. The daemon
listens on loopback only; nothing leaves the machine.
"""
from __future__ import annotations

import httpx

from ..config import settings
from ..models import RetrievedChunk
from .prompt_builder import build_prompt


def generate_answer(query: str, sources: list[RetrievedChunk], timeout: float = 180.0) -> str:
    prompt = build_prompt(query, sources)
    payload = {
        "model": settings.llm_model,
        "prompt": prompt,
        "stream": False,
        "think": False,
        "options": {
            "temperature": settings.llm_temperature,
            "top_p": settings.llm_top_p,
            "num_ctx": 8192,
        },
    }
    r = httpx.post(f"{settings.ollama_url}/api/generate", json=payload, timeout=timeout)
    r.raise_for_status()
    return (r.json().get("response") or "").strip()


def list_models() -> list[str]:
    r = httpx.get(f"{settings.ollama_url}/api/tags", timeout=10.0)
    r.raise_for_status()
    return [m.get("name", "") for m in r.json().get("models", [])]


def ollama_status() -> tuple[bool, str]:
    try:
        models = list_models()
        base = {m.split(":")[0] for m in models}
        missing = [
            m for m in {settings.llm_model.split(":")[0], settings.vision_model.split(":")[0]}
            if m not in base
        ]
        if missing:
            return False, f"connected, but missing model(s): {', '.join(missing)}"
        return True, f"connected - {len(models)} model(s) available"
    except Exception as exc:
        return False, f"cannot reach Ollama at {settings.ollama_url}: {exc}"
