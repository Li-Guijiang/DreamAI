import requests, re
base = "https://liguijiang.com"
for path in ["/lsl", "/lsl/刷题工具", "/lsl/刷题工具/", "/lsl/刷题工具/assets/index-BDZVfQXH.css", "/lsl/刷题工具/assets/index-D-7FDxgb.js", "/lsl/刷题工具/data/data.json", "/lsl/实验平台", "/lsl/实验平台/", "/"]:
    r = requests.get(base + path, allow_redirects=False, timeout=30)
    loc = r.headers.get("location", "")
    extra = ""
    if r.status_code in (301, 302):
        r2 = requests.get(base + path, timeout=30)
        t = re.search(r"<title>([^<]*)</title>", r2.text)
        extra = f" -> {r2.status_code} {t.group(1) if t else ''}"
    print(path, r.status_code, r.headers.get("content-type"), f"loc={loc}{extra}")