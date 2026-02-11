#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${REPO_ROOT}"

# In most deployments the DB may come up slightly after the app starts.
bash "${SCRIPT_DIR}/wait_for_db.sh"

echo "Running migrations..."
if command -v poetry >/dev/null 2>&1; then
  poetry run alembic upgrade head
else
  alembic upgrade head
fi
echo "Migrations complete."

