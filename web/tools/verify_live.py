import hashlib, requests
cfg = requests.get("https://liguijiang.com/api/config", timeout=15).json()
print("model:", cfg["defaultModel"], "| free:", cfg["free"], "| version:", cfg["version"])
js = requests.get("https://liguijiang.com/assets/js/app.js?v=1.2.0", timeout=20).text
print("strip rule present:", "步骤\\s*\\d+" in js)
og = requests.get("https://liguijiang.com/assets/img/og.png", timeout=20).content
print("og bytes:", len(og), "sha:", hashlib.sha256(og).hexdigest()[:16])