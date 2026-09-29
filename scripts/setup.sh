#!/usr/bin/env bash
# One-time setup. After this runs, the system needs no network connection.
set -euo pipefail
cd "$(dirname "$0")/.."

say() { printf '\n\033[1;34m==>\033[0m %s\n' "$1"; }
need() { command -v "$1" >/dev/null 2>&1 || { echo "missing: $1 ($2)"; MISSING=1; }; }

MISSING=0
say "Checking system dependencies"
need python3 "install Python 3.10+"
need node    "install Node.js 18+"
need docker  "needed to run Qdrant locally"
need ffmpeg  "brew install ffmpeg  |  apt install ffmpeg"
need tesseract "brew install tesseract  |  apt install tesseract-ocr"
command -v ollama >/dev/null 2>&1 || echo "note: ollama not found — install from https://ollama.com"
[ "$MISSING" = "1" ] && { echo "Install the missing tools above, then re-run."; exit 1; }

say "Creating the Python virtual environment"
[ -d .venv ] || python3 -m venv .venv
./.venv/bin/pip install --upgrade pip >/dev/null
./.venv/bin/pip install -r backend/requirements.txt

say "Installing frontend dependencies"
(cd frontend && npm install)

say "Starting Qdrant"
docker compose up -d

say "Pulling local models through Ollama (one-time download)"
if command -v ollama >/dev/null 2>&1; then
  ollama pull llama3.1 || true
  ollama pull llava    || true
else
  echo "skipped — install Ollama, then run: ollama pull llama3.1 && ollama pull llava"
fi

say "Warming the embedding, reranker and transcription caches"
./.venv/bin/python - <<'PY'
from sentence_transformers import SentenceTransformer, CrossEncoder
SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
import open_clip
open_clip.create_model_and_transforms("ViT-B-32", pretrained="laion2b_s34b_b79k")
from faster_whisper import WhisperModel
WhisperModel("large-v3", device="auto", compute_type="int8")
print("all model weights cached locally")
PY

[ -f .env ] || cp .env.example .env
say "Setup complete. Run ./scripts/dev.sh to start the system."
