from __future__ import annotations

import time

from fastapi import APIRouter, HTTPException

from ..config import settings
from ..generation import generate_answer
from ..models import QueryRequest, QueryResponse, QueryTimings
from ..retrieval import retrieve
from ..store import get_registry

router = APIRouter(prefix="/query", tags=["query"])


@router.post("", response_model=QueryResponse)
def query(req: QueryRequest) -> QueryResponse:
    if not req.query.strip():
        raise HTTPException(400, "query must not be empty")

    started = time.perf_counter()
    try:
        sources, timings = retrieve(
            req.query, req.top_k, req.modalities, req.source_files
        )
    except ModuleNotFoundError as exc:
        raise HTTPException(
            503,
            f"A pipeline dependency is missing ({exc.name}). "
            "Install the backend requirements: pip install -r backend/requirements.txt",
        ) from exc
    except Exception as exc:
        raise HTTPException(
            503,
            f"Retrieval failed: {exc}. Check that Qdrant is running "
            "(docker compose up -d) and that the models have been downloaded.",
        ) from exc

    answer, warning = "", None
    gen_ms = 0
    if not sources:
        warning = "No indexed content matched this query."
    elif req.generate:
        t0 = time.perf_counter()
        try:
            answer = generate_answer(req.query, sources)
        except Exception as exc:
            warning = f"Retrieval succeeded but generation failed: {exc}"
        gen_ms = int((time.perf_counter() - t0) * 1000)

    total_ms = int((time.perf_counter() - started) * 1000)
    get_registry().log_query(req.query, [s.chunk_id for s in sources], answer, total_ms)

    return QueryResponse(
        query=req.query,
        answer=answer,
        sources=sources,
        timings=QueryTimings(generate_ms=gen_ms, total_ms=total_ms, **timings),
        rerank_enabled=settings.enable_rerank,
        warning=warning,
    )


@router.get("/history")
def history(limit: int = 20):
    return get_registry().recent_queries(limit)
