import requests
for url in ["https://liguijiang.com/", "https://liguijiang.com/assets/css/app.css", "https://www.liguijiang.com/"]:
    r = requests.get(url, timeout=20, allow_redirects=False)
    print(url, "->", r.status_code, "|", r.headers.get("location", ""))
    for h in ["content-security-policy", "x-frame-options", "strict-transport-security", "server", "content-encoding"]:
        if r.headers.get(h):
            print("   ", h, "=", r.headers[h][:100])