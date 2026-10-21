"""后端 API 冒烟测试（不依赖模型 Key，可直接跑通演示模式）。

用法：
  backend\\.venv\\Scripts\\python.exe scripts\\test_api.py
"""
from __future__ import annotations

import json
import sys

import httpx

BASE = "http://127.0.0.1:8000"
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")


def show(title: str, data: dict) -> None:
    print(f"\n===== {title} =====")
    print(json.dumps(data, ensure_ascii=False, indent=2)[:1600])


def main() -> None:
    with httpx.Client(base_url=BASE, timeout=120) as client:
        health = client.get("/api/health").json()
        show("health", health)

        demo = client.post("/api/datasets/demo").json()
        print("\n===== demo dataset =====")
        print(demo.get("name"), demo.get("rows"), "rows")
        for col in demo.get("columns", []):
            print(f"  {col['name']:12s} {col['dtype']:10s} samples={col['samples'][:2]}")

        preview = client.get("/api/datasets/demo_double11/preview", params={"limit": 3}).json()
        show("preview", preview)

        questions = [
            "各区域的销售额对比",
            "双11当天各小时销售额趋势",
            "销售额最高的5个品类",
            "各渠道的退款率排名",
        ]
        for question in questions:
            resp = client.post("/api/chat", json={
                "dataset_id": "demo_double11",
                "question": question,
                "history": [],
            })
            data = resp.json()
            print(f"\n===== Q: {question} =====")
            print("ok:", data.get("ok"), "| intent:", data.get("intent"), "| mock:", data.get("mock"),
                  "| model:", data.get("model"))
            if data.get("error"):
                print("error:", data["error"])
            print("plan:", data.get("plan"))
            print("sql :", data.get("sql"))
            chart = data.get("chart") or {}
            print("chart:", chart.get("type"), "| x:", chart.get("x"), "| y:", chart.get("y"))
            result = data.get("result") or {}
            print("cols:", result.get("columns"))
            print("rows:", json.dumps(result.get("rows", [])[:3], ensure_ascii=False))
            ins = data.get("insight") or {}
            print("insight:", ins.get("headline"))
            for bullet in ins.get("bullets", []):
                print("   -", bullet)
            print("followups:", ins.get("followups"))
            print("steps:", [(s["label"], s["detail"]) for s in data.get("steps", [])])

        # 安全检查：危险 SQL 必须被拦截
        bad = client.post("/api/query", json={
            "dataset_id": "demo_double11",
            "sql": "DROP TABLE demo_double11;",
        })
        print("\n===== guard test =====")
        print("status:", bad.status_code, "detail:", bad.json().get("detail"))


if __name__ == "__main__":
    main()
