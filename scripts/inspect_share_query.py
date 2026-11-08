import json

import httpx

c = httpx.Client(timeout=180)
datasets = c.get("http://127.0.0.1:8000/api/datasets").json()
demo = [d for d in datasets if "双11" in d["name"]][0]
r = c.post("http://127.0.0.1:8000/api/chat", json={"dataset_id": demo["id"], "question": "各品类销售额占比", "history": []}).json()
print("columns:", r["result"]["columns"])
print("rows:", r["result"]["rows"][:6])
print("chart:", json.dumps(r.get("chart"), ensure_ascii=False))
print("sql:", (r.get("sql") or "")[:240])
