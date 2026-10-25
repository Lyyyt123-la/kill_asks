"""文档/图片解析与 RAG 问答测试：上传 PDF / Word / 图片，验证表格提取与问答。"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import httpx

BASE = "http://127.0.0.1:8000"
ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "demo_data" / "documents"
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

FILES = [
    ("2025年Q3经营情况报告.pdf", "这份报告里华东区 Q3 的销售额和同比是多少？"),
    ("双11大促复盘摘要.docx", "双11当天销售额是多少？占大促总销售额的比例是多少？"),
    ("各渠道退款率截图.png", "截图里哪个渠道退款率最高？是多少？"),
]


def main() -> None:
    with httpx.Client(base_url=BASE, timeout=240) as client:
        print("health:", client.get("/api/health").json().get("model"))
        for filename, question in FILES:
            path = DOCS / filename
            if not path.exists():
                print(f"跳过（文件不存在）：{path}")
                continue
            print(f"\n===== 上传：{filename} =====")
            started = time.time()
            with path.open("rb") as handle:
                resp = client.post("/api/documents/upload", files={"file": (filename, handle)})
            elapsed = int((time.time() - started) * 1000)
            print(f"http={resp.status_code} elapsed={elapsed}ms")
            if resp.status_code != 200:
                print(resp.text[:500])
                continue
            doc = resp.json()
            print(f"doc={doc['id']} type={doc['file_type']} chars={doc['chars']} chunks={doc['chunks']}")
            print(f"tables={json.dumps(doc['tables'], ensure_ascii=False)}")
            print(f"preview={doc['text_preview'][:160]!r}")

            print(f"--- 提问：{question}")
            started = time.time()
            ask = client.post(f"/api/documents/{doc['id']}/ask", json={"question": question})
            elapsed = int((time.time() - started) * 1000)
            data = ask.json()
            print(f"http={ask.status_code} elapsed={elapsed}ms model={data.get('model')} mock={data.get('mock')}")
            print("answer:", (data.get("answer") or "")[:500])
            for citation in (data.get("citations") or [])[:3]:
                print(f"  [{citation['index']}] {citation['text'][:90]}")


if __name__ == "__main__":
    main()
