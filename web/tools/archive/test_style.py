import json, requests
r = requests.post("http://127.0.0.1:8787/api/chat", json={"messages":[{"role":"user","content":"hi"}],"style":"concise"}, stream=True, timeout=30)
print("status", r.status_code)
for line in r.iter_lines(decode_unicode=True):
    if line and line.startswith("event:"):
        print(line)