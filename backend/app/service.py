"""Ingestion orchestration.

Ties the loaders, chunker, encoders and stores together. Writes follow a
staging-then-commit order - vectors into Qdrant first, then the registry rows -
so an interrupted ingestion can only leave orphaned vectors (harmless, and
overwritten on the next run because IDs are content-derived) rather than
registry rows pointing at vectors that do not exist.
"""
from __future__ import annotations

import shutil
import time
from pathlib import Path

from .config import settings
from .ingest.chunker import merge_segments, normalise, sliding_window
from .ingest.router import detect_modality, load_file
from .models import IngestResult
from .store import chunk_uuid, file_sha256, get_registry, get_store


def _stage_text_chunks(doc_id: str, source_file: str, text: str,
                       page_number: int | None = None) -> list[dict]:
    out = []
    for i, window in enumerate(sliding_window(text)):
        out.append({
            "chunk_id": chunk_uuid(doc_id, "text", page_number, i, window),
            "doc_id": doc_id,
            "modality": "text",
            "source_file": source_file,
            "page_number": page_number,
            "chunk_text": window,
        })
    return out


def ingest_file(path: Path, original_name: str | None = None) -> IngestResult:
    started = time.perf_counter()
    source_file = original_name or path.name
    registry = get_registry()
    store = get_store()

    modality, _kind = detect_modality(path)
    file_hash = file_sha256(path)
    doc_id = chunk_uuid("doc", file_hash)

    payload = load_file(path)
    text_chunks: list[dict] = []
    image_chunks: list[dict] = []

    if payload["kind"] in {"pdf"}:
        for page_number, page_text in payload["pages"]:
            text_chunks += _stage_text_chunks(doc_id, source_file, page_text, page_number)
        from .ingest.image_loader import ocr_image
        if settings.enable_vision_describe:
            from .embeddings.vision_describe import describe_image as _describe
        else:
            _describe = None

        for page_number, img_path in payload["images"]:
            description_parts = []
            ocr_text = ocr_image(img_path)
            if ocr_text:
                description_parts.append(f"Text in image: {normalise(ocr_text)}")
            if _describe is not None:
                desc = _describe(img_path)
                if desc:
                    description_parts.append(desc)
            image_chunks.append({
                "chunk_id": chunk_uuid(doc_id, "image", page_number, str(img_path)),
                "doc_id": doc_id,
                "modality": "image",
                "source_file": source_file,
                "page_number": page_number,
                "image_path": str(img_path),
                "chunk_text": " ".join(description_parts).strip(),
            })

    elif payload["kind"] in {"docx", "plain"}:
        text_chunks += _stage_text_chunks(doc_id, source_file, payload["text"])

    elif payload["kind"] == "image":
        img_path = Path(payload["image_path"])
        description_parts = []
        if payload.get("ocr"):
            description_parts.append(f"Text in image: {normalise(payload['ocr'])}")
        if settings.enable_vision_describe:
            from .embeddings.vision_describe import describe_image

            desc = describe_image(img_path)
            if desc:
                description_parts.append(desc)
        image_chunks.append({
            "chunk_id": chunk_uuid(doc_id, "image", str(img_path)),
            "doc_id": doc_id,
            "modality": "image",
            "source_file": source_file,
            "image_path": str(img_path),
            "chunk_text": " ".join(description_parts).strip(),
        })

    elif payload["kind"] == "audio":
        for i, (start, end, seg_text) in enumerate(merge_segments(payload["segments"])):
            text_chunks.append({
                "chunk_id": chunk_uuid(doc_id, "audio", i, start, seg_text),
                "doc_id": doc_id,
                "modality": "audio",
                "source_file": source_file,
                "start_time": start,
                "end_time": end,
                "chunk_text": normalise(seg_text),
            })

    staged = text_chunks + image_chunks
    total_staged = len(staged)

    # ---- deduplicate against what is already indexed -------------------
    existing = registry.existing_chunk_ids([c["chunk_id"] for c in staged])
    fresh = [c for c in staged if c["chunk_id"] not in existing]
    skipped = total_staged - len(fresh)

    # ---- link siblings that came from the same page --------------------
    by_page: dict[int | None, list[str]] = {}
    for c in fresh:
        by_page.setdefault(c.get("page_number"), []).append(c["chunk_id"])
    for c in fresh:
        siblings = [x for x in by_page.get(c.get("page_number"), []) if x != c["chunk_id"]]
        c["linked_chunks"] = siblings[:8]

    # ---- embed ---------------------------------------------------------
    points: list[dict] = []
    fresh_text = [c for c in fresh if c["modality"] in {"text", "audio"} or c.get("chunk_text")]
    fresh_images = [c for c in fresh if c["modality"] == "image" and c.get("image_path")]

    if fresh_text:
        from .embeddings.text_encoder import encode_texts

        vectors = encode_texts([c["chunk_text"] for c in fresh_text])
        for c, v in zip(fresh_text, vectors):
            points.append({
                "id": c["chunk_id"],
                "vector_name": settings.text_vector,
                "vector": v,
                "payload": _payload(c),
            })

    if fresh_images:
        from .embeddings.image_encoder import encode_images

        vectors = encode_images([Path(c["image_path"]) for c in fresh_images])
        for c, v in zip(fresh_images, vectors):
            points.append({
                "id": c["chunk_id"],
                "vector_name": settings.image_vector,
                "vector": v,
                "payload": _payload(c),
            })

    # ---- commit ---------------------------------------------------------
    # Order matters: vectors first (orphans are harmless and are overwritten on
    # the next run because IDs are content-derived), then the parent document
    # row, then the chunk rows that reference it by foreign key.
    store.upsert(points)
    doc_row = dict(
        doc_id=doc_id,
        file_name=source_file,
        file_path=str(path),
        file_hash=file_hash,
        file_size=path.stat().st_size,
        modality=modality,
        last_modified=str(path.stat().st_mtime),
    )
    registry.upsert_document(chunk_count=0, **doc_row)
    registry.insert_chunks(fresh)
    registry.upsert_document(chunk_count=_count_for_doc(registry, doc_id), **doc_row)

    return IngestResult(
        file_name=source_file,
        modality=modality,
        doc_id=doc_id,
        chunks_created=len(fresh),
        chunks_skipped=skipped,
        duration_ms=int((time.perf_counter() - started) * 1000),
    )


def _count_for_doc(registry, doc_id: str) -> int:
    return sum(1 for c in registry.all_chunks() if c["doc_id"] == doc_id)


def _payload(chunk: dict) -> dict:
    return {
        "modality": chunk["modality"],
        "source_file": chunk["source_file"],
        "page_number": chunk.get("page_number"),
        "start_time": chunk.get("start_time"),
        "end_time": chunk.get("end_time"),
        "image_path": chunk.get("image_path"),
        "chunk_text": (chunk.get("chunk_text") or "")[:4000],
        "doc_id": chunk["doc_id"],
    }


def save_upload(filename: str, data: bytes) -> Path:
    safe = Path(filename).name.replace("/", "_")
    dest = settings.upload_dir / safe
    counter = 1
    while dest.exists() and dest.read_bytes()[:64] != data[:64]:
        dest = settings.upload_dir / f"{Path(safe).stem}_{counter}{Path(safe).suffix}"
        counter += 1
    dest.write_bytes(data)
    return dest


def reset_index() -> None:
    get_store().drop()
    get_registry().reset()
    for sub in ("uploads", "extracted"):
        target = settings.data_dir / sub
        if target.exists():
            shutil.rmtree(target, ignore_errors=True)
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
