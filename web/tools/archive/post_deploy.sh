set -e
APP_DIR=/www/wwwroot/liguijiang.com
cp /tmp/dreamai.env "$APP_DIR/.env"
rm -f /tmp/dreamai.env
chown www:www "$APP_DIR/.env"
chmod 600 "$APP_DIR/.env"
systemctl restart dreamai-web
sleep 3
echo "=== service ==="
systemctl is-active dreamai-web
systemctl status dreamai-web --no-pager -n 8 2>&1 | tail -12
echo "=== health ==="
curl -sS -m 10 http://127.0.0.1:8010/api/health
echo
echo "=== site files ==="
ls -la "$APP_DIR"
echo "=== nginx vhost head ==="
head -40 /www/server/panel/vhost/nginx/liguijiang.com.conf
