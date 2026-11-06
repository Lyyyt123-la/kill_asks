#!/usr/bin/env bash
# 在 GitHub Codespaces / Dev Container 中首次创建时执行：
# 安装后端依赖、构建前端、写入模型 Key（可选）。
set -euo pipefail
cd "$(dirname "$0")/.."

echo "==> [1/3] 创建 Python 虚拟环境并安装后端依赖 ..."
python -m venv backend/.venv
backend/.venv/bin/pip install --disable-pip-version-check -q --timeout 120 \
  -i https://pypi.tuna.tsinghua.edu.cn/simple \
  -r backend/requirements.txt

echo "==> [2/3] 安装前端依赖并构建（首次约 1-2 分钟）..."
cd frontend
npm install --no-audit --no-fund
npm run build
cd ..

echo "==> [3/3] 写入环境变量 ..."
if [ ! -f backend/.env ]; then
  cp backend/.env.example backend/.env
fi
# Codespaces Secret：LLM_API_KEY（没有则保持演示模式）
if [ -n "${LLM_API_KEY:-}" ]; then
  python - <<'PY'
from pathlib import Path
path = Path('backend/.env')
lines = path.read_text(encoding='utf-8').splitlines()
key = __import__('os').environ['LLM_API_KEY']
updated = []
found = False
for line in lines:
    if line.startswith('LLM_API_KEY='):
        updated.append(f'LLM_API_KEY={key}')
        found = True
    else:
        updated.append(line)
if not found:
    updated.append(f'LLM_API_KEY={key}')
path.write_text('\n'.join(updated) + '\n', encoding='utf-8')
print('LLM_API_KEY 已写入 backend/.env')
PY
else
  echo "未检测到 LLM_API_KEY，将以演示模式运行（界面与图表完整可用）。"
fi

echo "==> 初始化完成。稍后容器启动时会自动运行服务。"
