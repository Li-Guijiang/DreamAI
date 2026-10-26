#!/usr/bin/env bash
# ===========================================================================
#  Dream AI · Web 一键部署（在服务器上以 root 运行）
#
#  用法：
#     tar czf dreamai-web.tar.gz -C release .
#     scp dreamai-web.tar.gz root@8.156.85.180:/tmp/
#     ssh root@8.156.85.180
#     mkdir -p /tmp/dreamai-release && tar xzf /tmp/dreamai-web.tar.gz -C /tmp/dreamai-release
#     bash /tmp/dreamai-release/deploy/install.sh
#
#  安全策略：部署前会自动备份原站点；除 `lsl` 标记文件外清空站点目录。
#  如目录中找不到 lsl，脚本会中止（确认无误可加 FORCE=1 强制执行）。
# ===========================================================================
set -euo pipefail

APP_DIR="${APP_DIR:-/www/wwwroot/liguijiang.com}"
DOMAIN="${DOMAIN:-liguijiang.com}"
PORT="${PORT:-8000}"
PYTHON="${PYTHON:-python3}"
WEB_USER="${WEB_USER:-www}"
PIP_INDEX="${PIP_INDEX:-https://mirrors.aliyun.com/pypi/simple}"
SRC_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKUP_DIR="${BACKUP_DIR:-/www/backup}"
PANEL_VHOST="/www/server/panel/vhost/nginx/${DOMAIN}.conf"
NGINX_CONF="/etc/nginx/conf.d/${DOMAIN}.conf"

log()  { printf '\033[1;36m[dreamai]\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m[dreamai]\033[0m %s\n' "$*"; }
die()  { printf '\033[1;31m[dreamai] %s\033[0m\n' "$*" >&2; exit 1; }

[[ "${EUID}" -eq 0 ]] || die "请使用 root 运行本脚本。"
[[ -d "${APP_DIR}" ]] || die "站点目录不存在：${APP_DIR}"
[[ -f "${SRC_DIR}/app/main.py" ]] || die "未找到应用源码，请在解压后的 release 目录中运行。"

if [[ ! -e "${APP_DIR}/lsl" && "${FORCE:-0}" != "1" ]]; then
  die "站点目录中没有找到 lsl 标记，为安全起见已中止。确认要清空请加 FORCE=1。"
fi

# ---------------------------------------------------------------------------
# 1. 备份 + 清理（保留 lsl）
# ---------------------------------------------------------------------------
mkdir -p "${BACKUP_DIR}"
STAMP="$(date +%Y%m%d-%H%M%S)"
BACKUP_FILE="${BACKUP_DIR}/${DOMAIN}-site-${STAMP}.tar.gz"
log "备份原站点到 ${BACKUP_FILE}"
tar czf "${BACKUP_FILE}" -C "${APP_DIR}" . 2>/dev/null || warn "备份时出现警告，继续执行"

log "清理站点目录（保留 lsl 与 .well-known）"
find "${APP_DIR}" -mindepth 1 -maxdepth 1 ! -name 'lsl' ! -name '.well-known' -exec rm -rf {} +

# ---------------------------------------------------------------------------
# 2. 复制程序文件
# ---------------------------------------------------------------------------
log "复制程序文件"
for item in app web requirements.txt .env.example deploy README.md; do
  if [[ -e "${SRC_DIR}/${item}" ]]; then
    cp -a "${SRC_DIR}/${item}" "${APP_DIR}/"
  fi
done

mkdir -p "${APP_DIR}/data"

# ---------------------------------------------------------------------------
# 3. Python 虚拟环境
# ---------------------------------------------------------------------------
command -v "${PYTHON}" >/dev/null 2>&1 || die "未找到 ${PYTHON}，请先安装 Python 3.10+。"
"${PYTHON}" -c 'import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)' \
  || die "Python 版本过低，需要 3.10 及以上。"

if [[ ! -x "${APP_DIR}/.venv/bin/python" ]]; then
  log "创建虚拟环境"
  "${PYTHON}" -m venv "${APP_DIR}/.venv"
fi

log "安装依赖（${PIP_INDEX}）"
"${APP_DIR}/.venv/bin/python" -m pip install --upgrade pip -q -i "${PIP_INDEX}"
"${APP_DIR}/.venv/bin/python" -m pip install -q -r "${APP_DIR}/requirements.txt" -i "${PIP_INDEX}"

