echo "=== index 刷题工具 ==="
cat "/www/wwwroot/liguijiang.com/lsl/刷题工具/index.html"
echo
echo "=== files 刷题工具 ==="
find "/www/wwwroot/liguijiang.com/lsl/刷题工具" -maxdepth 3 -type f -printf "%p %s bytes\n" | head -40
echo "=== files 实验平台 ==="
find "/www/wwwroot/liguijiang.com/lsl/实验平台" -maxdepth 3 -type f -printf "%p %s bytes\n" | head -40
echo "=== nginx conf ==="
cat /www/server/panel/vhost/nginx/liguijiang.com.conf
echo "=== backups ==="
ls -lh /www/backup | tail -10