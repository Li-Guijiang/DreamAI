import requests
home = requests.get("https://liguijiang.com/", timeout=20).text
print("home has download link:", "/download.html" in home)
print("download page:", requests.get("https://liguijiang.com/download.html", timeout=20).status_code)
print("latest.json:", requests.get("https://liguijiang.com/downloads/latest.json", timeout=20).text)
r = requests.get("https://liguijiang.com/downloads/DreamAI-Setup-1.0.0.exe", headers={"Range": "bytes=0-1023"}, timeout=20)
print("range:", r.status_code, r.headers.get("content-range"), len(r.content))