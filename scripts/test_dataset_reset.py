import httpx

BASE = "http://127.0.0.1:8000"
csv = "区域,销售额\n华东,100\n华南,80\n".encode("utf-8")
with httpx.Client(timeout=120) as c:
    up = c.post(BASE + "/api/datasets/upload", files={"file": ("reset_test.csv", csv, "text/csv")}).json()
    print("uploaded:", up["id"], up["name"], up["rows"])
    reset = c.post(BASE + f"/api/datasets/{up['id']}/reset")
    print("reset status:", reset.status_code)
    data = reset.json()
    print("after reset:", data.get("id"), data.get("name"), data.get("rows"), data.get("source_file"))
    c.delete(BASE + f"/api/datasets/{up['id']}")
    print("cleanup ok")
