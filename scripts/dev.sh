#!/usr/bin/env bash
# Starts the backend and the frontend dev server together.
set -euo pipefail
cd "$(dirname "$0")/.."

docker compose up -d >/dev/null 2>&1 || echo "warning: could not start Qdrant via docker compose"

./.venv/bin/uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000 --reload &
BACKEND=$!
trap 'kill $BACKEND 2>/dev/null || true' EXIT

(cd frontend && npm run dev)
