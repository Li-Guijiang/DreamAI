from pathlib import Path
import os, time, paramiko

ROOT = Path(r"D:\Users\HI MATEBOOK 14\Documents\deepseek-harness\default-workspace\dreamai-web")
APP = "/www/wwwroot/liguijiang.com"

tpl = (ROOT / "deploy" / "nginx.conf").read_text(encoding="utf-8")
conf = (tpl
    .replace("__DOMAIN__", "liguijiang.com")
    .replace("__ROOT__", APP)
    .replace("__PORT__", "8010")
    .replace("__CERT__", "/www/server/nginx/conf/ssl/liguijiang.com.pem")
    .replace("__KEY__", "/www/server/nginx/conf/ssl/liguijiang.com.key")
    .replace("__LOG_DIR__", "/www/wwwlogs"))

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("8.156.85.180", username="root", password=os.environ["DREAMAI_SSH_PASSWORD"], timeout=20, look_for_keys=False, allow_agent=False)
sftp = c.open_sftp()
for name in ["robots.txt", "sitemap.xml", "favicon.ico"]:
    sftp.put(str(ROOT / "web" / name), f"{APP}/web/{name}")
    print("uploaded", name)
target = "/www/server/panel/vhost/nginx/liguijiang.com.conf"
with sftp.open(target, "w") as fh:
    fh.write(conf)
sftp.close()
cmd = f"chown -R www:www {APP}/web && nginx -t 2>&1 && nginx -s reload && echo RELOADED"
stdin, stdout, stderr = c.exec_command(cmd, timeout=60)
print(stdout.read().decode("utf-8", "replace"))
print(stderr.read().decode("utf-8", "replace"))
c.close()