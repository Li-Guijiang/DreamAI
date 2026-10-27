set -e
echo "=== lsl tree ==="
ls -la /www/wwwroot/liguijiang.com/lsl
echo "=== 刷题工具 ==="
ls -la "/www/wwwroot/liguijiang.com/lsl/刷题工具" | head -30
echo "=== 实验平台 ==="
ls -la "/www/wwwroot/liguijiang.com/lsl/实验平台" | head -20
echo "=== find files ==="
find /www/wwwroot/liguijiang.com/lsl -maxdepth 2 -type f | head -30
echo "=== nginx lsl ==="
nginx -T 2>/dev/null | grep -n -B3 -A12 "lsl" | head -80
echo "=== curl local ==="
curl -sS -o /dev/null -w "root=%{http_code}\n" "http://127.0.0.1/lsl/"
curl -sS -o /dev/null -w "tool=%{http_code}\n" "http://127.0.0.1/lsl/%E5%88%B7%E9%A2%98%E5%B7%A5%E5%85%B7/"
curl -sS -o /dev/null -w "tool_slash=%{http_code}\n" "http://127.0.0.1/lsl/%E5%88%B7%E9%A2%98%E5%B7%A5%E5%85%B7/index.html"
echo "=== docker ==="
docker ps -a --format "{{.Names}} {{.Status}} {{.Ports}}"
echo "=== error log ==="
tail -25 /www/wwwlogs/liguijiang.com.error.log 2>/dev/null || tail -25 /www/wwwlogs/error.log 2>/dev/null