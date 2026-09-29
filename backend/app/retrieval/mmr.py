"""Maximal Marginal Relevance.

Suppresses near-duplicate candidates - the same paragraph appearing in two
overlapping chunks - so the shortlist handed to the reranker covers more
distinct evidence.
"""
from __future__ import annotations

from .bm25 import tokenize


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    inter = len(a & b)
    return inter / (len(a) + len(b) - inter)


def mmr_select(
    items: list[dict], k: int, lambda_: float = 0.7, text_key: str = "text",
    score_key: str = "dense_score",
) -> list[dict]:
    if len(items) <= k:
        return items

    pool = list(items)
    token_sets = {id(it): set(tokenize(it.get(text_key, ""))) for it in pool}
    selected: list[dict] = []

    while pool and len(selected) < k:
        best, best_score = None, float("-inf")
        for cand in pool:
            relevance = float(cand.get(score_key, 0.0))
            redundancy = max(
                (_jaccard(token_sets[id(cand)], token_sets[id(s)]) for s in selected),
                default=0.0,
            )
            score = lambda_ * relevance - (1 - lambda_) * redundancy
            if score > best_score:
                best, best_score = cand, score
        selected.append(best)
        pool.remove(best)
    return selected
