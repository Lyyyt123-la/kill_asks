"""列出百炼上可用的视觉/嵌入模型。"""
from pathlib import Path

import httpx

env = Path(__file__).resolve().parent.parent / "backend" / ".env"
key = ""
for line in env.read_text(encoding="utf-8").splitlines():
    if line.strip().startswith("LLM_API_KEY="):
        key = line.split("=", 1)[1].strip()
        break

base = "https://dashscope.aliyuncs.com/compatible-mode/v1"
resp = httpx.get(f"{base}/models", headers={"Authorization": f"Bearer {key}"}, timeout=30)
ids = [m.get("id", "") for m in resp.json().get("data", [])]
vl = [i for i in ids if "vl" in i.lower() or "vision" in i.lower() or "ocr" in i.lower()]
embed = [i for i in ids if "embedding" in i.lower()]
print(f"total={len(ids)} vl={len(vl)} embedding={len(embed)}")
print("\n[视觉/OCR 模型]")
for model in vl:
    print("  -", model)
print("\n[嵌入模型]")
for model in embed:
    print("  -", model)
