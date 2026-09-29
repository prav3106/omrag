"""Retrieval pipeline: dense search -> BM25 fusion -> MMR -> cross-encoder rerank.

Scores from each stage are min-max normalised before fusion so that they are
comparable, then combined with the weights in `settings`. The modality
diversity bonus stops a result set collapsing entirely into one modality when
evidence from another would be more useful.
"""
from __future__ import annotations

import time

from ..config import settings
from ..models import Modality, RetrievedChunk
from ..store import get_registry, get_store
from .bm25 import BM25
from .mmr import mmr_select
from .reranker import rerank


def _normalise(values: list[float]) -> list[float]:
    if not values:
        return []
    lo, hi = min(values), max(values)
    if hi - lo < 1e-9:
        return [0.5] * len(values)
    return [(v - lo) / (hi - lo) for v in values]


def _fmt_ts(seconds: float | None) -> str:
    if seconds is None:
        return ""
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    return f"{h:02d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"


def _citation(row: dict) -> str:
    name = row.get("source_file") or "unknown"
    if row.get("modality") == "audio" and row.get("start_time") is not None:
        return f"{name} @ {_fmt_ts(row['start_time'])}-{_fmt_ts(row.get('end_time'))}"
    if row.get("page_number"):
        return f"{name}, p.{row['page_number']}"
    return name


def retrieve(
    query: str,
    top_k: int | None = None,
    modalities: list[Modality] | None = None,
    source_files: list[str] | None = None,
) -> tuple[list[RetrievedChunk], dict]:
    top_k = top_k or settings.final_k
    timings: dict[str, int] = {}
    store = get_store()
    registry = get_registry()

    # ---- 1. encode the query ------------------------------------------
    t0 = time.perf_counter()
    from ..embeddings.text_encoder import encode_query

    text_vec = encode_query(query)
    clip_vec = None
    want_images = modalities is None or "image" in modalities
    if want_images:
        try:
            from ..embeddings.image_encoder import encode_text_for_images

            clip_vec = encode_text_for_images(query)
        except Exception:
            clip_vec = None
    timings["encode_ms"] = int((time.perf_counter() - t0) * 1000)

    # ---- 2. dense search across every named vector space ---------------
    t0 = time.perf_counter()
    hits: dict[str, dict] = {}

    def absorb(results: list[dict]) -> None:
        for h in results:
            prev = hits.get(h["id"])
            if prev is None or h["score"] > prev["score"]:
                hits[h["id"]] = h

    absorb(
        store.search(
            settings.text_vector, text_vec, settings.candidate_k, modalities, source_files
        )
    )
    if clip_vec is not None:
        absorb(
            store.search(
                settings.image_vector, clip_vec, settings.candidate_k, ["image"], source_files
            )
        )
    timings["search_ms"] = int((time.perf_counter() - t0) * 1000)

    if not hits:
        timings["fuse_ms"] = timings["rerank_ms"] = 0
        return [], timings

    # ---- 3. hydrate from the registry ----------------------------------
    rows = registry.chunks_by_ids(list(hits))
    candidates: list[dict] = []
    for cid, hit in hits.items():
        row = rows.get(cid)
        if row is None:
            payload = hit["payload"]
            row = {
                "chunk_id": cid,
                "modality": payload.get("modality", "text"),
                "source_file": payload.get("source_file", ""),
                "page_number": payload.get("page_number"),
                "start_time": payload.get("start_time"),
                "end_time": payload.get("end_time"),
                "image_path": payload.get("image_path"),
                "chunk_text": payload.get("chunk_text", ""),
            }
        candidates.append({**row, "text": row.get("chunk_text", ""), "dense_score": hit["score"]})

    # ---- 4. BM25 fusion + MMR diversification --------------------------
    t0 = time.perf_counter()
    sparse = BM25([c["text"] for c in candidates]).scores(query)
    dense_n = _normalise([c["dense_score"] for c in candidates])
    sparse_n = _normalise(sparse)
    for c, d, s, raw in zip(candidates, dense_n, sparse_n, sparse):
        c["dense_norm"] = d
        c["sparse_score"] = raw
        c["fused"] = 0.65 * d + 0.35 * s

    shortlist = mmr_select(
        candidates, k=settings.candidate_k, lambda_=settings.mmr_lambda, score_key="fused"
    )
    timings["fuse_ms"] = int((time.perf_counter() - t0) * 1000)

    # ---- 5. cross-encoder reranking ------------------------------------
    t0 = time.perf_counter()
    if settings.enable_rerank and shortlist:
        try:
            scores = rerank(query, shortlist)
            for c, s in zip(shortlist, scores):
                c["rerank_score"] = s
            rerank_n = _normalise([c["rerank_score"] for c in shortlist])
        except Exception:
            for c in shortlist:
                c["rerank_score"] = 0.0
            rerank_n = [c["fused"] for c in shortlist]
    else:
        for c in shortlist:
            c["rerank_score"] = 0.0
        rerank_n = [c["fused"] for c in shortlist]
    timings["rerank_ms"] = int((time.perf_counter() - t0) * 1000)

    # ---- 6. weighted late fusion with a modality diversity bonus -------
    seen: set[str] = set()
    for c, r in zip(shortlist, rerank_n):
        bonus = 0.0 if c["modality"] in seen else 1.0
        seen.add(c["modality"])
        c["final_score"] = (
            settings.w_dense * c["dense_norm"]
            + settings.w_rerank * r
            + settings.w_diversity * bonus
        )

    shortlist.sort(key=lambda c: c["final_score"], reverse=True)

    # Reserve one slot per modality present in the shortlist before filling the
    # rest by raw score. Without this, a modality whose scores sit on a lower
    # natural scale (e.g. CLIP image similarity vs. text dense similarity) can
    # be squeezed out entirely on compound/cross-modal queries even when it is
    # the only source that actually answers part of the question.
    best_per_modality: dict[str, dict] = {}
    for c in shortlist:
        m = c["modality"]
        if m not in best_per_modality or c["final_score"] > best_per_modality[m]["final_score"]:
            best_per_modality[m] = c

    top: list[dict] = []
    seen_ids: set[str] = set()
    for c in sorted(best_per_modality.values(), key=lambda c: c["final_score"], reverse=True):
        if len(top) >= top_k:
            break
        top.append(c)
        seen_ids.add(c["chunk_id"])
    for c in shortlist:
        if len(top) >= top_k:
            break
        if c["chunk_id"] not in seen_ids:
            top.append(c)
            seen_ids.add(c["chunk_id"])

    top.sort(key=lambda c: c["final_score"], reverse=True)

    return [
        RetrievedChunk(
            rank=i + 1,
            chunk_id=c["chunk_id"],
            modality=c["modality"],
            text=c["text"],
            source_file=c.get("source_file", ""),
            citation=_citation(c),
            page_number=c.get("page_number"),
            start_time=c.get("start_time"),
            end_time=c.get("end_time"),
            image_path=c.get("image_path"),
            dense_score=round(float(c.get("dense_score", 0.0)), 4),
            sparse_score=round(float(c.get("sparse_score", 0.0)), 4),
            rerank_score=round(float(c.get("rerank_score", 0.0)), 4),
            final_score=round(float(c["final_score"]), 4),
        )
        for i, c in enumerate(top)
    ], timings
