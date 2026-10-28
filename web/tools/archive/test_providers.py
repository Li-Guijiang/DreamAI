import json, requests

BASE = "http://127.0.0.1:8787"
cfg = requests.get(BASE + "/api/config", timeout=10).json()
print("config:", json.dumps(cfg, ensure_ascii=False, indent=1)[:900])

def chat(payload):
    r = requests.post(BASE + "/api/chat", json=payload, stream=True, timeout=40)
    print("status:", r.status_code)
    if r.status_code != 200:
        print("body:", r.text[:200])
        return
    events = []
    for line in r.iter_lines(decode_unicode=True):
        if line and line.startswith("event:"):
            events.append(line[6:].strip())
    print("events:", events[:3], "...", events[-2:], "count", len(events))

print("\n--- free ---")
chat({"messages": [{"role": "user", "content": "hi"}], "provider": "free", "model": "mock-glm"})
print("\n--- byok with key ---")
chat({"messages": [{"role": "user", "content": "hi"}], "provider": "byok", "model": "deepseek-chat", "apiKey": "sk-test-user-key-1234567890"})
print("\n--- byok without key ---")
chat({"messages": [{"role": "user", "content": "hi"}], "provider": "byok", "model": "deepseek-chat"})