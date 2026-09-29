"""Grounding prompt construction.

Every retrieved chunk is numbered and annotated with its provenance, and the
system instruction forbids answering from anything else. Numbered citations
are what make a hallucination visible: a claim without a resolvable [n] is
immediately detectable by the reader.
"""
from __future__ import annotations

from ..config import settings
from ..models import RetrievedChunk

SYSTEM_PROMPT = (
    "You are an offline retrieval assistant. Answer using ONLY the numbered context "
    "passages provided. Each passage begins with its own bracketed number, e.g. '[2] "
    "(DOCUMENT - ...)'. When you use a passage, you MUST cite that exact same number — "
    "re-read the bracket at the start of the passage you are drawing from immediately "
    "before writing its citation marker; do not cite a different passage's number, and "
    "do not renumber passages sequentially in your answer. "
    "Context blocks labelled IMAGE contain AI-generated visual descriptions of the image "
    "content — treat them as authoritative evidence for questions about appearance, "
    "facial features, clothing, charts, diagrams or any visual content. "
    "If the context does not contain the answer, "
    "say exactly: 'The indexed sources do not contain an answer to this question.' "
    "Never invent sources, numbers, or citation markers. Be concise and specific."
)


def _approx_tokens(text: str) -> int:
    return max(1, len(text) // 4)


def build_prompt(query: str, sources: list[RetrievedChunk]) -> str:
    budget = settings.max_context_tokens
    blocks: list[str] = []
    used = _approx_tokens(query) + 200

    for src in sources:
        label = {"text": "DOCUMENT", "image": "IMAGE", "audio": "AUDIO"}.get(src.modality, "SOURCE")
        body = src.text.strip() or "(no extractable text)"
        block = f"[{src.rank}] ({label} - {src.citation})\n{body}"
        cost = _approx_tokens(block)
        if used + cost > budget:
            remaining = max(0, (budget - used)) * 4
            if remaining > 200:
                blocks.append(block[:remaining] + " ...[truncated]")
            break
        blocks.append(block)
        used += cost

    context = "\n\n".join(blocks) if blocks else "(no context retrieved)"
    return (
        f"{SYSTEM_PROMPT}\n\n"
        f"=== CONTEXT ===\n{context}\n\n"
        f"=== QUESTION ===\n{query}\n\n"
        f"=== ANSWER (with [n] citations) ===\n"
    )
