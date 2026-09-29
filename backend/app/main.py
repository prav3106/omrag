"""FastAPI application entry point.

Binds to loopback by default. No route in this application makes an outbound
request to anything other than the local Qdrant and Ollama daemons.
"""
from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .routers import index, ingest, query, status

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("omrag")

app = FastAPI(
    title="Offline Multimodal RAG",
    version="1.0.0",
    description="Fully offline multimodal retrieval-augmented generation over "
                "documents, images and audio.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_origins),
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ingest.router)
app.include_router(query.router)
app.include_router(index.router)
app.include_router(status.router)


@app.on_event("startup")
def startup() -> None:
    log.info("data directory: %s", settings.data_dir)
    try:
        from .store import get_store

        get_store().ensure_collection()
        log.info("qdrant collection '%s' ready", settings.collection)
    except Exception as exc:
        log.warning("qdrant not reachable at startup: %s", exc)


@app.get("/")
def root():
    return {"name": "Offline Multimodal RAG", "version": "1.0.0", "offline": True}


@app.get("/health")
def health():
    return {"ok": True}
