from pathlib import Path
p = Path("/www/server/panel/vhost/nginx/liguijiang.com.conf")
s = p.read_text(encoding="utf-8")
if "location /lsl/" in s:
    print("already patched")
    raise SystemExit(0)
anchor = "    # ---- 流式对话接口 ----"
block = """    # ---- 老师的静态工具（/lsl：刷题工具、实验平台） ----
    location = /lsl { return 301 /lsl/; }

    location /lsl/ {
        root /www/wwwroot/liguijiang.com;
        index index.html;
        try_files $uri $uri/ =404;
        autoindex off;
    }

"""
if anchor not in s:
    raise SystemExit("anchor not found")
p.with_suffix(".conf.bak-20261027").write_text(s, encoding="utf-8")
p.write_text(s.replace(anchor, block + anchor, 1), encoding="utf-8")
print("patched")