# ---------------------------------------------------------------------------
# 4. 配置文件
# ---------------------------------------------------------------------------
if [[ ! -f "${APP_DIR}/.env" ]]; then
  cp "${APP_DIR}/.env.example" "${APP_DIR}/.env"
  warn "已生成 .env，请填写 DREAMAI_API_KEY 后执行：systemctl restart dreamai-web"
fi

if grep -q '^DREAMAI_API_KEY=$' "${APP_DIR}/.env" 2>/dev/null; then
  warn "警告：DREAMAI_API_KEY 仍为空，网站可以打开但无法对话。"
fi

# ---------------------------------------------------------------------------
# 5. systemd 服务
# ---------------------------------------------------------------------------
log "写入 systemd 服务"
sed -e "s#__APP_DIR__#${APP_DIR}#g" \
    -e "s#__PORT__#${PORT}#g" \
    -e "s#__WEB_USER__#${WEB_USER}#g" \
    "${SRC_DIR}/deploy/dreamai-web.service" > /etc/systemd/system/dreamai-web.service

systemctl daemon-reload
systemctl enable dreamai-web >/dev/null 2>&1 || true
systemctl restart dreamai-web

# ---------------------------------------------------------------------------
# 6. Nginx
# ---------------------------------------------------------------------------
CERT=""
KEY=""
CERT_PAIRS=(
  "/www/server/panel/vhost/cert/${DOMAIN}/fullchain.pem|/www/server/panel/vhost/cert/${DOMAIN}/privkey.pem"
  "/etc/letsencrypt/live/${DOMAIN}/fullchain.pem|/etc/letsencrypt/live/${DOMAIN}/privkey.pem"
  "/www/server/nginx/conf/ssl/${DOMAIN}.pem|/www/server/nginx/conf/ssl/${DOMAIN}.key"
)
for pair in "${CERT_PAIRS[@]}"; do
  c="${pair%%|*}"
  k="${pair##*|}"
  if [[ -f "${c}" && -f "${k}" ]]; then
    CERT="${c}"
    KEY="${k}"
    break
  fi
done

[[ -n "${CERT}" ]] || die "未找到 ${DOMAIN} 的 SSL 证书，请先在宝塔面板申请证书。"

if [[ -d "/www/wwwlogs" ]]; then LOG_DIR="/www/wwwlogs"; else LOG_DIR="/var/log/nginx"; fi

log "写入 Nginx 配置"
NGINX_TARGET="${NGINX_CONF}"
if [[ -d "/www/server/panel/vhost/nginx" ]]; then
  NGINX_TARGET="${PANEL_VHOST}"
  [[ -f "${NGINX_TARGET}" ]] && cp "${NGINX_TARGET}" "${NGINX_TARGET}.bak-${STAMP}"
fi

sed -e "s#__DOMAIN__#${DOMAIN}#g" \
    -e "s#__ROOT__#${APP_DIR}#g" \
    -e "s#__PORT__#${PORT}#g" \
    -e "s#__CERT__#${CERT}#g" \
    -e "s#__KEY__#${KEY}#g" \
    -e "s#__LOG_DIR__#${LOG_DIR}#g" \
    "${SRC_DIR}/deploy/nginx.conf" > "${NGINX_TARGET}"

if command -v nginx >/dev/null 2>&1; then
  nginx -t
  nginx -s reload 2>/dev/null || systemctl reload nginx
else
  warn "未找到 nginx 命令，请手动重载 Nginx。"
fi

# ---------------------------------------------------------------------------
# 7. 权限与自检
# ---------------------------------------------------------------------------
log "设置权限"
chown -R "${WEB_USER}:${WEB_USER}" "${APP_DIR}" 2>/dev/null || warn "chown 失败，请检查用户 ${WEB_USER} 是否存在"
chmod 600 "${APP_DIR}/.env" 2>/dev/null || true

sleep 2
if curl -fsS "http://127.0.0.1:${PORT}/api/health" >/dev/null; then
  log "服务健康检查通过：http://127.0.0.1:${PORT}/api/health"
else
  warn "健康检查失败，请查看：journalctl -u dreamai-web -n 80 --no-pager"
fi

log "完成。访问：https://${DOMAIN}"
