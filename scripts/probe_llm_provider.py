"""探测 backend/.env 里的 LLM_API_KEY 属于哪个 OpenAI 兼容平台。

只用于排查配置：不会打印 Key 本体，只打印各平台 /models 的状态码与可用模型名。
用法：backend\\.venv\\Scripts\\python.exe scripts\\probe_llm_provider.py
"""
from __future__ import annotations

import os
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = ROOT / "backend" / ".env"

CANDIDATES = [
    ("硅基流动 SiliconFlow", "https://api.siliconflow.cn/v1"),
    ("302.AI", "https://api.302.ai/v1"),
    ("AiHubMix", "https://aihubmix.com/v1"),
    ("OhMyGPT", "https://api.ohmygpt.com/v1"),
    ("API2D", "https://openai.api2d.net/v1"),
    ("DeepSeek", "https://api.deepseek.com/v1"),
    ("通义 DashScope", "https://dashscope.aliyuncs.com/compatible-mode/v1"),
    ("Kimi Moonshot", "https://api.moonshot.cn/v1"),
    ("OpenAI", "https://api.openai.com/v1"),
    ("智谱 BigModel", "https://open.bigmodel.cn/api/paas/v4"),
    ("OpenRouter", "https://openrouter.ai/api/v1"),
    ("ChatAnywhere", "https://api.chatanywhere.tech/v1"),
    ("GPTsAPI", "https://api.gptsapi.net/v1"),
    ("AIGC2D", "https://api.aigc2d.com/v1"),
    ("MetaSo", "https://api.metaso.cn/v1"),
]


def read_key() -> str:
    for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        if line.strip().startswith("LLM_API_KEY="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


def main() -> None:
    key = read_key()
    if not key:
        print("backend/.env 中没有 LLM_API_KEY")
        return
    print(f"Key 长度: {len(key)}，前缀: {key[:4]}****")

    for name, base in CANDIDATES:
        url = base.rstrip("/") + "/models"
        try:
            resp = httpx.get(url, headers={"Authorization": f"Bearer {key}"}, timeout=8)
        except Exception as exc:  # noqa: BLE001
            print(f"[{name:16s}] 连接失败: {type(exc).__name__}")
            continue
        if resp.status_code == 200:
            try:
                data = resp.json()
                models = [m.get("id") for m in data.get("data", []) if m.get("id")]
            except Exception:  # noqa: BLE001
                models = []
            print(f"[{name:16s}] ✅ 200，可用模型 {len(models)} 个")
            interesting = [m for m in models if any(k in m.lower() for k in ("deepseek", "qwen", "glm", "gpt-4", "claude", "kimi", "moonshot"))]
            for model_id in interesting[:20]:
                print("    -", model_id)
        else:
            print(f"[{name:16s}] HTTP {resp.status_code}")


if __name__ == "__main__":
    main()
