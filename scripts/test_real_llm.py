"""真实大模型链路测试（百炼 Qwen）：一次跑多类问题，输出 SQL / 图表 / 洞察 / 耗时。

用法：backend\\.venv\\Scripts\\python.exe scripts\\test_real_llm.py
"""
from __future__ import annotations

import json
import sys
import time

import httpx

BASE = "http://127.0.0.1:8000"
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

QUESTIONS = [
    "各区域的销售额对比",
    "2025年双11当天各小时销售额趋势",
    "销售额最低的3个品类",
    "各渠道的退款率排名",
    "最近30天的销售额趋势",
    "华东地区销售额最高的3个城市",
]


def main() -> None:
    with httpx.Client(base_url=BASE, timeout=180) as client:
        health = client.get("/api/health").json()
        print(f"LLM enabled={health['llm_enabled']} model={health['model']} mock={health['mock_mode']}")
        if health["mock_mode"]:
            print("⚠️ 当前仍是演示模式，请检查 backend/.env 的 Key / 模型配置")
            return
        test = client.post("/api/llm/test")
        print("llm test:", test.status_code, json.dumps(test.json(), ensure_ascii=False)[:200])

        demo = client.post("/api/datasets/demo").json()
        print(f"dataset: {demo.get('name')} rows={demo.get('rows')}")
        for col in demo.get("columns", []):
            if col.get("min_value"):
                print(f"  {col['name']}: {col['min_value']} ~ {col['max_value']}")

        for question in QUESTIONS:
            started = time.time()
            try:
                resp = client.post("/api/chat", json={
                    "dataset_id": "demo_double11",
                    "question": question,
                    "history": [],
                })
                elapsed = int((time.time() - started) * 1000)
                data = resp.json()
                print(f"\n===== Q: {question} =====")
                print(f"http={resp.status_code} elapsed={elapsed}ms intent={data.get('intent')} mock={data.get('mock')} "
                      f"attempts={data.get('attempts')} model={data.get('model')}")
                if data.get("error"):
                    print("error:", str(data["error"])[:300])
                print("plan:", data.get("plan"))
                print("sql:", (data.get("sql") or "")[:600])
                chart = data.get("chart") or {}
                print("chart:", chart.get("type"), "| x:", chart.get("x"), "| y:", chart.get("y"))
                result = data.get("result") or {}
                print("cols:", result.get("columns"))
                print("rows:", json.dumps(result.get("rows", [])[:4], ensure_ascii=False))
                ins = data.get("insight") or {}
                print("insight:", ins.get("headline"))
                for bullet in ins.get("bullets", [])[:3]:
                    print("   -", bullet)
                if data.get("clarification"):
                    print("clarify:", data["clarification"])
            except Exception as exc:  # noqa: BLE001
                print(f"\n===== Q: {question} =====\n请求失败：{exc}")


if __name__ == "__main__":
    main()
