echo "=== 刷题工具 ==="
curl -sS -k -H "Host: liguijiang.com" "https://127.0.0.1/lsl/%E5%88%B7%E9%A2%98%E5%B7%A5%E5%85%B7/" | grep -o "<title>[^<]*</title>" | head -1
curl -sS -k -o /dev/null -w "asset=%{http_code} %{content_type}\n" -H "Host: liguijiang.com" "https://127.0.0.1/lsl/%E5%88%B7%E9%A2%98%E5%B7%A5%E5%85%B7/assets/index-BDZVfQXH.css"
curl -sS -k -o /dev/null -w "data=%{http_code} %{content_type} %{size_download}\n" -H "Host: liguijiang.com" "https://127.0.0.1/lsl/%E5%88%B7%E9%A2%98%E5%B7%A5%E5%85%B7/data/data.json"
echo "=== 实验平台 ==="
curl -sS -k -H "Host: liguijiang.com" "https://127.0.0.1/lsl/%E5%AE%9E%E9%AA%8C%E5%B9%B3%E5%8F%B0/" | grep -o "<title>[^<]*</title>" | head -1
echo "=== redirects/root ==="
curl -sS -k -o /dev/null -w "lsl=%{http_code} -> %{redirect_url}\n" -H "Host: liguijiang.com" "https://127.0.0.1/lsl"
curl -sS -k -H "Host: liguijiang.com" "https://127.0.0.1/" | grep -o "<title>[^<]*</title>" | head -1