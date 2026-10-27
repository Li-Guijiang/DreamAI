import requests
for path in ["/lsl/", "/lsl/刷题工具", "/lsl/刷题工具/"]:
    r = requests.get("https://liguijiang.com" + path, allow_redirects=False, timeout=20)
    print(path, r.status_code, r.headers.get("location", ""))
    if r.status_code in (301, 302):
        r2 = requests.get("https://liguijiang.com" + path, timeout=20)
        print("  ->", r2.status_code, len(r2.content))