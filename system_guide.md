# System Guide — Offline Multimodal RAG

A living reference for how this project actually works: architecture, every model in the pipeline, current configuration, and the metrics that exist for it (both from the original project report and from live testing done in this session).

---

## 1. What this system does

A fully offline Retrieval-Augmented Generation platform that ingests **PDF, DOCX, TXT, images (PNG/JPG), and audio (WAV/MP3)** into a single searchable index, and answers natural-language questions with citation-backed responses — with no network call at runtime after the one-time model download.

Six pipeline stages: **ingest → embed → index → retrieve → generate → present.**

---

## 2. Architecture at a glance

```
                     ┌─────────────────────────────────────────┐
                     │              React Frontend              │
                     │  Dashboard · Knowledge Base · Chat ·      │
                     │  Processor Lab · System Status · Arch     │
                     └───────────────────┬───────────────────────┘
                                          │ HTTP (127.0.0.1:5173 → :8000)
                     ┌───────────────────▼───────────────────────┐
                     │             FastAPI Backend                │
                     │   /ingest   /query   /index   /status      │
                     └──┬────────┬─────────┬─────────┬────────────┘
                        │        │         │         │
                 ┌──────▼───┐ ┌──▼─────┐ ┌─▼───────┐ ┌▼──────────┐
                 │ Ingest   │ │Embed   │ │Retrieve │ │ Generate  │
                 │ Layer    │ │Layer   │ │Layer    │ │ Layer     │
                 └──────────┘ └────────┘ └─────────┘ └───────────┘
                        │        │         │              │
                 ┌──────▼────────▼───┐ ┌───▼──────┐  ┌────▼─────┐
                 │  SQLite registry   │ │ Qdrant   │  │  Ollama  │
                 │ (docs/chunks/log)  │ │(vectors) │  │ (LLM)    │
                 └────────────────────┘ └──────────┘  └──────────┘
```

Code layout (`backend/app/`):
- `ingest/` — `pdf_loader.py`, `docx_loader.py`, `image_loader.py`, `audio_loader.py`, `router.py` (MIME dispatch), `chunker.py` (sliding window)
- `embeddings/` — `text_encoder.py`, `image_encoder.py`, `vision_describe.py` (vision-language captioning)
- `store/` — Qdrant client + SQLite registry + UUID5 dedup
- `retrieval/` — `bm25.py`, `mmr.py`, `reranker.py`, `pipeline.py` (fusion + scoring, the core logic)
- `generation/` — `prompt_builder.py`, `ollama_client.py`
- `routers/` — `ingest.py`, `query.py`, `index.py`, `status.py`

---

## 3. Every model in the pipeline

| Stage | Model | Dim / Size | Purpose |
|---|---|---|---|
| Text embedding | `sentence-transformers/all-MiniLM-L6-v2` | 384-d | Encodes document-length text chunks (and OCR/transcript text) for dense search |
| Image embedding | `open_clip ViT-B/32` (laion2b_s34b_b79k) | 512-d | Encodes images for dense visual search; also encodes the text query into the same space for cross-modal search |
| Vision captioning | **`qwen2.5vl:3b`** (via Ollama) | 3.8B | Generates a natural-language description of each ingested image at index time; that caption is embedded as *text*, giving every image both a visual and a semantic-text representation |
| Reranking | `cross-encoder/ms-marco-MiniLM-L-6-v2` | — | Cross-encodes query+candidate jointly for precise relevance scoring on the top-20 shortlist (text-only — does not rerank image-to-image) |
| Speech-to-text | `faster-whisper large-v3` (int8 quantised) | — | Transcribes audio with segment-level timestamps |
| Answer generation | **`qwen2.5:3b`** (via Ollama) | 3.1B | Produces the final grounded, cited answer from retrieved context |

