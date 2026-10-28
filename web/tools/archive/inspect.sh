echo "=== OS ==="
cat /etc/os-release | head -6
uname -m
echo "=== resources ==="
df -h / /www 2>/dev/null | head -6
free -m | head -3
echo "=== python ==="
python3 --version 2>&1
python3 -m venv --help >/dev/null 2>&1 && echo "venv: ok" || echo "venv: missing"
echo "=== nginx ==="
nginx -v 2>&1
systemctl is-active nginx 2>&1
ls /www/server/panel/vhost/nginx/ 2>/dev/null | head -20
echo "=== site dir ==="
ls -la /www/wwwroot/liguijiang.com 2>/dev/null
echo "=== certs ==="
ls -la /www/server/panel/vhost/cert/liguijiang.com 2>/dev/null
echo "=== vhost config ==="
cat /www/server/panel/vhost/nginx/liguijiang.com.conf 2>/dev/null
echo "=== listening ==="
ss -lntp 2>/dev/null | head -20
echo "=== disk of site ==="
du -sh /www/wwwroot/liguijiang.com 2>/dev/null
