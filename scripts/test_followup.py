"""验证多轮追问与澄清问法（真实模型）。"""
from __future__ import annotations

import json
import sys

import httpx

BASE = "http://127.0.0.1:8000"
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")


def ask(client, question, history):
    resp = client.post("/api/chat", json={
        "dataset_id": "demo_double11",
        "question": question,
        "history": history,
    })
    return resp.json()


def brief(data):
    print(f"  intent={data.get('intent')} mock={data.get('mock')} attempts={data.get('attempts')} elapsed={data.get('elapsed_ms')}ms")
    print(f"  sql = {(data.get('sql') or '')[:260]}")
    result = data.get("result") or {}
    print(f"  cols={result.get('columns')} rows={json.dumps(result.get('rows', [])[:3], ensure_ascii=False)}")
    ins = data.get("insight") or {}
    print(f"  insight = {ins.get('headline')}")
    if data.get("clarification"):
        print(f"  clarify = {data['clarification']}")


def main() -> None:
    with httpx.Client(base_url=BASE, timeout=180) as client:
        print("=== 多轮上下文：先问小时趋势，再问“那华东呢” ===")
        first = ask(client, "2025年双11当天各小时销售额趋势", [])
        brief(first)
        history = [{
            "question": "2025年双11当天各小时销售额趋势",
            "sql": first.get("sql"),
            "columns": (first.get("result") or {}).get("columns", []),
            "summary": (first.get("insight") or {}).get("headline"),
        }]
        second = ask(client, "那华东呢？", history)
        brief(second)

        print("\n=== 澄清问法：最近卖得怎么样 ===")
        brief(ask(client, "最近卖得怎么样", []))

        print("\n=== 复杂归因：哪个渠道退款率最高，可能是什么原因 ===")
        brief(ask(client, "哪个渠道退款率最高，可能是什么原因", []))


if __name__ == "__main__":
    main()
