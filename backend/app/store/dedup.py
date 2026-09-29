"""Content-derived identifiers.

Deriving the point ID from a UUID5 hash of the normalised chunk content makes
deduplication deterministic: re-ingesting an unchanged corpus is a no-op
regardless of ingestion order or file naming.
"""
from __future__ import annotations

import hashlib
import uuid
from pathlib import Path

NAMESPACE = uuid.UUID("6f1c8c4a-6d9b-5c8e-9a3f-0b2d1e4a7c55")


def chunk_uuid(*parts: object) -> str:
    key = "||".join(str(p) for p in parts)
    return str(uuid.uuid5(NAMESPACE, key))


def file_sha256(path: Path, block: int = 1 << 20) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        while chunk := fh.read(block):
            digest.update(chunk)
    return digest.hexdigest()
