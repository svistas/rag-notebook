#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${DATABASE_URL:-}" ]]; then
  echo "DATABASE_URL is not set; skipping DB wait."
  exit 0
fi

TIMEOUT_SECONDS="${DB_WAIT_TIMEOUT_SECONDS:-60}"
SLEEP_SECONDS="${DB_WAIT_SLEEP_SECONDS:-2}"

echo "Waiting for DB (timeout=${TIMEOUT_SECONDS}s)..."

start_ts="$(date +%s)"
while true; do
  if python - <<'PY'
import os
import sys

from sqlalchemy import create_engine, text

url = os.environ.get("DATABASE_URL")
engine = create_engine(url, pool_pre_ping=True)
try:
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
except Exception:
    sys.exit(1)
sys.exit(0)
PY
  then
    echo "DB is ready."
    exit 0
  fi

  now_ts="$(date +%s)"
  elapsed="$((now_ts - start_ts))"
  if [[ "${elapsed}" -ge "${TIMEOUT_SECONDS}" ]]; then
    echo "DB did not become ready within ${TIMEOUT_SECONDS}s."
    exit 1
  fi

  sleep "${SLEEP_SECONDS}"
done

