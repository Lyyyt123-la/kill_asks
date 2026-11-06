# -*- coding: utf-8 -*-
"""测试阿里云百炼 TTS（OpenAI 兼容 audio/speech 或 dashscope SDK）是否可用。"""
import os
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent
env_path = ROOT / "backend" / ".env"
key = ""
for line in env_path.read_text(encoding="utf-8", errors="ignore").splitlines():
    if line.strip().startswith("LLM_API_KEY="):
        key = line.split("=", 1)[1].strip()
        break
if not key:
    print("NO_KEY")
    raise SystemExit(1)

base = "https://dashscope.aliyuncs.com/compatible-mode/v1"
headers = {"Authorization": f"Bearer {key}"}

candidates = [
    {"model": "qwen-tts", "voice": "Cherry", "input": "你好，这是问数 AskData 的演示配音。"},
    {"model": "qwen3-tts-flash", "voice": "Cherry", "input": "你好，这是问数 AskData 的演示配音。"},
    {"model": "cosyvoice-v2", "voice": "longxiaochun_v2", "input": "你好，这是问数 AskData 的演示配音。"},
]
out = Path("D:/dsworking/tts_test")
out.mkdir(parents=True, exist_ok=True)
for index, payload in enumerate(candidates):
    for endpoint in ("/audio/speech", "/audio/generations"):
        try:
            response = httpx.post(base + endpoint, headers=headers, json=payload, timeout=60)
            print(payload["model"], endpoint, "status", response.status_code, "len", len(response.content))
            if response.status_code == 200 and len(response.content) > 1000:
                target = out / f"tts_{index}.mp3"
                target.write_bytes(response.content)
                print("SAVED", target)
                raise SystemExit(0)
            if response.status_code != 200:
                print("body:", response.text[:200])
        except Exception as exc:  # noqa: BLE001
            print(payload["model"], endpoint, "ERR", type(exc).__name__, str(exc)[:150])
print("ALL_FAILED")
