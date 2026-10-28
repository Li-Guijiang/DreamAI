echo "=== grep lsl configs ==="
grep -RIn "lsl" /www/server/panel/vhost/nginx /www/server/nginx/conf 2>/dev/null | head -30
echo "=== nginx backups ==="
find /www/backup/nginxBak -maxdepth 2 -type f 2>/dev/null | head -10
echo "=== old site backup lsl ==="
tar -tzf /www/backup/liguijiang.com-site-20261025-200115.tar.gz 2>/dev/null | grep -i "lsl" | head -20
echo "=== curl with host ==="
curl -sS -k -o /dev/null -w "lsl_root=%{http_code} redirect=%{redirect_url}\n" -H "Host: liguijiang.com" "https://127.0.0.1/lsl/"
curl -sS -k -o /dev/null -w "tool=%{http_code} redirect=%{redirect_url}\n" -H "Host: liguijiang.com" "https://127.0.0.1/lsl/%E5%88%B7%E9%A2%98%E5%B7%A5%E5%85%B7"
curl -sS -k -o /dev/null -w "tool_slash=%{http_code} type=%{content_type}\n" -H "Host: liguijiang.com" "https://127.0.0.1/lsl/%E5%88%B7%E9%A2%98%E5%B7%A5%E5%85%B7/"