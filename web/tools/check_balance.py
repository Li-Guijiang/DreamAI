import json, re, requests
from pathlib import Path

env = Path(r"D:\Users\HI MATEBOOK 14\Documents\deepseek-harness\default-workspace\dreamai-web\.env").read_text(encoding="utf-8")
key = re.search(r"DREAMAI_API_KEY=(\S+)", env).group(1)
masked = key[:8] + "..." + key[-4:]
print("key in use:", masked)

r = requests.get("https://api.deepseek.com/user/balance", headers={"Authorization": f"Bearer {key}"}, timeout=20)
print("balance status:", r.status_code)
try:
    data = r.json()
    print(json.dumps(data, ensure_ascii=False, indent=2))
except Exception:
    print(r.text[:300])