#!/usr/bin/env bash
# 容器每次启动时执行：后台启动 FastAPI 服务（单端口 8000，同时托管前端）。
set -euo pipefail
cd "$(dirname "$0")/.."

if curl -sf http://127.0.0.1:8000/api/health >/dev/null 2>&1; then
  echo "AskData 已在运行：http://127.0.0.1:8000"
  exit 0
fi

cd backend
nohup .venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 \
  > /tmp/askdata-codespaces.log 2>&1 &

for _ in $(seq 1 40); do
  sleep 1
  if curl -sf http://127.0.0.1:8000/api/health >/dev/null 2>&1; then
    echo "AskData 已启动：http://127.0.0.1:8000"
    exit 0
  fi
done

echo "启动失败，最近日志："
tail -50 /tmp/askdata-codespaces.log || true
exit 1
