import json, time, requests

BASE = "https://liguijiang.com"
started = time.time()
with requests.post(
    BASE + "/api/chat",
    json={"messages": [{"role": "user", "content": "用三句话介绍一下你自己，并说明你最适合帮人做什么。"}], "model": "deepseek-chat"},
    stream=True, timeout=90, headers={"Accept": "text/event-stream"},
) as resp:
    ttft = None
    chars = 0
    text = ""
    for line in resp.iter_lines(decode_unicode=True):
        if not line or not line.startswith("data:"):
            continue
        data = line[5:].strip()
        if data == "[DONE]":
            break
        try:
            obj = json.loads(data)
        except Exception:
            continue
        if obj.get("t"):
            if ttft is None:
                ttft = time.time() - started
            chars += len(obj["t"])
            text += obj["t"]
print(f"status={resp.status_code} ttft={ttft:.2f}s total={time.time()-started:.2f}s chars={chars}")
print("answer:", text[:160].replace("\n", " "))