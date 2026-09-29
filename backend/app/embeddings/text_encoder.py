"""384-dimensional text embeddings via sentence-transformers.

Vectors are L2-normalised on encode so cosine similarity reduces to a dot
product, which is what Qdrant computes under the hood for the cosine metric.
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
                from sentence_transformers import SentenceTransformer

                _model = SentenceTransformer(settings.text_model)
    return _model


def encode_texts(texts: list[str], batch_size: int = 64) -> list[list[float]]:
    if not texts:
        return []
    model = _get_model()
    vectors = model.encode(
        texts,
        batch_size=batch_size,
        normalize_embeddings=True,
        convert_to_numpy=True,
        show_progress_bar=False,
    )
    return [v.tolist() for v in vectors]


def encode_query(text: str) -> list[float]:
    return encode_texts([text])[0]


def text_encoder_ready() -> tuple[bool, str]:
    try:
        model = _get_model()
        dim = model.get_sentence_embedding_dimension()
        ok = dim == settings.text_dim
        return ok, f"{settings.text_model} ({dim}-d)"
    except Exception as exc:  # pragma: no cover - environment dependent
        return False, str(exc)
