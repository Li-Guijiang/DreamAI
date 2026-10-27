from pathlib import Path
p = Path("/www/server/panel/vhost/nginx/liguijiang.com.conf")
s = p.read_text(encoding="utf-8")
old = """    location /lsl/ {
        root /www/wwwroot/liguijiang.com;
        index index.html;
        try_files $uri $uri/ =404;
        autoindex off;
    }
"""
new = """    location /lsl/ {
        root /www/wwwroot/liguijiang.com;
        index index.html;
        if (-d $request_filename) {
            rewrite ^(.*[^/])$ $1/ permanent;
        }
        try_files $uri $uri/ =404;
        autoindex off;
    }
"""
if "if (-d $request_filename)" in s:
    print("already patched")
elif old in s:
    p.write_text(s.replace(old, new, 1), encoding="utf-8")
    print("patched")
else:
    raise SystemExit("block not found")