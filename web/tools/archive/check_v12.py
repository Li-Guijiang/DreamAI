import requests, re
home = requests.get("https://liguijiang.com/", timeout=20).text
print("home app.js 1.4:", "app.js?v=1.4.0" in home)
print("home has code strings:", "编程模式" in requests.get("https://liguijiang.com/assets/js/app.js?v=1.4.0", timeout=30).text)
page = requests.get("https://liguijiang.com/download.html", timeout=20).text
print("download v1.2:", "v1.2.0" in page, "| code banner:", "code-banner" in page, "| node faq:", "Node.js 20+" in page)
print("latest:", requests.get("https://liguijiang.com/downloads/latest.json", timeout=20).text)