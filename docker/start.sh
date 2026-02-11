#!/usr/bin/env bash
set -euo pipefail

HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8000}"

if command -v poetry >/dev/null 2>&1; then
  exec poetry run uvicorn app.main:app --host "${HOST}" --port "${PORT}"
fi

exec uvicorn app.main:app --host "${HOST}" --port "${PORT}"

