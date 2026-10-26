from pathlib import Path
import os, paramiko
ROOT = Path(r"D:\Users\HI MATEBOOK 14\Documents\deepseek-harness\default-workspace\dreamai-web")
APP = "/www/wwwroot/liguijiang.com"
SKIP = {"__pycache__", ".venv", "node_modules", "shots"}
c = paramiko.SSHClient(); c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("8.156.85.180", username="root", password=os.environ["DREAMAI_SSH_PASSWORD"], timeout=20, look_for_keys=False, allow_agent=False)
sftp = c.open_sftp()

def ensure(remote_dir):
    cur = ""
    for part in remote_dir.strip("/").split("/"):
        cur += "/" + part
        try: sftp.stat(cur)
        except IOError: sftp.mkdir(cur)

count = 0
for base in ["app", "web"]:
    for path in sorted((ROOT / base).rglob("*")):
        if any(part in SKIP for part in path.parts) or not path.is_file():
            continue
        if path.stat().st_size > 5 * 1024 * 1024:
            continue
        rel = path.relative_to(ROOT).as_posix()
        remote = APP + "/" + rel
        ensure(os.path.dirname(remote).replace("\\", "/"))
        sftp.put(str(path), remote)
        count += 1
sftp.put(str(ROOT / "README.md"), APP + "/README.md")
sftp.close()
print("uploaded", count, "files")

cmd = ("chown -R www:www /www/wwwroot/liguijiang.com/app /www/wwwroot/liguijiang.com/web /www/wwwroot/liguijiang.com/README.md && "
       "chown www:www /www/wwwroot/liguijiang.com/.env && chmod 600 /www/wwwroot/liguijiang.com/.env && "
       "systemctl restart dreamai-web && sleep 3 && systemctl is-active dreamai-web && "
       "curl -sS -m 10 http://127.0.0.1:8010/api/health && echo && "
       "curl -sS -m 10 https://liguijiang.com/api/config | head -c 300")
_, out, err = c.exec_command(cmd, timeout=120)
print(out.read().decode("utf-8", "replace"))
print(err.read().decode("utf-8", "replace"))
c.close()