"""Offline speech-to-text with faster-whisper.

The model is loaded lazily and cached at module level so that repeated
ingestion does not pay the load cost more than once per process.
"""
from __future__ import annotations

from pathlib import Path

from ..config import settings

_model = None


def _get_model():
    global _model
    if _model is None:
        from faster_whisper import WhisperModel

        _model = WhisperModel(
            settings.whisper_model,
            device="auto",
            compute_type=settings.whisper_compute,
        )
    return _model


def transcribe(path: Path) -> list[tuple[float, float, str]]:
    """Return [(start_seconds, end_seconds, text), ...] for an audio file."""
    model = _get_model()
    segments, _info = model.transcribe(str(path), vad_filter=True, beam_size=5)
    out: list[tuple[float, float, str]] = []
    for seg in segments:
        text = (seg.text or "").strip()
        if text:
            out.append((float(seg.start), float(seg.end), text))
    return out
