from __future__ import annotations

from fastapi import APIRouter, File, HTTPException, UploadFile

from ..config import settings
from ..models import IngestResponse, IngestResult
from ..service import ingest_file, save_upload

router = APIRouter(prefix="/ingest", tags=["ingest"])


@router.post("", response_model=IngestResponse)
async def ingest(files: list[UploadFile] = File(...)) -> IngestResponse:
    if not files:
        raise HTTPException(400, "no files supplied")

    results: list[IngestResult] = []
    for upload in files:
        data = await upload.read()
        if len(data) > settings.max_upload_mb * 1024 * 1024:
            results.append(IngestResult(
                file_name=upload.filename or "unknown", modality="text", doc_id="",
                chunks_created=0, chunks_skipped=0, duration_ms=0,
                error=f"file exceeds the {settings.max_upload_mb} MB limit",
            ))
            continue
        try:
            path = save_upload(upload.filename or "upload.bin", data)
            results.append(ingest_file(path, original_name=upload.filename))
        except Exception as exc:
            results.append(IngestResult(
                file_name=upload.filename or "unknown", modality="text", doc_id="",
                chunks_created=0, chunks_skipped=0, duration_ms=0, error=str(exc),
            ))

    return IngestResponse(results=results, total_chunks=sum(r.chunks_created for r in results))
