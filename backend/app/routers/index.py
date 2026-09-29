from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from ..config import settings
from ..models import DocumentInfo, IndexStats
from ..service import reset_index
from ..store import get_registry, get_store

router = APIRouter(prefix="/index", tags=["index"])


@router.get("/stats", response_model=IndexStats)
def stats() -> IndexStats:
    registry_stats = get_registry().stats()
    try:
        schema = get_store().vector_schema()
    except Exception:
        schema = []
    return IndexStats(collection=settings.collection, vector_schema=schema, **registry_stats)


@router.get("/documents", response_model=list[DocumentInfo])
def documents() -> list[DocumentInfo]:
    return [
        DocumentInfo(
            doc_id=d["doc_id"], file_name=d["file_name"], file_path=d["file_path"],
            modality=d["modality"], file_size=d["file_size"],
            chunk_count=d["chunk_count"], ingested_at=d["ingested_at"],
        )
        for d in get_registry().list_documents()
    ]


@router.get("/documents/{doc_id}/chunks")
def document_chunks(doc_id: str):
    chunks = [c for c in get_registry().all_chunks() if c["doc_id"] == doc_id]
    if not chunks:
        raise HTTPException(404, "no chunks found for this document")
    return chunks


@router.delete("/documents/{doc_id}")
def delete_document(doc_id: str):
    ids = get_registry().delete_document(doc_id)
    get_store().delete(ids)
    return {"deleted_chunks": len(ids)}


@router.post("/reset")
def reset():
    reset_index()
    return {"status": "index cleared"}


@router.get("/image")
def image(path: str):
    """Serve a locally extracted image back to the UI. Confined to the data dir."""
    from pathlib import Path

    target = Path(path).resolve()
    if not str(target).startswith(str(settings.data_dir.resolve())) or not target.is_file():
        raise HTTPException(404, "image not found")
    return FileResponse(target)