**Note on model history:** the original project report (Phase-I submission) was benchmarked against **Llama 3.1 8B (4-bit)** for generation and **LLaVA** for vision, per `.env.example`. The `.env` in this repo has since been switched to the smaller, faster **Qwen2.5 family** (`qwen2.5:3b` / `qwen2.5vl:3b`) — both already pulled locally in Ollama. All live results in §6 below are from testing this Qwen configuration, not the original Llama/LLaVA pairing the report's benchmark table describes.

---

## 4. Retrieval pipeline — how a query actually gets answered

1. **Query encoding** — the query is encoded three ways: into the 384-d text space (dense), tokenized for BM25 (sparse), and — if image results are allowed — into the 512-d CLIP space via CLIP's text tower.
2. **Dense search** — top `candidate_k` (default 20) nearest neighbors are pulled independently from each named vector space in Qdrant (`text`, `image`).
3. **Fusion** — dense scores are min-max normalized and combined with BM25 sparse scores: `fused = 0.65 * dense_norm + 0.35 * sparse_norm`.
4. **MMR diversification** — Maximal Marginal Relevance (`mmr_lambda = 0.7`) suppresses near-duplicate candidates from the fused shortlist.
5. **Cross-encoder reranking** — `ms-marco-MiniLM` jointly scores query+candidate for the shortlist (text-only signal).
6. **Late fusion** — final score per candidate: `final = w_dense * dense_norm + w_rerank * rerank_norm + w_diversity * modality_bonus` (defaults: 0.4 / 0.5 / 0.1).
7. **Per-modality slot reservation** *(added this session — see §7)* — before truncating to `top_k`, one slot is reserved for the best candidate of each modality present in the shortlist, then remaining slots are filled by raw score. This prevents a modality with a structurally lower score scale (e.g. CLIP image similarity) from being squeezed out entirely on compound/cross-modal queries.
8. **Grounded generation** — the surviving chunks are numbered and serialized into a prompt (`prompt_builder.py`) with a system instruction to answer only from context, cite every claim `[n]`, and explicitly refuse when the context doesn't support an answer. Sent to `qwen2.5:3b` via Ollama at `temperature=0.1`, `top_p=0.9`.

Config knobs (`.env` / `backend/app/config.py`): `CHUNK_TOKENS=512`, `CHUNK_OVERLAP=50`, `CANDIDATE_K=20`, `FINAL_K=5`, `W_DENSE=0.4`, `W_RERANK=0.5`, `W_DIVERSITY=0.1`, `MMR_LAMBDA=0.7`, `MAX_CONTEXT_TOKENS=6000`.

---

## 5. Storage

- **Qdrant** (local Docker, `127.0.0.1:6333`) — one collection `multimodal_rag` with two named vectors (`text` @ 384-d, `image` @ 512-d, both cosine). Points are keyed by a UUID5 hash of normalized chunk content → re-ingesting an unchanged file is a no-op.
- **SQLite** (`data/registry.db`) — three tables:
  - `documents` — doc_id, filename, path, SHA-256 hash, size, modality, chunk_count, timestamps
  - `chunks` — chunk_id, doc_id, modality, source_file, page_number, start/end_time (audio), image_path, chunk_text, linked_chunks
  - `queries` — logged query text, retrieved chunk IDs, generated answer, response time (this is the running query log, useful for your own eval later)

---

## 6. Metrics

### 6a. From the original project report (Llama 3.1 8B + LLaVA, benchmark corpus: 150 docs / 2,847 chunks / 500 queries, Apple M2 16GB, no GPU)

**Retrieval accuracy by query type (top-5):**

| Query type | Queries | Top-5 Accuracy | Note |
|---|---|---|---|
| Text-to-text | 200 | 91.5% | Strongest path; benefits most from BM25 fusion |
| Text-to-image | 100 | 85.0% | Aided by vision-caption text surrogate |
| Text-to-audio | 120 | 83.1% | Limited mainly by transcription errors |
| Image-to-text | 50 | 84.3% | Cross-modal sibling links improve recall |
| Hybrid/mixed | 30 | 86.0% | Diversity bonus keeps modalities represented |
| **Overall** | **500** | **87.6%** | Weighted across all query types |

