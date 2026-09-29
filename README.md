# Offline Multimodal RAG System

Semantic search and grounded question answering over **documents, images and audio**
in a single unified index — running entirely on your own machine, with no network
call at runtime after the one-time model download.

Built for the Project Work Phase-I submission (23CS701), Department of CSE,
Sri Krishna College of Technology.

---

## What it does

- Ingests **PDF, DOCX, TXT, PNG/JPG and WAV/MP3** through MIME-based routing
- Extracts text (PyMuPDF / python-docx), runs **OCR** on images (OpenCV + pytesseract),
  and **transcribes audio** with segment-level timestamps (faster-whisper large-v3, int8)
- Embeds text at **384-d** (sentence-transformers) and images at **512-d** (open_clip ViT-B/32),
  stored as **named vectors in one local Qdrant collection**
- Retrieves across **every modality from a single query** — dense search fused with BM25,
  diversified with MMR, reranked by an ms-marco-MiniLM cross-encoder
- Generates answers with a **local LLM via Ollama**, every claim carrying a `[n]` citation
  that resolves to a file, page number or audio timestamp
- Deduplicates deterministically with **UUID5 content hashing**, so re-ingesting an
  unchanged corpus is a no-op

---

## Quick start

```bash
# 1. one-time setup: venv, npm install, Qdrant container, model downloads
./scripts/setup.sh

# 2. run it
./scripts/dev.sh
```

Then open **http://127.0.0.1:5173**.

### Manual setup

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r backend/requirements.txt
cd frontend && npm install && cd ..
cp .env.example .env

docker compose up -d                 # Qdrant on 127.0.0.1:6333
ollama pull llama3.1 && ollama pull llava

uvicorn app.main:app --app-dir backend --port 8000 --reload   # terminal 1
cd frontend && npm run dev                                    # terminal 2
```

### System dependencies

| Tool | Why | Install |
|---|---|---|
| Python 3.10+ | backend | — |
| Node.js 18+ | frontend | — |
| Docker | Qdrant container | — |
| Ollama | local LLM + LLaVA | https://ollama.com |
| `ffmpeg` | audio normalisation | `brew install ffmpeg` / `apt install ffmpeg` |
| `tesseract` | image OCR | `brew install tesseract` / `apt install tesseract-ocr` |

Reference hardware: **Apple M2 MacBook Air, 16 GB, no discrete GPU.**
Model weights total ~5.4 GB on disk; ~6 GB resident during active querying.

---

## Proving it is offline

```bash
# disable the network interface, then:
./scripts/verify_offline.sh
```

Ingestion and querying must both succeed with networking down. All assets, fonts
and scripts in the frontend are bundled locally — nothing is fetched from a CDN.
Qdrant and Ollama are both bound to loopback.

---

## Architecture

```
INGEST     PDF/DOCX (PyMuPDF, python-docx) · Images (OpenCV + pytesseract)
           Audio (faster-whisper large-v3, int8) · MIME-based routing
              ↓
PROCESS    Sliding window 512 tokens / 50 overlap
           Text → sentence-transformers (384-d) · Images → open_clip (512-d) + LLaVA description
              ↓
INDEX      Qdrant collection `multimodal_rag`, named vectors text(384-d) + image(512-d), cosine
           SQLite registry: documents · chunks · queries · UUID5 dedup · cross-modal links
              ↓
RETRIEVE   Dense search (all vector spaces) + BM25 fusion + MMR → top-20
           ms-marco-MiniLM cross-encoder rerank → top-5
              ↓
GENERATE   Ollama (Llama 3.1 / Mistral 7B) → grounded answer with [n] citations
           React UI: Dashboard · Knowledge Base · Chat Workspace · Processor Lab · System Status · Architecture
```

### Why two encoders

CLIP's text tower is trained on caption-length strings and degrades badly on
document-length passages, so sentence-transformers handles text while CLIP handles
the visual space. The two are bridged in two ways: LLaVA-generated descriptions put a
semantic surrogate for each image into the text space, and explicit sibling links in
the payload associate chunks derived from the same page or the same moment of a recording.

### Why rerank only a shortlist

A bi-encoder never lets the query and candidate interact, which caps its precision.
A cross-encoder does, but is far too slow corpus-wide. Applying it to a 20-item
shortlist captures most of the accuracy benefit for a fraction of the cost.

---

## Layout

```
backend/app/
  config.py            all tunables, env-overridable
  models.py            pydantic schemas
  service.py           ingestion orchestration (stage → commit)
  main.py              FastAPI app
  ingest/              router.py (MIME dispatch) + pdf/docx/image/audio loaders + chunker
  embeddings/          text_encoder · image_encoder · vision_describe (LLaVA)
  store/               qdrant_store · sqlite_registry · dedup (UUID5, SHA-256)
  retrieval/           dense + bm25 + mmr + reranker, orchestrated by pipeline.py
  generation/          prompt_builder (grounding + citations) · ollama_client
  routers/             ingest · query · index · status
  tests/               unit tests for the pure-python stages

frontend/src/
  App.jsx              shell, routing, theme
  lib/api.js           the only place that talks to the backend
  components/          Sidebar · Dropzone · Icons · Primitives
  pages/               Dashboard · KnowledgeBase · ChatWorkspace · ProcessorLab · SystemStatus · Architecture
```

---

## API

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/ingest` | multipart upload; routes, extracts, embeds, indexes |
| `POST` | `/query` | retrieve + generate; returns answer, ranked sources, per-stage timings |
| `GET` | `/query/history` | recent queries with latency |
| `GET` | `/index/stats` | document / chunk counts, modality split, vector schema |
| `GET` | `/index/documents` | ingested sources |
| `GET` | `/index/documents/{id}/chunks` | chunk-level inspection |
| `DELETE` | `/index/documents/{id}` | remove a source and its vectors |
| `POST` | `/index/reset` | clear collection, registry and uploads |
| `GET` | `/status?deep=true` | dependency health; `deep` also loads and verifies the models |
| `GET` | `/status/config` | active model and pipeline configuration |

Interactive docs at **http://127.0.0.1:8000/docs** once the backend is running.

---

## Tuning

Everything lives in `.env` (see `.env.example`). The ones worth touching:

| Variable | Default | Effect |
|---|---|---|
| `CHUNK_TOKENS` / `CHUNK_OVERLAP` | 512 / 50 | smaller = more precise retrieval, more chunks |
| `CANDIDATE_K` / `FINAL_K` | 20 / 5 | shortlist size and context size |
| `W_DENSE` / `W_RERANK` / `W_DIVERSITY` | 0.4 / 0.5 / 0.1 | late-fusion weights |
| `ENABLE_RERANK` | 1 | set `0` to reproduce the ablation in the report |
| `ENABLE_VISION_DESCRIBE` | 1 | set `0` to skip LLaVA (much faster image ingestion, worse text→image recall) |
| `LLM_MODEL` | `llama3.1` | `mistral` also works |

---

## Tests

```bash
cd backend && python -m pytest -q tests
```

These cover chunking, BM25, MMR and deduplication, and run without Qdrant,
Ollama or any model download.

---

## Known limitations

- The cross-encoder reranker is **text-only**, so image-to-image retrieval relies on
  dense similarity alone.
- Transcription accuracy degrades on heavily accented speech, overlapping speakers
  and non-English audio, and those errors propagate directly into retrieval.
- Embedding models are general-purpose; specialised domain vocabulary underperforms.
- OCR is not layout-aware, so multi-column and complex scanned layouts extract poorly.
- Index behaviour beyond ~100k chunks is untested; HNSW tuning would be needed there.
