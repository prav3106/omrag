from __future__ import annotations

import shutil

from fastapi import APIRouter

from ..config import settings
from ..generation import ollama_status
from ..models import DependencyStatus, IndexStats, StatusResponse
from ..store import get_registry, get_store

router = APIRouter(prefix="/status", tags=["status"])


def _check_qdrant() -> DependencyStatus:
    try:
        ok, detail = get_store().healthy()
    except Exception as exc:
        ok, detail = False, str(exc)
    return DependencyStatus(name="Qdrant vector store", ok=ok, detail=detail)


def _check_registry() -> DependencyStatus:
    try:
        s = get_registry().stats()
        return DependencyStatus(
            name="SQLite registry", ok=True,
            detail=f"{s['documents']} documents, {s['chunks']} chunks",
        )
    except Exception as exc:
        return DependencyStatus(name="SQLite registry", ok=False, detail=str(exc))


def _check_binary(name: str, binary: str) -> DependencyStatus:
    path = shutil.which(binary)
    return DependencyStatus(
        name=name, ok=path is not None,
        detail=path or f"'{binary}' not found on PATH",
    )


@router.get("", response_model=StatusResponse)
def status(deep: bool = False) -> StatusResponse:
    deps: list[DependencyStatus] = [
        DependencyStatus(name="Backend API", ok=True, detail="FastAPI running"),
        _check_registry(),
        _check_qdrant(),
    ]

    ok, detail = ollama_status()
    deps.append(DependencyStatus(name="Ollama inference", ok=ok, detail=detail))
    deps.append(_check_binary("ffmpeg (audio normalisation)", "ffmpeg"))
    deps.append(_check_binary("tesseract (image OCR)", "tesseract"))


    if deep:
        from ..embeddings.image_encoder import image_encoder_ready
        from ..embeddings.text_encoder import text_encoder_ready
        from ..retrieval.reranker import reranker_ready

        for label, fn in (
            ("Text embeddings", text_encoder_ready),
            ("Image embeddings", image_encoder_ready),
            ("Cross-encoder reranker", reranker_ready),
        ):
            ok, detail = fn()
            deps.append(DependencyStatus(name=label, ok=ok, detail=detail))

    try:
        rs = get_registry().stats()
        stats = IndexStats(
            collection=settings.collection, vector_schema=get_store().vector_schema(), **rs
        )
    except Exception:
        stats = None

    return StatusResponse(
        healthy=all(d.ok for d in deps if d.name in {"Backend API", "SQLite registry"}),
        offline=True, dependencies=deps, stats=stats,
    )


@router.get("/config")
def config():
    return {
        "collection": settings.collection,
        "text_model": settings.text_model,
        "image_model": f"{settings.image_model} / {settings.image_pretrained}",
        "reranker_model": settings.reranker_model,
        "whisper_model": f"{settings.whisper_model} ({settings.whisper_compute})",
        "llm_model": settings.llm_model,
        "vision_model": settings.vision_model,
        "chunk_tokens": settings.chunk_tokens,
        "chunk_overlap": settings.chunk_overlap,
        "candidate_k": settings.candidate_k,
        "final_k": settings.final_k,
        "weights": {
            "dense": settings.w_dense,
            "rerank": settings.w_rerank,
            "diversity": settings.w_diversity,
        },
        "rerank_enabled": settings.enable_rerank,
        "vision_describe_enabled": settings.enable_vision_describe,
    }
