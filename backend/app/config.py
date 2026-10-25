"""全局配置：路径、LLM、限制参数。所有密钥只从环境变量读取，绝不写进代码。"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parent.parent      # backend/
PROJECT_ROOT = BACKEND_DIR.parent                          # 仓库根目录
DATA_DIR = BACKEND_DIR / "data"
UPLOADS_DIR = DATA_DIR / "uploads"
DATASETS_DIR = DATA_DIR / "datasets"
META_DB_PATH = DATA_DIR / "meta.db"
FRONTEND_DIST = PROJECT_ROOT / "frontend" / "dist"

load_dotenv(BACKEND_DIR / ".env")

# ---------------- LLM ----------------
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://open.bigmodel.cn/api/paas/v4").strip()
LLM_API_KEY = os.getenv("LLM_API_KEY", "").strip()
LLM_MODEL = os.getenv("LLM_MODEL", "glm-4-flash").strip()
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.1"))
LLM_TIMEOUT_S = float(os.getenv("LLM_TIMEOUT_S", "60"))

# mock: auto = 没有 key 时自动进入演示模式；on/off 强制开关
MOCK_MODE = os.getenv("MOCK_MODE", "auto").strip().lower()

# ---------------- 限制 ----------------
MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "30"))
MAX_ROWS = int(os.getenv("MAX_ROWS", "1000"))
QUERY_TIMEOUT_S = int(os.getenv("QUERY_TIMEOUT_S", "15"))
MAX_RETRY = int(os.getenv("MAX_RETRY", "2"))
MAX_HISTORY_TURNS = int(os.getenv("MAX_HISTORY_TURNS", "3"))

# ---------------- 文档 / 图片解析（RAG & Vision） ----------------
MAX_DOC_MB = int(os.getenv("MAX_DOC_MB", "20"))
DOC_DIR = DATA_DIR / "documents"
VISION_MODEL = os.getenv("VISION_MODEL", "qwen3-vl-plus").strip()
EMBED_MODEL = os.getenv("EMBED_MODEL", "qwen3.7-text-embedding-flash").strip()
RAG_TOP_K = int(os.getenv("RAG_TOP_K", "5"))
RAG_CHUNK_SIZE = int(os.getenv("RAG_CHUNK_SIZE", "420"))
RAG_CHUNK_OVERLAP = int(os.getenv("RAG_CHUNK_OVERLAP", "80"))

# ---------------- 公网部署保护 ----------------
APP_ACCESS_CODE = os.getenv("APP_ACCESS_CODE", "").strip()
RATE_LIMIT_PER_MIN = int(os.getenv("RATE_LIMIT_PER_MIN", "0"))

# ---------------- 数据 ----------------
DEMO_DATASET_ID = "demo_double11"
DEMO_DATASET_NAME = "双11大促销售数据（示例）"
DEMO_DATASET_FILE = PROJECT_ROOT / "demo_data" / "double11_sales.csv"


def ensure_dirs() -> None:
    for d in (DATA_DIR, UPLOADS_DIR, DATASETS_DIR, DOC_DIR):
        d.mkdir(parents=True, exist_ok=True)


def llm_enabled() -> bool:
    if MOCK_MODE == "on":
        return False
    if MOCK_MODE == "off":
        return True
    return bool(LLM_API_KEY)
