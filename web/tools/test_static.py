import requests
BASE = "https://liguijiang.com"
for path in ["/favicon.ico", "/robots.txt", "/sitemap.xml", "/manifest.webmanifest", "/"]:
    r = requests.get(BASE + path, timeout=15)
    print(f"{path:24} {r.status_code}  type={r.headers.get('content-type')}  cache={r.headers.get('cache-control')}")