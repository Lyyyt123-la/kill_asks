import json

import httpx

c = httpx.Client(timeout=180)
datasets = c.get("http://127.0.0.1:8000/api/datasets").json()
demo = [d for d in datasets if "双11" in d["name"]][0]
for question in ["各区域各渠道的退款率", "各区域各渠道销售额"]:
    r = c.post("http://127.0.0.1:8000/api/chat", json={"dataset_id": demo["id"], "question": question, "history": []}).json()
    print("Q:", question)
    print(" columns:", r["result"]["columns"])
    rows = r["result"]["rows"]
    print(" rows:", len(rows), "first:", rows[:4])
    # 检查重复 (x,y)
    if len(r["result"]["columns"]) >= 3:
        cols = r["result"]["columns"]
        pairs = [(str(row[0]), str(row[1])) for row in rows]
        print(" unique pairs:", len(set(pairs)), "duplicates:", len(pairs) - len(set(pairs)))
    print(" chart:", json.dumps(r.get("chart"), ensure_ascii=False))