**Latency & throughput:**

| Measurement | Result |
|---|---|
| Avg. end-to-end query latency | 3.4 s (σ = 0.8 s) |
| Text ingestion throughput | 180 chunks/min |
| Image ingestion throughput | 45 images/min |
| Audio transcription throughput | 12 min audio/min |
| Index size | ~30 MB per 10,000 chunks |
| Model weights on disk | ~5.4 GB total |

**Reranker ablation:**

| Configuration | Top-5 Accuracy | Avg. Latency |
|---|---|---|
| Dense retrieval only | 80.1% | 2.4 s |
| + BM25 fusion + MMR | 83.4% | 2.8 s |
| + cross-encoder rerank (full pipeline) | 87.6% | 3.4 s |

Reranking costs +0.6s/query for +4.2pp accuracy — the report's stated justification for keeping it on.

### 6b. Live testing this session (Qwen2.5:3b + Qwen2.5vl:3b, this machine, small 3-doc corpus)

No formal benchmark corpus has been run against Qwen yet — these are targeted correctness/latency spot-checks, not a statistical eval:

| Test | Result |
|---|---|
| Text query (project doc) | Accurate, cited answer. ~23s cold generation, ~4-9s warm |
| Audio query, off-topic distractor ("oak") | Correctly refused — no hallucination |
| Audio query, on-topic | Correct, cited, 3.7s |
| Image query (vision caption retrieval) | Accurate, cited, ~13s |
| Multi-fact synthesis (hardware specs + ablation numbers) | Correct; verified numbers against source — no hallucination |
| Trap question (false cross-topic link) | Correctly declined the fabricated connection |
| Compound cross-modal query (audio + image in one question) | **Failed initially** — image evidence was retrieved by CLIP but ranked below the top-8 cutoff due to score-scale mismatch between CLIP similarity and text dense similarity; fixed by the pipeline change in §7, now passes |
| Query with no true answer in corpus (video support, aggregate audio duration) | Correctly refused both times |

**Known limitation carried over unfixed:** when a modality is entirely absent from the top-ranked context for a genuinely out-of-scope question (rather than just under-ranked), `qwen2.5:3b` doesn't always follow the exact refusal template — it can produce a plausible-sounding but ungrounded excuse instead of the literal "the indexed sources do not contain an answer" string. Worth stress-testing more before relying on this for a demo; not yet fixed.

---

## 7. Change log (fixes made in this session)

**`backend/app/retrieval/pipeline.py` — per-modality slot reservation.** Root cause: CLIP text→image similarity for a genuinely matching image scores ~0.13, while text→text MiniLM similarity for loosely-related passages scores ~0.23–0.31. Since all candidates were min-max normalized together in one pool, image (and by extension audio) candidates got squeezed toward the bottom on any query where relevant text chunks competed, especially compound/multi-intent queries where a single query embedding has to represent two topics at once. The flat `w_diversity=0.1` bonus wasn't enough to compensate. Fix: reserve one slot in the final top-k for the best-scoring candidate of each modality present in the post-rerank shortlist, then fill remaining slots by score as before. Verified: an image chunk that previously ranked 17th of 20 (dropped from any top_k ≤ 16) now surfaces correctly for compound cross-modal queries, with no regression on the other test queries.

---

## 8. Running it

```bash
# one-time setup
./scripts/setup.sh

# every time
./scripts/dev.sh
# or manually:
docker compose up -d                                             # Qdrant
uvicorn app.main:app --app-dir backend --port 8000 --reload      # backend
cd frontend && npm run dev                                       # frontend
```

Then open **http://127.0.0.1:5173**. Check `/status` (backend) or the System Status view (frontend) to verify all dependencies (Qdrant, Ollama, ffmpeg, tesseract, SQLite) are healthy before testing.

Currently indexed test corpus: `Offline_Multimodal_RAG_Project_Report.docx` (24 text chunks), `DSC_9187.jpg` (1 image chunk), `harvard.wav` (6 audio chunks, 6 Harvard sentences).
