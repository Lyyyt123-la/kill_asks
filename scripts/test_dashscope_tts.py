# -*- coding: utf-8 -*-
"""测试 DashScope 语音合成（tts_v2 WebSocket）。"""
from pathlib import Path

import dashscope
from dashscope.audio.tts_v2 import SpeechSynthesizer

ROOT = Path(__file__).resolve().parent.parent
key = ""
for line in (ROOT / "backend" / ".env").read_text(encoding="utf-8", errors="ignore").splitlines():
    if line.strip().startswith("LLM_API_KEY="):
        key = line.split("=", 1)[1].strip()
        break
dashscope.api_key = key
out_dir = Path("D:/dsworking/tts_test")
out_dir.mkdir(parents=True, exist_ok=True)

candidates = [
    ("cosyvoice-v2", "longxiaochun_v2"),
    ("cosyvoice-v1", "longxiaochun"),
    ("qwen-tts", "Cherry"),
]
for model, voice in candidates:
    try:
        synthesizer = SpeechSynthesizer(model=model, voice=voice)
        audio = synthesizer.call("你好，这是问数 AskData 的演示配音。")
        if audio and len(audio) > 1000:
            target = out_dir / f"dashscope_{model}.mp3"
            target.write_bytes(audio)
            print("OK", model, voice, len(audio), "->", target)
            break
        print("EMPTY", model, voice, type(audio), len(audio or b""))
    except Exception as exc:  # noqa: BLE001
        print("FAIL", model, voice, type(exc).__name__, str(exc)[:250])
