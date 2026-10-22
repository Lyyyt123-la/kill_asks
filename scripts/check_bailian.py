"""百炼（DashScope）模型探测：列出可用对话模型并测试几个候选模型的可用性/耗时。

不会打印 Key。用法：backend\\.venv\\Scripts\\python.exe scripts/check_bailian.py
"""
from __future__ import annotations

import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = ROOT / "backend" / ".env"
BASE = "https://dashscope.aliyuncs.com/compatible-mode/v1"

SKIP = ("embedding", "rerank", "image", "audio", "realtime", "asr", "tts", "omni", "video", "ocr", "vl-", "voice", "cosyvoice", "wanx")
PREFER = [
    "qwen3.8-max-0902", "qwen3.8-max", "qwen-max", "qwen3.8-plus", "qwen-plus",
    "deepseek-v4.1-flash-1017", "deepseek-v4.1", "deepseek-v3",
    "glm-5.3", "glm-4.7", "kimi-k2.8-preview", "qwen3.8-flash", "qwen-flash",
]


def read_key() -> str:
    for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        if line.strip().startswith("LLM_API_KEY="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


def main() -> None:
    key = read_key()
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    with httpx.Client(timeout=30) as client:
        resp = client.get(f"{BASE}/models", headers=headers)
        print("models status:", resp.status_code)
        ids = []
        if resp.status_code == 200:
            ids = [m.get("id", "") for m in resp.json().get("data", [])]
            print("model count:", len(ids))
            chat_models = [
                mid for mid in ids
                if not any(skip in mid.lower() for skip in SKIP)
                and any(k in mid.lower() for k in ("qwen", "deepseek", "glm", "kimi", "moonshot", "claude", "gpt"))
            ]
            print("\n可用对话模型（部分）:")
            for mid in chat_models[:60]:
                print("  -", mid)
        else:
            print(resp.text[:300])

        # 选出候选：优先表里存在的高质量模型
        candidates = []
        for want in PREFER:
            if want in ids:
                candidates.append(want)
        for mid in ids:
            low = mid.lower()
            if len(candidates) >= 6:
                break
            if any(skip in low for skip in SKIP):
                continue
            if any(k in low for k in ("qwen", "deepseek", "glm")):
                candidates.append(mid)
        candidates = list(dict.fromkeys(candidates))[:6]

        print("\n测试候选模型：")
        for model in candidates:
            payload = {
                "model": model,
                "messages": [
                    {"role": "system", "content": "你是一个 JSON 输出测试助手，只输出 JSON。"},
                    {"role": "user", "content": '只输出一个 JSON：{"ok": true}'},
                ],
                "temperature": 0.1,
                "max_tokens": 60,
            }
            started = time.time()
            try:
                r = client.post(f"{BASE}/chat/completions", headers=headers, json=payload)
                elapsed = int((time.time() - started) * 1000)
                if r.status_code == 200:
                    content = r.json().get("choices", [{}])[0].get("message", {}).get("content", "")
                    print(f"  ✅ {model:32s} {elapsed}ms  -> {content[:80]!r}")
                else:
                    print(f"  ❌ {model:32s} HTTP {r.status_code} -> {r.text[:160]}")
            except Exception as exc:  # noqa: BLE001
                print(f"  ❌ {model:32s} 连接失败: {type(exc).__name__}: {exc}")


if __name__ == "__main__":
    main()
