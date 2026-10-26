from pathlib import Path
import os, posixpath, paramiko

ROOT = Path(r"D:\Users\HI MATEBOOK 14\Documents\deepseek-harness\default-workspace\dreamai-web")
APP = "/www/wwwroot/liguijiang.com"
SKIP = {"__pycache__", ".venv", "node_modules", "shots"}

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("8.156.85.180", username="root", password=os.environ["DREAMAI_SSH_PASSWORD"], timeout=20, look_for_keys=False, allow_agent=False)
sftp = c.open_sftp()

def ensure(remote_dir):
    parts = remote_dir.strip("/").split("/")
    cur = ""
    for part in parts:
        cur += "/" + part
        try:
            sftp.stat(cur)
        except IOError:
            sftp.mkdir(cur)

count = 0
for base in ["app", "web"]:
    for path in sorted((ROOT / base).rglob("*")):
        if any(part in SKIP for part in path.parts):
            continue
        if not path.is_file():
            continue
        rel = path.relative_to(ROOT).as_posix()
        remote = posixpath.join(APP, rel)
        ensure(posixpath.dirname(remote))
        sftp.put(str(path), remote)
        count += 1

sftp.put(str(ROOT / "README.md"), posixpath.join(APP, "README.md"))
sftp.close()
print("uploaded", count, "files")

cmd = (
    f"chown -R www:www {APP}/app {APP}/web {APP}/README.md && "
    "systemctl restart dreamai-web && sleep 3 && systemctl is-active dreamai-web && "
    "curl -sS -m 10 http://127.0.0.1:8010/api/health && echo && "
    "curl -sS -m 10 https://liguijiang.com/ | grep -o '<title>[^<]*</title>' && "
    "curl -sS -o /dev/null -w 'favicon %{http_code} %{content_type} %{size_download}\\n' https://liguijiang.com/assets/img/favicon.ico"
)
_, out, err = c.exec_command(cmd, timeout=120)
print(out.read().decode("utf-8", "replace"))
print(err.read().decode("utf-8", "replace"))
c.close()