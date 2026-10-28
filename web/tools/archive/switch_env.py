"""Switch the live site to the free-model + BYOK configuration.

Run after receiving the Zhipu key:

    set DREAMAI_SSH_PASSWORD=...
    set ZHIPU_API_KEY=xxxxx.yyyyy
    python tools/switch_env.py

It rewrites /www/wwwroot/liguijiang.com/.env (removing the site DeepSeek key),
restarts the service and verifies the free model with one real request.
"""

from __future__ import annotations

import json
import os
import posixpath
import re
import time

import paramiko
import requests

APP = "/www/wwwroot/liguijiang.com"
DOMAIN = "https://liguijiang.com"

zhipu_key = os.environ.get("ZHIPU_API_KEY", "").strip()
if not zhipu_key:
    raise SystemExit("ZHIPU_API_KEY is required")

env = f"""# Dream AI · production (free model + BYOK)
DREAMAI_FREE_API_KEY={zhipu_key}
DREAMAI_FREE_BASE_URL=https://open.bigmodel.cn/api/paas/v4
DREAMAI_FREE_MODEL=glm-4-flash
DREAMAI_FREE_LABEL=GLM-4-Flash
DREAMAI_FREE_KEY_URL=https://open.bigmodel.cn/usercenter/apikeys

DREAMAI_BYOK_BASE_URL=https://api.deepseek.com/v1
DREAMAI_BYOK_MODELS=deepseek-chat|DeepSeek V3|0,deepseek-reasoner|DeepSeek R1|1
DREAMAI_BYOK_KEY_URL=https://platform.deepseek.com/api_keys
DREAMAI_BYOK_LABEL=DeepSeek

DREAMAI_SITE_TITLE=Dream AI
DREAMAI_SITE_TAGLINE=让每一个想法，都被认真对待
DREAMAI_REPO_URL=https://github.com/Li-Guijiang/DreamAI

DREAMAI_TEMPERATURE=0.7
DREAMAI_MAX_TOKENS=4096
DREAMAI_RATE_LIMIT=30
DREAMAI_RATE_WINDOW=600
DREAMAI_DAILY_LIMIT=800
DREAMAI_MAX_CONCURRENCY=8
DREAMAI_MAX_INPUT_CHARS=12000
DREAMAI_MAX_HISTORY_MESSAGES=30
DREAMAI_MAX_HISTORY_CHARS=60000
"""

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(
    "8.156.85.180",
    username="root",
    password=os.environ["DREAMAI_SSH_PASSWORD"],
    timeout=20,
    look_for_keys=False,
    allow_agent=False,
)
sftp = client.open_sftp()
with sftp.open(posixpath.join(APP, ".env"), "w") as handle:
    handle.write(env)
sftp.close()

cmd = (
    f"chown www:www {APP}/.env && chmod 600 {APP}/.env && "
    "systemctl restart dreamai-web && sleep 3 && systemctl is-active dreamai-web && "
    "curl -sS -m 10 http://127.0.0.1:8010/api/health"
)
_, out, err = client.exec_command(cmd, timeout=120)
print(out.read().decode("utf-8", "replace"))
print(err.read().decode("utf-8", "replace"))

print("waiting for service...")
for _ in range(10):
    try:
        cfg = requests.get(f"{DOMAIN}/api/config", timeout=10).json()
        print(json.dumps(cfg, ensure_ascii=False)[:500])
        break
    except Exception:
        time.sleep(2)

started = time.time()
with requests.post(
    f"{DOMAIN}/api/chat",
    json={"messages": [{"role": "user", "content": "用一句话介绍你自己"}], "provider": "free"},
    stream=True,
    timeout=90,
    headers={"Accept": "text/event-stream"},
) as resp:
    print("free chat status:", resp.status_code)
    text = ""
    model = None
    for line in resp.iter_lines(decode_unicode=True):
        if not line or not line.startswith("data:"):
            continue
        data = line[5:].strip()
        try:
            obj = json.loads(data)
        except Exception:
            continue
        if obj.get("model"):
            model = obj["model"]
        if obj.get("t"):
            text += obj["t"]
        if obj.get("message"):
            print("error:", obj["message"])
print(f"model={model} ttft~{time.time()-started:.2f}s chars={len(text)}")
print("answer:", text[:120].replace("\n", " "))

client.close()
