import requests
url = "https://liguijiang.com/downloads/DreamAI-Setup-1.1.0.exe"
r = requests.get(url, headers={"Range": "bytes=0-1023"}, timeout=30)
print("range:", r.status_code, r.headers.get("content-range"), len(r.content))