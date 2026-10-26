import json, requests
BASE = "https://liguijiang.com"
with requests.post(BASE + "/api/chat", json={
    "messages": [{"role": "user", "content": "你是谁开发的？团队里有哪些人？请用一句话回答。"}],
    "provider": "free",
}, stream=True, timeout=60) as r:
    text = ""
    err = None
    for line in r.iter_lines(decode_unicode=True):
        if not line or not line.startswith("data:"):
            continue
        try:
            obj = json.loads(line[5:].strip())
        except Exception:
            continue
        if obj.get("t"):
            text += obj["t"]
        if obj.get("message"):
            err = obj["message"]
print("status", r.status_code)
print("answer:", text.strip())
print("error:", err)