"""Upload the Windows installer to the site and verify its checksum."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path

import paramiko

ROOT = Path(r"D:\Users\HI MATEBOOK 14\Documents\deepseek-harness\default-workspace\dreamai-web")
LOCAL = ROOT / "web" / "downloads" / "DreamAI-Setup-1.0.0.exe"
REMOTE = "/www/wwwroot/liguijiang.com/web/downloads/DreamAI-Setup-1.0.0.exe"

local_hash = hashlib.sha256(LOCAL.read_bytes()).hexdigest()
print("local:", LOCAL.stat().st_size, local_hash)

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
state = {"last": 0}

def progress(done: int, total: int) -> None:
    if done - state["last"] >= 10 * 1024 * 1024 or done == total:
        state["last"] = done
        print(f"  {done / 1024 / 1024:.1f} / {total / 1024 / 1024:.1f} MB", flush=True)

sftp.put(str(LOCAL), REMOTE, callback=progress, confirm=True)
sftp.chmod(REMOTE, 0o644)
sftp.close()

stdin, stdout, stderr = client.exec_command(
    f"chown www:www {REMOTE} && sha256sum {REMOTE} && ls -lh {REMOTE}", timeout=120
)
print(stdout.read().decode("utf-8", "replace"))
print(stderr.read().decode("utf-8", "replace"))
client.close()
print("expected sha256:", local_hash)
