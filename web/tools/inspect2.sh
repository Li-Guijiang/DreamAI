echo "=== python candidates ==="
ls -1 /usr/bin/python* 2>/dev/null
ls -1 /usr/local/bin/python* 2>/dev/null
for v in 3.9 3.10 3.11 3.12; do command -v python$v >/dev/null 2>&1 && echo "found python$v: $(python$v --version 2>&1)"; done
ls -d /www/server/pyenv* 2>/dev/null && /www/server/pyenv/bin/python3 --version 2>/dev/null
echo "=== dnf python availability ==="
dnf -q list available python3.11 python3.9 2>/dev/null | tail -12
echo "=== existing app on 8000 ==="
ps -ef | grep -E "uvicorn|gunicorn|next-server" | grep -v grep | head -10
echo "=== www user ==="
id www
echo "=== ssl cert ==="
openssl x509 -in /www/server/nginx/conf/ssl/liguijiang.com.pem -noout -subject -issuer -dates 2>&1
echo "=== lsl ==="
ls -la /www/wwwroot/liguijiang.com/lsl | head -10
echo "=== ports 8000/8010 ==="
ss -lntp | grep -E ":8000|:8010" || echo "8010 free"
echo "=== curl present ==="
command -v curl && curl --version | head -1
