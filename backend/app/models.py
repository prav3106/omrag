"""Pydantic request/response schemas shared by the routers."""
from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

Modality = Literal["text", "image", "audio"]


class Chunk(BaseModel):
    chunk_id: str
    doc_id: str
    modality: Modality
    text: str = ""
    source_file: str = ""
    page_number: Optional[int] = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    image_path: Optional[str] = None
    linked_chunks: list[str] = Field(default_factory=list)
    extra: dict[str, Any] = Field(default_factory=dict)

    def citation_label(self) -> str:
        if self.modality == "audio" and self.start_time is not None:
            return f"{self.source_file} @ {_fmt_ts(self.start_time)}-{_fmt_ts(self.end_time or self.start_time)}"
        if self.page_number is not None:
            return f"{self.source_file}, p.{self.page_number}"
        return self.source_file


def _fmt_ts(seconds: float) -> str:
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    return f"{h:02d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"


class IngestResult(BaseModel):
    file_name: str
    modality: Modality
    doc_id: str
    chunks_created: int
    chunks_skipped: int
    duration_ms: int
    error: Optional[str] = None


class IngestResponse(BaseModel):
    results: list[IngestResult]
    total_chunks: int


class RetrievedChunk(BaseModel):
    rank: int
    chunk_id: str
    modality: Modality
    text: str
    source_file: str
    citation: str
    page_number: Optional[int] = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    image_path: Optional[str] = None
    dense_score: float = 0.0
    sparse_score: float = 0.0
    rerank_score: float = 0.0
    final_score: float = 0.0


class QueryRequest(BaseModel):
    query: str
    top_k: Optional[int] = None
    modalities: Optional[list[Modality]] = None
    source_files: Optional[list[str]] = None
    generate: bool = True


class QueryTimings(BaseModel):
    encode_ms: int = 0
    search_ms: int = 0
    fuse_ms: int = 0
    rerank_ms: int = 0
    generate_ms: int = 0
    total_ms: int = 0


class QueryResponse(BaseModel):
    query: str
    answer: str = ""
    sources: list[RetrievedChunk] = Field(default_factory=list)
    timings: QueryTimings = Field(default_factory=QueryTimings)
    rerank_enabled: bool = True
    warning: Optional[str] = None


class DocumentInfo(BaseModel):
    doc_id: str
    file_name: str
    file_path: str
    modality: Modality
    file_size: int
    chunk_count: int
    ingested_at: str


class IndexStats(BaseModel):
    documents: int
    chunks: int
    by_modality: dict[str, int]
    collection: str
    vector_schema: list[dict[str, Any]]


class DependencyStatus(BaseModel):
    name: str
    ok: bool
    detail: str = ""


class StatusResponse(BaseModel):
    healthy: bool
    offline: bool = True
    dependencies: list[DependencyStatus]
    stats: Optional[IndexStats] = None
