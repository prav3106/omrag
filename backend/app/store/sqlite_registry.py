"""SQLite metadata registry.

Vector search and relational filtering have different access patterns, so
provenance, ingestion bookkeeping and BM25 source text live here while Qdrant
handles approximate nearest-neighbour search.
"""
from __future__ import annotations

import json
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from ..config import settings

SCHEMA = """
CREATE TABLE IF NOT EXISTS documents (
    doc_id        TEXT PRIMARY KEY,
    file_name     TEXT NOT NULL,
    file_path     TEXT NOT NULL,
    file_hash     TEXT NOT NULL,
    file_size     INTEGER NOT NULL,
    modality      TEXT NOT NULL,
    chunk_count   INTEGER NOT NULL DEFAULT 0,
    last_modified TEXT,
    ingested_at   TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS chunks (
    chunk_id      TEXT PRIMARY KEY,
    doc_id        TEXT NOT NULL REFERENCES documents(doc_id) ON DELETE CASCADE,
    modality      TEXT NOT NULL,
    source_file   TEXT NOT NULL,
    page_number   INTEGER,
    start_time    REAL,
    end_time      REAL,
    image_path    TEXT,
    chunk_text    TEXT NOT NULL DEFAULT '',
    linked_chunks TEXT NOT NULL DEFAULT '[]',
    created_at    TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_chunks_doc ON chunks(doc_id);
CREATE INDEX IF NOT EXISTS idx_chunks_modality ON chunks(modality);

CREATE TABLE IF NOT EXISTS queries (
    query_id           INTEGER PRIMARY KEY AUTOINCREMENT,
    query_text         TEXT NOT NULL,
    query_modality     TEXT NOT NULL DEFAULT 'text',
    retrieved_chunk_ids TEXT NOT NULL DEFAULT '[]',
    llm_response       TEXT NOT NULL DEFAULT '',
    response_time_ms   INTEGER NOT NULL DEFAULT 0,
    created_at         TEXT NOT NULL
);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class Registry:
    def __init__(self, path: Path | None = None) -> None:
        self.path = Path(path or settings.sqlite_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(self.path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        with self._lock:
            self._conn.executescript(SCHEMA)
            self._conn.commit()

    # ---- documents ----------------------------------------------------
    def upsert_document(self, **kw: Any) -> None:
        with self._lock:
            self._conn.execute(
                """INSERT INTO documents
                   (doc_id, file_name, file_path, file_hash, file_size, modality,
                    chunk_count, last_modified, ingested_at)
                   VALUES (:doc_id, :file_name, :file_path, :file_hash, :file_size,
                           :modality, :chunk_count, :last_modified, :ingested_at)
                   ON CONFLICT(doc_id) DO UPDATE SET
                       chunk_count = excluded.chunk_count,
                       file_hash   = excluded.file_hash,
                       ingested_at = excluded.ingested_at""",
                {"ingested_at": _now(), **kw},
            )
            self._conn.commit()

    def document_by_hash(self, file_hash: str) -> sqlite3.Row | None:
        with self._lock:
            return self._conn.execute(
                "SELECT * FROM documents WHERE file_hash = ?", (file_hash,)
            ).fetchone()

    def list_documents(self) -> list[dict]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM documents ORDER BY ingested_at DESC"
            ).fetchall()
        return [dict(r) for r in rows]

    def delete_document(self, doc_id: str) -> list[str]:
        with self._lock:
            ids = [
                r["chunk_id"]
                for r in self._conn.execute(
                    "SELECT chunk_id FROM chunks WHERE doc_id = ?", (doc_id,)
                ).fetchall()
            ]
            self._conn.execute("DELETE FROM chunks WHERE doc_id = ?", (doc_id,))
            self._conn.execute("DELETE FROM documents WHERE doc_id = ?", (doc_id,))
            self._conn.commit()
        return ids

    # ---- chunks -------------------------------------------------------
    def existing_chunk_ids(self, ids: Iterable[str]) -> set[str]:
        ids = list(ids)
        if not ids:
            return set()
        found: set[str] = set()
        with self._lock:
            for i in range(0, len(ids), 800):
                batch = ids[i : i + 800]
                placeholders = ",".join("?" * len(batch))
                rows = self._conn.execute(
                    f"SELECT chunk_id FROM chunks WHERE chunk_id IN ({placeholders})", batch
                ).fetchall()
                found.update(r["chunk_id"] for r in rows)
        return found

    def insert_chunks(self, chunks: list[dict]) -> None:
        if not chunks:
            return
        with self._lock:
            self._conn.executemany(
                """INSERT OR IGNORE INTO chunks
                   (chunk_id, doc_id, modality, source_file, page_number, start_time,
                    end_time, image_path, chunk_text, linked_chunks, created_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                [
                    (
                        c["chunk_id"], c["doc_id"], c["modality"], c["source_file"],
                        c.get("page_number"), c.get("start_time"), c.get("end_time"),
                        c.get("image_path"), c.get("chunk_text", ""),
                        json.dumps(c.get("linked_chunks", [])), _now(),
                    )
                    for c in chunks
                ],
            )
            self._conn.commit()

    def all_chunks(self, modalities: list[str] | None = None,
                   source_files: list[str] | None = None) -> list[dict]:
        sql = "SELECT * FROM chunks"
        clauses, params = [], []
        if modalities:
            clauses.append(f"modality IN ({','.join('?' * len(modalities))})")
            params += modalities
        if source_files:
            clauses.append(f"source_file IN ({','.join('?' * len(source_files))})")
            params += source_files
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        with self._lock:
            rows = self._conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]

    def chunks_by_ids(self, ids: list[str]) -> dict[str, dict]:
        if not ids:
            return {}
        out: dict[str, dict] = {}
        with self._lock:
            for i in range(0, len(ids), 800):
                batch = ids[i : i + 800]
                placeholders = ",".join("?" * len(batch))
                rows = self._conn.execute(
                    f"SELECT * FROM chunks WHERE chunk_id IN ({placeholders})", batch
                ).fetchall()
                for r in rows:
                    out[r["chunk_id"]] = dict(r)
        return out

    # ---- stats & queries ----------------------------------------------
    def stats(self) -> dict:
        with self._lock:
            docs = self._conn.execute("SELECT COUNT(*) c FROM documents").fetchone()["c"]
            chunks = self._conn.execute("SELECT COUNT(*) c FROM chunks").fetchone()["c"]
            rows = self._conn.execute(
                "SELECT modality, COUNT(*) c FROM chunks GROUP BY modality"
            ).fetchall()
        return {
            "documents": docs,
            "chunks": chunks,
            "by_modality": {r["modality"]: r["c"] for r in rows},
        }

    def log_query(self, query_text: str, chunk_ids: list[str], response: str, ms: int) -> None:
        with self._lock:
            self._conn.execute(
                """INSERT INTO queries
                   (query_text, query_modality, retrieved_chunk_ids, llm_response,
                    response_time_ms, created_at)
                   VALUES (?,?,?,?,?,?)""",
                (query_text, "text", json.dumps(chunk_ids), response, ms, _now()),
            )
            self._conn.commit()

    def recent_queries(self, limit: int = 20) -> list[dict]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM queries ORDER BY query_id DESC LIMIT ?", (limit,)
            ).fetchall()
        return [dict(r) for r in rows]

    def reset(self) -> None:
        with self._lock:
            self._conn.executescript(
                "DELETE FROM chunks; DELETE FROM documents; DELETE FROM queries;"
            )
            self._conn.commit()


_registry: Registry | None = None


def get_registry() -> Registry:
    global _registry
    if _registry is None:
        _registry = Registry()
    return _registry
