echo "=== current body ==="
curl -sS -k -H "Host: liguijiang.com" "https://127.0.0.1/lsl/%E5%88%B7%E9%A2%98%E5%B7%A5%E5%85%B7/" | head -8
echo "=== data refs in js ==="
grep -oE "[^\"']*data\.json[^\"']*" "/www/wwwroot/liguijiang.com/lsl/刷题工具/assets/index-D-7FDxgb.js" | head -5
grep -oE "\"/api/[^\"]*\"|'/api/[^']*'" "/www/wwwroot/liguijiang.com/lsl/刷题工具/assets/index-D-7FDxgb.js" | head -5
echo "=== backup data sizes ==="
tar -tvzf /www/backup/liguijiang.com-site-20261025-200115.tar.gz | grep "data.json"
ls -l "/www/wwwroot/liguijiang.com/lsl/刷题工具/data/data.json"