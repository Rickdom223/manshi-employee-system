#!/usr/bin/env bash
# Explicit fallback: FastAPI serves a previously built SPA. Use only when Nginx is unavailable.
set -Eeuo pipefail
ROOT="$(cd -- "${BASH_SOURCE[0]%/*}/.." && pwd)"
PY="$ROOT/backend/.venv/bin/python"
[[ -x "$PY" && -f "$ROOT/frontend/dist/index.html" ]] || { echo '请先安装后端依赖并执行frontend中的npm ci与npm run build';exit 1; }
cd "$ROOT/backend"
"$PY" -m alembic upgrade head
"$PY" -m app.scripts.init_data
APP_SERVE_STATIC=true exec "$PY" -m uvicorn app.main:app --host 0.0.0.0 --port "${PUBLIC_PORT:-8080}"
