from pathlib import Path
p = Path("/www/server/panel/vhost/nginx/liguijiang.com.conf")
s = p.read_text(encoding="utf-8")
if "location = /lsl/ " in s:
    print("already")
    raise SystemExit(0)
anchor = "    location /lsl/ {"
block = "    location = /lsl/ { return 302 /lsl/%E5%88%B7%E9%A2%98%E5%B7%A5%E5%85%B7/; }\n\n"
if anchor not in s:
    raise SystemExit("anchor missing")
p.write_text(s.replace(anchor, block + anchor, 1), encoding="utf-8")
print("patched")