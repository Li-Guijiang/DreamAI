import os, time, json
from pathlib import Path
from dotenv import dotenv_values
import requests
cfg = dotenv_values(Path(r"D:\Users\HI MATEBOOK 14\Documents\deepseek-harness\default-workspace\dreamai-web\.env"))
key = cfg.get("DREAMAI_FREE_API_KEY")
base = cfg.get("DREAMAI_FREE_BASE_URL", "https://open.bigmodel.cn/api/paas/v4")
for model in ["glm-4.5-flash", "glm-4-flash"]:
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": "用 Node.js 原生 http 写一个 server.js，提供 GET/POST /api/tasks，完整代码，不要解释。"}],
        "temperature": 0.3,
        "max_tokens": 800,
        "stream": True,
    }
    t0 = time.time()
    try:
        r = requests.post(f"{base.rstrip('/')}/chat/completions", headers={"Authorization": f"Bearer {key}"}, json=payload, stream=True, timeout=180)
        if r.status_code != 200:
            print(model, "HTTP", r.status_code, r.text[:200]); continue
        chars = 0
        for line in r.iter_lines():
            if line.startswith(b"data: ") and b"[DONE]" not in line:
                try:
                    delta = json.loads(line[6:]).get("choices", [{}])[0].get("delta", {}).get("content") or ""
                    chars += len(delta)
                except Exception:
                    pass
        print(model, "ok", round(time.time()-t0,1), "s", chars, "chars")
    except Exception as e:
        print(model, "ERR", round(time.time()-t0,1), str(e)[:120])