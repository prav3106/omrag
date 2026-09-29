"""Sliding-window chunking.

Token counts are approximated with a whitespace tokenizer, which is within a few
percent of the sentence-transformers tokenizer for prose and costs nothing to
compute. The overlap guarantees that a sentence straddling a boundary still
appears intact inside one of the two adjacent windows.
"""
from __future__ import annotations

import re

from ..config import settings

_WS = re.compile(r"\s+")


def normalise(text: str) -> str:
    return _WS.sub(" ", text or "").strip()


def sliding_window(text: str, size: int | None = None, overlap: int | None = None) -> list[str]:
    size = size or settings.chunk_tokens
    overlap = overlap if overlap is not None else settings.chunk_overlap
    if overlap >= size:
        overlap = size // 4

    tokens = normalise(text).split(" ")
    tokens = [t for t in tokens if t]
    if not tokens:
        return []
    if len(tokens) <= size:
        return [" ".join(tokens)]

    step = size - overlap
    windows: list[str] = []
    for start in range(0, len(tokens), step):
        window = tokens[start : start + size]
        if not window:
            break
        windows.append(" ".join(window))
        if start + size >= len(tokens):
            break
    return windows


def merge_segments(
    segments: list[tuple[float, float, str]],
    target_words: int | None = None,
    max_gap: float | None = None,
) -> list[tuple[float, float, str]]:
    """Coalesce consecutive transcript segments into larger, context-bearing chunks.

    faster-whisper's VAD splits on every pause, which on narrated / TTS audio
    (short phrase-length pauses) yields dozens of near-context-free segments per
    minute. Folding runs of segments together up to a word-count target keeps
    citation timestamps close to accurate while giving embeddings enough
    context to match paraphrased queries. A large gap between segments (e.g. a
    genuine pause between sections) still forces a new chunk.
    """
    target_words = target_words or settings.audio_chunk_words
    max_gap = max_gap if max_gap is not None else settings.audio_chunk_max_gap
    if not segments:
        return []

    merged: list[tuple[float, float, str]] = []
    cur_start, cur_end, cur_text = segments[0]
    cur_words = len(cur_text.split())

    for start, end, text in segments[1:]:
        gap = start - cur_end
        words = len(text.split())
        if cur_words + words <= target_words and gap <= max_gap:
            cur_end = end
            cur_text = f"{cur_text} {text}".strip()
            cur_words += words
        else:
            merged.append((cur_start, cur_end, cur_text))
            cur_start, cur_end, cur_text = start, end, text
            cur_words = words

    merged.append((cur_start, cur_end, cur_text))
    return merged
