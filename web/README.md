# Dream AI · Web

> 让每一个想法，都被认真对待。

Dream AI 的网页版：一个可以直接在浏览器里使用的通用智能体。它延续了
[DreamAI](https://github.com/Li-Guijiang/DreamAI) 仓库的定位与配置约定
（OpenAI 兼容 Provider、`DREAMAI_*` 环境变量），并补上了网页端真正需要的
东西——流式输出、深度思考、多轮会话、移动端适配，以及一套足够克制的界面。

- 线上地址：<https://liguijiang.com>
- 开源仓库：<https://github.com/Li-Guijiang/DreamAI>
- 开发团队：李贵江 等

![首页](docs/preview-hero.png)

## 特性

| | |
| --- | --- |
| **流式对话** | 基于 SSE 逐字输出，Nginx 关闭缓冲，首字延迟约 0.7 秒 |
| **对话 / 工作双模式** | 对话模式直接问答；工作模式先拆计划，再逐步执行并汇总 |
| **桌面版** | Windows 客户端，内置本地文件工作台（整理 / 重命名 / 导出文档） |
| **深度思考** | 支持 `deepseek-reasoner` 等推理模型，思考过程可折叠查看 |
| **风格预设** | 通用 / 严谨 / 创意 / 精简，一键切换语气与温度 |
| **附件阅读** | 拖入或上传 txt / md / csv / json / 代码等文本文件，一起发送 |
| **语音输入** | 浏览器原生语音识别（Chrome / Edge），说完直接发送 |
| **会话管理** | 本地保存、搜索、重命名、单条导出、全部导出 |
| **消息编辑** | 修改已发送的问题并重新生成回答 |
| **Markdown 渲染** | 标题、表格、引用、代码块，代码高亮 + 一键复制（Prism） |
| **双主题 / 字号** | 深色、浅色、跟随系统；紧凑 / 标准 / 舒适三档字号 |
| **响应式** | 桌面双栏、移动端抽屉侧栏与安全区适配 |
| **两种模型来源** | 默认免费模型（GLM-4-Flash），也可填自己的 DeepSeek Key 用 V3 / R1 |
| **私有部署** | API Key 只存在于服务器 `.env`，浏览器永远拿不到 |
| **防滥用** | 按 IP 滑动窗口限流 + 每日额度 + 并发信号量 + 输入长度校验 |

![对话](docs/preview-chat.png)

## 对话模式 / 工作模式

| | 对话模式 | 工作模式 |
| --- | --- | --- |
| 适合 | 写作、编程、问答、闲聊 | 策划、调研、多步骤任务 |
| 行为 | 一次回答 | 先拆 3–6 步计划，逐步执行，最后汇总 |
| 界面 | 普通消息 | 可展开的步骤卡片 + 进度 + 最终结果 |
| 耗时 | 1–3 秒 | 十几秒到一分钟 |

工作模式按 DreamAI 仓库里的「规划 → 执行 → 汇总」思路实现：模型先输出 JSON 计划，
前端逐步调用模型完成每一步，最后再合成最终答复。每一步的产出都可以展开查看。

![工作模式](docs/preview-work.png)

![附件](docs/preview-files.png)

## 目录结构

```
dreamai-web/
├─ app/                    # FastAPI 服务
│  ├─ main.py              # 路由、SSE、限流、安全响应头
│  ├─ llm.py               # OpenAI 兼容流式客户端（httpx）
│  └─ config.py            # 环境变量解析
├─ web/                    # 纯静态前端（无需构建）
│  ├─ index.html
│  ├─ manifest.webmanifest
│  └─ assets/
│     ├─ css/app.css       # 设计系统
│     ├─ js/app.js         # 会话、流式渲染、Markdown、交互
│     ├─ img/              # 品牌图标、favicon、社交分享图
│     └─ vendor/           # marked / DOMPurify / Prism（本地托管）
├─ desktop/                # Electron 桌面版（本地文件工作台）
├─ deploy/                 # 部署脚本与配置模板
├─ tools/                  # 本地维护脚本（Mock 模型、资产生成、SSH 助手），见 tools/README.md
├─ requirements.txt
└─ .env.example
```

## 桌面版（Windows）

下载：<https://liguijiang.com/download.html>（安装包放在 `web/downloads/`）。

桌面版 = 官网同一套界面 + 本地文件工作台：

- 按类型整理文件夹（先预览、再确认）
- 批量重命名（前缀 + 序号，保留扩展名）
- 把当前对话保存为 Markdown

构建方式见 [desktop 说明](https://github.com/Li-Guijiang/DreamAI/tree/main/desktop)。

## 本地运行

需要 Python 3.10+。

```bash
python -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env        # 填入 DREAMAI_FREE_API_KEY（或用 Mock 测试）
.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
```

打开 <http://127.0.0.1:8000>。

没有 API Key 也可以先看界面：`tools/mock_upstream.py` 会返回一段固定的
Markdown 回答，用来调试样式与流式渲染。

```bash
.venv/bin/uvicorn mock_upstream:app --app-dir tools --port 8799
DREAMAI_FREE_API_KEY=test DREAMAI_FREE_BASE_URL=http://127.0.0.1:8799/v1 \
DREAMAI_FREE_MODEL=mock-glm \
  .venv/bin/uvicorn app.main:app --port 8000
```

## 两种模型来源

| 来源 | 说明 | 谁付费 |
| --- | --- | --- |
| **免费模型**（默认） | 站点统一提供，默认智谱 `GLM-4-Flash`，访客打开即用 | 站长（免费额度，可换模型） |
| **自带 Key（BYOK）** | 访客在「设置 → 模型来源」粘贴自己的 DeepSeek Key，可切到 V3 / R1 | 访客自己 |

- 免费模型的 Key 只存在服务器 `.env`，浏览器拿不到
- 用户的 Key 只存在其浏览器 `localStorage`，每次请求临时转发，服务端不存储、不写日志
- 免费模型有每日全局额度；BYOK 请求不计入站长额度

## 配置

所有配置都在 `.env`（完整示例见 [`.env.example`](.env.example)）：

| 变量 | 说明 | 默认值 |
| --- | --- | --- |
| `DREAMAI_FREE_API_KEY` | 免费模型密钥（智谱 / 硅基流动等） | 空 |
| `DREAMAI_FREE_BASE_URL` | 免费模型 OpenAI 兼容接口 | `https://open.bigmodel.cn/api/paas/v4` |
| `DREAMAI_FREE_MODEL` | 免费模型名 | `glm-4-flash` |
| `DREAMAI_BYOK_BASE_URL` | 自带 Key 的接口地址 | `https://api.deepseek.com/v1` |
| `DREAMAI_BYOK_MODELS` | BYOK 可选模型，`id\|名称\|是否推理` | DeepSeek V3 / R1 |
| `DREAMAI_SYSTEM_PROMPT` | 自定义人设（单行） | 见 `config.py` |
| `DREAMAI_RATE_LIMIT` / `_WINDOW` | 每 IP 限流次数 / 窗口秒数 | 30 / 600 |
| `DREAMAI_DAILY_LIMIT` | 免费模型每日全局上限（BYOK 不计入） | 600 |
| `DREAMAI_MAX_CONCURRENCY` | 同时进行的模型请求上限 | 6 |

## 部署到服务器

目标环境：宝塔面板 + Nginx + systemd，站点目录 `/www/wwwroot/liguijiang.com`。

```bash
# 1. 本地打包（排除虚拟环境与缓存）
tar czf dreamai-web.tar.gz --exclude .venv --exclude __pycache__ --exclude .env \
    -C dreamai-web .

# 2. 上传并解压
scp dreamai-web.tar.gz root@8.156.85.180:/tmp/
ssh root@8.156.85.180 'mkdir -p /tmp/dreamai-release && tar xzf /tmp/dreamai-web.tar.gz -C /tmp/dreamai-release'

# 3. 一键部署（自动备份原站、保留 lsl、建 venv、装依赖、写 systemd 与 Nginx）
ssh root@8.156.85.180 'bash /tmp/dreamai-release/deploy/install.sh'
```

部署脚本会：

1. 把原站点打包到 `/www/backup/liguijiang.com-site-<时间>.tar.gz`；
2. 清空站点目录，**只保留 `lsl`**（找不到 `lsl` 时会中止，除非 `FORCE=1`）；
3. 创建 `.venv` 并从阿里云镜像安装依赖；
4. 写入 `dreamai-web.service` 并启动（2 个 uvicorn worker，监听 `127.0.0.1:8000`，可用 `PORT` 覆盖）；
5. 复用宝塔已有证书，写入 Nginx 配置并重载；
6. 调用 `/api/health` 做健康检查。

> 首次部署后记得在服务器上编辑 `/www/wwwroot/liguijiang.com/.env` 填写
> `DREAMAI_FREE_API_KEY`，然后 `systemctl restart dreamai-web`。

常用运维命令：

```bash
systemctl status dreamai-web
journalctl -u dreamai-web -f
nginx -t && nginx -s reload
```

### 本次上线记录（2026-10-25）

| | |
| --- | --- |
| 服务器 | `8.156.85.180` · Alibaba Cloud Linux 3 · Nginx 1.28 |
| 站点目录 | `/www/wwwroot/liguijiang.com` |
| 服务端口 | `127.0.0.1:8010`（8000 已被同机其他项目占用） |
| systemd | `dreamai-web`（已设置开机自启） |
| HTTPS 证书 | `/www/server/nginx/conf/ssl/liguijiang.com.pem`（含 www，有效期至 2027-01-05） |
| 旧站备份 | `/www/backup/liguijiang.com-site-20261025-200115.tar.gz` |
| Nginx 配置备份 | `/www/server/panel/vhost/nginx/liguijiang.com.conf.bak-20261025-200259` |

清理旧站时保留了 `lsl/` 与 `.well-known/`（后者用于证书续期），其余文件已删除。

## 请求链路

```
浏览器 ──POST /api/chat──▶ Nginx ──▶ FastAPI ──▶ OpenAI 兼容接口
   ▲                         │           │
   └──── SSE: meta/delta ────┘           └─ 密钥只在服务端内存中
         reasoning/done/error
```

- 前端把整段对话历史发给后端，后端裁剪为最近 30 条 / 6 万字符后追加人设；
- 任何一个 Provider 只要兼容 `/chat/completions` 就能接入，换模型只改 `.env`；
- `reasoning_content` 事件单独下发，渲染为可折叠的「思考过程」。

## 安全与隐私

- API Key 仅存放于服务器 `.env`（权限 `600`），不会写进前端产物；
- 对话只保存在访问者自己的浏览器里，服务端不落盘、不需要登录；
- 所有模型输出经 DOMPurify 清洗后再渲染，链接统一 `noopener noreferrer`；
- 响应头包含 CSP、`X-Frame-Options: DENY`、`nosniff` 等；
- 按 IP 限流与并发上限，避免公开站点被刷。

## 和 DreamAI 仓库的关系

DreamAI 仓库里的 `dream_ai/` 是命令行版本的智能体内核（Provider、记忆、工具、
自主规划）。网页版复用了它的产品定义与配置约定，把「对话」这一层做到了浏览器里；
后续可以把 `dream_ai.tools` 的工具调用与 `autonomy` 引擎接到 `/api/chat` 的工具
事件上，让网页端也具备联网、文件与多步任务能力。

## 团队

| | |
| --- | --- |
| 李贵江 | 发起人 · 全栈开发 |

- 电话：191 1073 4460
- 邮箱：599575094@qq.com
- GitHub：<https://github.com/Li-Guijiang>

## License

MIT — 与 DreamAI 仓库保持一致。
