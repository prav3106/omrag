"""Local Qdrant vector store using named vectors.

A single collection holds both embedding spaces - `text` at 384 dimensions and
`image` at 512 - so one query can reach every modality without the operational
overhead of maintaining a collection per modality.
"""
from __future__ import annotations

import threading
from typing import Any

from ..config import settings


class QdrantStore:
    def __init__(self, url: str | None = None, collection: str | None = None) -> None:
        from qdrant_client import QdrantClient

        self.url = url or settings.qdrant_url
        self.collection = collection or settings.collection
        self.client = QdrantClient(url=self.url, timeout=30.0)
        self._lock = threading.RLock()

    # ---- schema -------------------------------------------------------
    def ensure_collection(self) -> None:
        from qdrant_client.models import Distance, VectorParams

        with self._lock:
            names = {c.name for c in self.client.get_collections().collections}
            if self.collection in names:
                return
            self.client.create_collection(
                collection_name=self.collection,
                vectors_config={
                    settings.text_vector: VectorParams(
                        size=settings.text_dim, distance=Distance.COSINE
                    ),
                    settings.image_vector: VectorParams(
                        size=settings.image_dim, distance=Distance.COSINE
                    ),
                },
            )

    def vector_schema(self) -> list[dict[str, Any]]:
        try:
            info = self.client.get_collection(self.collection)
            vectors = info.config.params.vectors
            if hasattr(vectors, "items"):
                return [
                    {"name": name, "dim": params.size, "metric": str(params.distance).split(".")[-1].title()}
                    for name, params in vectors.items()
                ]
            return [{"name": "default", "dim": vectors.size, "metric": "Cosine"}]
        except Exception:
            return []

    def count(self) -> int:
        try:
            return int(self.client.count(self.collection, exact=True).count)
        except Exception:
            return 0

    # ---- writes -------------------------------------------------------
    def upsert(self, points: list[dict]) -> None:
        """points: [{id, vector_name, vector, payload}, ...]"""
        if not points:
            return
        from qdrant_client.models import PointStruct

        structs = [
            PointStruct(id=p["id"], vector={p["vector_name"]: p["vector"]}, payload=p["payload"])
            for p in points
        ]
        with self._lock:
            for i in range(0, len(structs), 128):
                self.client.upsert(
                    collection_name=self.collection, points=structs[i : i + 128], wait=True
                )

    def delete(self, ids: list[str]) -> None:
        if not ids:
            return
        from qdrant_client.models import PointIdsList

        with self._lock:
            self.client.delete(
                collection_name=self.collection,
                points_selector=PointIdsList(points=ids),
                wait=True,
            )

    def drop(self) -> None:
        with self._lock:
            try:
                self.client.delete_collection(self.collection)
            except Exception:
                pass
        self.ensure_collection()

    # ---- reads --------------------------------------------------------
    def search(
        self,
        vector_name: str,
        vector: list[float],
        limit: int,
        modalities: list[str] | None = None,
        source_files: list[str] | None = None,
    ) -> list[dict]:
        from qdrant_client.models import FieldCondition, Filter, MatchAny

        must = []
        if modalities:
            must.append(FieldCondition(key="modality", match=MatchAny(any=list(modalities))))
        if source_files:
            must.append(FieldCondition(key="source_file", match=MatchAny(any=list(source_files))))
        query_filter = Filter(must=must) if must else None

        hits = self.client.search(
            collection_name=self.collection,
            query_vector=(vector_name, vector),
            limit=limit,
            query_filter=query_filter,
            with_payload=True,
            with_vectors=False,
        )
        return [{"id": str(h.id), "score": float(h.score), "payload": h.payload or {}} for h in hits]

    def healthy(self) -> tuple[bool, str]:
        try:
            names = {c.name for c in self.client.get_collections().collections}
            if self.collection not in names:
                return False, f"collection '{self.collection}' not created yet"
            return True, f"collection '{self.collection}' ready, {self.count()} points"
        except Exception as exc:
            return False, f"cannot reach Qdrant at {self.url}: {exc}"


_store: QdrantStore | None = None


def get_store() -> QdrantStore:
    global _store
    if _store is None:
        _store = QdrantStore()
        _store.ensure_collection()
    return _store
