from pathlib import Path
import os, paramiko
ROOT = Path(r"D:\Users\HI MATEBOOK 14\Documents\deepseek-harness\default-workspace\dreamai-web")
APP = "/www/wwwroot/liguijiang.com"
c = paramiko.SSHClient(); c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("8.156.85.180", username="root", password=os.environ["DREAMAI_SSH_PASSWORD"], timeout=20, look_for_keys=False, allow_agent=False)
sftp = c.open_sftp()
for rel in ["app/main.py", "app/config.py", ".env"]:
    sftp.put(str(ROOT / rel), f"{APP}/{rel}")
    print("uploaded", rel)
sftp.close()
cmd = (f"chown www:www {APP}/.env {APP}/app/main.py {APP}/app/config.py && chmod 600 {APP}/.env && "
       "systemctl restart dreamai-web && sleep 3 && systemctl is-active dreamai-web && curl -sS -m 10 http://127.0.0.1:8010/api/health && echo && "
       "journalctl -u dreamai-web -n 5 --no-pager | tail -3")
_, out, err = c.exec_command(cmd, timeout=90)
print(out.read().decode("utf-8", "replace"))
print(err.read().decode("utf-8", "replace"))
c.close()