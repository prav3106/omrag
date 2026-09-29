"""Cross-encoder reranking with ms-marco-MiniLM.

A bi-encoder never lets the query and the candidate interact, which caps its
precision. A cross-encoder does, but is far too slow to run over the corpus -
so it is applied only to the shortlist, which is where most of the accuracy
benefit lives.
"""
from __future__ import annotations

import threading

from ..config import settings

_model = None
_lock = threading.Lock()


def _get_model():
    global _model
    if _model is None:
        with _lock:
            if _model is None:
                from sentence_transformers import CrossEncoder

                _model = CrossEncoder(settings.reranker_model)
    return _model


def rerank(query: str, candidates: list[dict], text_key: str = "text") -> list[float]:
    if not candidates:
        return []
    model = _get_model()
    pairs = [(query, (c.get(text_key) or "")[:2000]) for c in candidates]
    scores = model.predict(pairs, show_progress_bar=False)
    return [float(s) for s in scores]


def reranker_ready() -> tuple[bool, str]:
    if not settings.enable_rerank:
        return True, "disabled by configuration"
    try:
        _get_model()
        return True, settings.reranker_model
    except Exception as exc:  # pragma: no cover
        return False, str(exc)
