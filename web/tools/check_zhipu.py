import requests, json
url = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
payload = {"model": "glm-4-flash", "messages": [{"role": "user", "content": "hi"}], "stream": False}
try:
    r = requests.post(url, json=payload, headers={"Authorization": "Bearer test.invalid"}, timeout=20)
    print("http:", r.status_code)
    print(r.text[:300])
except Exception as exc:
    print("error:", type(exc).__name__, exc)