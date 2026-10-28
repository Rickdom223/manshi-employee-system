#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd -- "${BASH_SOURCE[0]%/*}/.." && pwd)"
PY="$ROOT/backend/.venv/bin/python"
[[ -x "$PY" ]] || { echo '请先执行 python3 -m venv backend/.venv，并安装backend/requirements-lock.txt';exit 1; }
command -v nginx >/dev/null || { echo '缺少Nginx。请按部署说明安装，或明确选择 deploy/start-fallback.sh 备用方案。';exit 1; }
command -v npm >/dev/null || { echo '缺少Node/npm，请安装Node22.12+（自带npm）。';exit 1; }
cd "$ROOT/backend"
"$PY" -c 'from app.core.config import secret_key;secret_key()'
"$PY" -m alembic upgrade head
"$PY" -m app.scripts.init_data
cd "$ROOT/frontend"
npm ci
npm run build
cd "$ROOT"
mkdir -p "$ROOT/deploy/runtime"
"$PY" deploy/render_nginx.py
nginx -t -c "$ROOT/deploy/nginx.generated.conf"
"$PY" - <<'PY'
import os,socket
for port in [8000,int(os.getenv('PUBLIC_PORT','8080'))]:
    with socket.socket() as s:
        try:s.bind(('127.0.0.1',port))
        except OSError:raise SystemExit(f'端口{port}已占用，拒绝抢占或自动换端口')
PY
BACKEND_PID=''
cleanup(){ local result=$?;trap - EXIT INT TERM;if [[ -n "$BACKEND_PID" ]];then kill "$BACKEND_PID" 2>/dev/null||true;wait "$BACKEND_PID" 2>/dev/null||true;fi;exit "$result"; }
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
cd "$ROOT/backend"
"$PY" -m uvicorn app.main:app --host 127.0.0.1 --port 8000 &
BACKEND_PID=$!
"$PY" - <<'PY'
import time,urllib.request
for _ in range(50):
    try:
        with urllib.request.urlopen('http://127.0.0.1:8000/api/health',timeout=1) as r:
            if r.status==200:break
    except OSError:time.sleep(.2)
else:raise SystemExit('后端未就绪')
PY
kill -0 "$BACKEND_PID"
nginx -c "$ROOT/deploy/nginx.generated.conf" -g 'daemon off;'
