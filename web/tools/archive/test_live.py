import time
import requests

BASE = "https://liguijiang.com"

r = requests.get(BASE + "/", timeout=20)
print("GET / ->", r.status_code, "bytes:", len(r.content), "server:", r.headers.get("server"))
for h in ["content-security-policy", "x-frame-options", "cache-control", "content-type"]:
    print("  ", h, "=", (r.headers.get(h) or "")[:80])

r = requests.get(BASE + "/api/health", timeout=20)
print("health ->", r.status_code, r.text)

started = time.time()
with requests.post(
    BASE + "/api/chat",
    json={"messages": [{"role": "user", "content": "用一句话介绍你自己，不要超过 30 个字。"}], "model": "deepseek-chat"},
    stream=True,
    timeout=90,
    headers={"Accept": "text/event-stream"},
) as resp:
    print("chat ->", resp.status_code, resp.headers.get("content-type"), "x-accel:", resp.headers.get("x-accel-buffering"))
    chunks = 0
    text = ""
    for line in resp.iter_lines(decode_unicode=True):
        if not line:
            continue
        if line.startswith("event:"):
            event = line[6:].strip()
        elif line.startswith("data:"):
            data = line[5:].strip()
            if event == "delta":
                chunks += 1
                text += __import__("json").loads(data).get("t", "")
            elif event in ("error", "done"):
                print("  ", event, "->", data[:160])
print(f"stream chunks: {chunks}, first token latency ~{time.time()-started:.2f}s")
print("answer:", text.strip()[:200])