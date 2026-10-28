# Dream AI 使用指南（命令行版 · v0.4.0）

<sub>[返回文档索引](./README.md)</sub>

> 这份指南面向第一次打开本项目的人，从零讲清楚：**现在这个 AI 能做什么、
> 怎么把它跑起来、每个命令怎么用、常见报错怎么处理。**
> 项目会持续迭代到 `v0.5`、`v0.6`……直到 `v1.0`，本指南会跟着版本一起更新。
>
> 阅读范围说明：
> 1. 本文件只讲**命令行（`dream_ai` 包）**。Web 服务见 [../web/README.md](../web/README.md)；
>    Windows 桌面端见 [../desktop/README.md](../desktop/README.md)。
> 2. 英文对外说明见 [README.md](../README.md)，全部文档的索引见同目录的 [文档索引](./README.md)。
> 3. 只想知道怎么装、不想看功能讲解，可直接看 [SETUP.md](./SETUP.md)。

---

## 0. 先搞清楚：现在的 Dream AI 能做什么

当前版本是 **v0.4.0（Autonomous Planning，自主规划）**。它由四层能力组成：

| 能力层 | 版本 | 现在能做什么 | 默认状态 |
|---|---|---|---|
| **对话** | v0.1 | 通过可替换的模型后端聊天；不绑定任何厂商 | 开启 |
| **记忆** | v0.2 | 会话历史存到本地、下次启动自动恢复；记住你的长期偏好并注入提示词 | 开启（持久化） |
| **工具** | v0.3 | 调用计算器、时钟；沙箱内读写文件；可选联网搜索；写操作要二次确认 | 计算器/时钟默认开，文件/搜索默认关 |
| **自主规划** | v0.4 | 把一个目标拆成有序计划，按 **思考 → 行动 → 观察 → 反思** 循环执行；有步数预算、失败重试、保护动作确认、全程轨迹可复盘 | 开启 |

### 现在还做不到的事（不要误解）

- **没有 API Key 时是离线占位模式**：回复只是把你说的话回显出来，**不是真实模型在理解**，用来熟悉命令和流程。
- **规划器目前是离线规则版**：只能识别简单的"时间、计算"意图；由模型自己理解目标、自主拆解计划，属于后续版本。
- **模型自动选工具（原生 function-calling）还没接**：现在工具由 `/tool` 手动调用，或自主循环按计划调用。
- 暂不支持流式打字输出、向量语义记忆、本地开源模型托管。这些都在路线图里，见 [ROADMAP.md](ROADMAP.md)。

---

## 1. 环境准备（只做一次）

### 1.1 需要什么

- **Python 3.11 或更高版本**（本项目在 3.11 / 3.12 / 3.13 上测试通过）。
- 终端里能运行 `python` 命令。
- 想跑容器才需要 Docker；纯命令行使用不需要。

### 1.2 检查 Python

在项目目录打开终端（PowerShell），执行：

```powershell
python --version
```

看到类似 `Python 3.13.16` 即可。如果提示 `python 不是内部或外部命令`，先去 python.org 安装 Python，安装时勾选 **Add Python to PATH**，然后重开终端。

### 1.3 进入项目目录

你的仓库在 `D:\Github\Dream-AI`：

```powershell
cd D:\Github\Dream-AI
```

> 全新克隆（在别的机器上）：
> ```powershell
> git clone https://github.com/Li-Guijiang/DreamAI.git
> cd DreamAI
> ```

### 1.4（推荐）创建虚拟环境并安装依赖

**Windows PowerShell：**

```powershell
python -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -e .
```

**macOS / Linux：**

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install --upgrade pip
pip install -e .
```

> 装开发工具（跑测试、lint、打包）用：
> ```powershell
> pip install -e ".[dev]"
> ```

成功后，命令行提示符前面会出现 `(.venv)`。以后每次使用前，先 `cd` 进项目目录并激活虚拟环境。

---

## 2. 第一次启动

### 2.1 复制配置文件

**Windows：**

```powershell
copy .env.example .env
```

**macOS / Linux：**

```bash
cp .env.example .env
```

`.env` 已经被 `.gitignore` 忽略，**永远不会提交到 GitHub**，里面可以放心写 Key。

### 2.2 启动

```powershell
python -m dream_ai
```

安装包之后也可以直接用命令：

```powershell
dream-ai
```

启动成功会先看到横幅和欢迎语，随后是一行离线/在线提示，最后是三行状态：

```text
ℹ Offline demo mode: no hosted API key was configured ...
Memory: persistent (C:\Users\你\.dream_ai)
Autonomy: on (max steps: 10, retries: 2)
Tools: 2 registered
```

- 没填 Key 时先出现 **Offline demo mode（离线演示模式）** 提示，这是正常的。
- `Memory: persistent`：会话和偏好会存到本地。
- `Autonomy: on`：自主任务已开启。
- `Tools: 2 registered`：当前注册了计算器和时钟。

退出：输入 `/quit` 或 `/exit`。

---

## 3. 两种运行模式

### 3.1 离线演示模式（不需要 Key）

`.env` 里 `DREAMAI_API_KEY=` 留空，程序自动回退到本地占位后端。
此时可以完整体验命令、记忆、工具、自主循环，但对话内容是回显，不做真实理解。

### 3.2 接入真实模型（以 DeepSeek 为例）

1. 到 DeepSeek 开放平台申请一个 API Key。
2. 打开项目根目录的 `.env`，填这几项：

```ini
DREAMAI_PROVIDER=openai_compat
DREAMAI_BASE_URL=https://api.deepseek.com/v1
DREAMAI_API_KEY=你的Key粘贴到这里
DREAMAI_MODEL=deepseek-chat
```

3. 保存后重启 `python -m dream_ai`。启动后不再提示离线模式，而是显示
   `Connected via provider: openai-compat`。

**其他兼容接口对照**（改 `DREAMAI_BASE_URL` 和 `DREAMAI_MODEL` 即可）：

| 平台 | `DREAMAI_BASE_URL` | `DREAMAI_MODEL` 示例 |
|---|---|---|
| DeepSeek | `https://api.deepseek.com/v1` | `deepseek-chat` |
| OpenAI | `https://api.openai.com/v1` | `gpt-4o-mini` |
| 通义 DashScope 兼容模式 | `https://dashscope.aliyuncs.com/compatible-mode/v1` | `qwen-plus` |

> 也可以不写进 `.env`，启动时临时覆盖参数（优先级高于 `.env`）：
>
> ```powershell
> python -m dream_ai --provider openai_compat --api-key 你的Key --model deepseek-chat --base-url https://api.deepseek.com/v1
> ```

---

## 4. 四大功能怎么用

### 4.1 聊天

直接在 `you ›` 后面输入内容，回车发送即可。

| 命令 | 作用 |
|---|---|
| 直接输入文字 | 和 Dream AI 对话一轮 |
| `/clear` | 清空当前会话历史（保留系统提示词） |
| `/about` | 查看当前模型、工具、自主模式、消息轮数、偏好数量 |

### 4.2 记忆（v0.2）

| 命令 | 作用 | 示例 |
|---|---|---|
| `/remember <内容>` | 记住一条长期偏好，之后自动注入系统提示 | `/remember 我喜欢骑自行车，回复简洁一点` |
| `/memory` | 查看已记住的偏好 | — |
| `/forget` | 清空全部偏好 | — |
| `/clear` | 只清空会话历史，不动偏好 | — |

默认会话历史和偏好存在 `~/.dream_ai/`（Windows 是 `C:\Users\你\.dream_ai\`），
下次启动自动恢复。相关开关见第 6 节配置表。

### 4.3 工具（v0.3）

**先看当前有哪些工具：**

```text
/tools
```

**手动调用某个工具：**

```text
/tool <工具名> {"参数名": "参数值"}
```

四个内置工具说明：

#### ① `calculator`（安全计算器，默认开启，safe）

支持数字、`+ - * / % // **`、括号，以及 `abs`、`round`、`min`、`max`、`sqrt`。
**不使用 `eval`**，会拒绝变量、导入、下标等一切危险写法。

```text
/tool calculator {"expression": "2 + 3 * 4"}
/tool calculator {"expression": "(12 + 8) / 5"}
/tool calculator {"expression": "sqrt(144)"}
```

真实输出：

```text
tool › 2 + 3 * 4 = 14
tool › (12 + 8) / 5 = 4
tool › sqrt(144) = 12
```

#### ② `clock`（本地时钟，默认开启，safe）

```text
/tool clock
```

真实输出：

```text
tool › Current local time: 2026-10-24 19:56:07 +0800
Weekday: Saturday
```

#### ③ `file_read` / `file_write`（沙箱文件，默认关闭，protected）

先在 `.env` 开启：

```ini
DREAMAI_FILE_ACCESS_ENABLED=true
# DREAMAI_WORKSPACE_DIR=.dream_ai/workspace   # 可选：自定义沙箱目录
```

- 所有路径都限制在工作区目录内，**禁止绝对路径、禁止 `..` 越界**。
- `file_write` 属于写操作，**执行前必须二次确认**。

读取：

```text
/tool file_read {"path": "notes.txt"}
```

写入（回车后会问 `Tool 'file_write' will modify files. Confirm? [y/N]`，输入 `y` 或 `yes` 才执行，其他输入都取消）：

```text
/tool file_write {"path": "notes.txt", "content": "Dream AI v0.4 第一条笔记"}
```

#### ④ `web_search`（联网即时答案，默认关闭，protected）

先在 `.env` 开启：

```ini
DREAMAI_WEB_SEARCH_ENABLED=true
```

```text
/tool web_search {"query": "OpenAI"}
```

> 该工具走 DuckDuckGo 即时答案接口，只返回简短摘要；网络不通会报友好错误，不会让程序崩溃。

**总开关：** `DREAMAI_TOOLS_ENABLED=false` 会关闭整个工具注册表。

### 4.4 自主任务（v0.4）

让 Dream AI 自己拆计划、逐步执行。

#### 发起一个自主任务

```text
/run What time is it now, and calculate 12 * 7?
```

引擎会：**规划 → 思考 → 调用工具 → 观察结果 → 反思 → 进入下一步**，
全部记录进轨迹。开启详细日志后能看到每一步事件：

```ini
DREAMAI_AUTONOMY_VERBOSE=true
```

#### 复盘上一次任务

```text
/trace
```

会打印：目标、最终状态、每一步的标题/状态/观察结果，以及完整的
`plan / think / act / observe / reflect / confirm / done / abort` 事件轨迹。

#### 安全机制

- **步数预算**：`DREAMAI_MAX_STEPS` 限制一次任务最多调用多少次工具，耗尽自动停止，防止死循环。
- **失败重试**：`DREAMAI_MAX_RETRIES` 设置每步失败后额外重试次数，耗尽则该步标记失败并停止。
- **保护动作确认**：文件写入等保护动作在自主执行前会弹出
  `⚠ Protected action 'file_write' {...}` 和 `Confirm this action? [y/N]`；
  输入 `y`/`yes` 才执行，拒绝后整个任务安全取消。

#### 离线演示目标示例

```text
/run What time is it now?
/run What time is it now, and calculate 12 * 7?
```

---

## 5. 命令速查表（v0.4.0 全量）

| 命令 | 作用 |
|---|---|
| `/help` | 显示帮助 |
| `/run <目标>` | 发起自主多步任务 |
| `/trace` | 复盘上次任务的计划、步骤与轨迹 |
| `/tools` | 列出已注册工具、风险等级、必填参数 |
| `/tool <名称> <JSON>` | 手动调用工具，如 `/tool calculator {"expression": "2 * 3"}` |
| `/remember <内容>` | 记录一条长期偏好 |
| `/memory` | 查看已记住的偏好 |
| `/forget` | 清空全部偏好 |
| `/clear` | 清空当前会话历史 |
| `/about` | 查看模型、工具、自主模式、轮数、偏好、上次任务状态 |
| `/quit` 或 `/exit` | 退出 |
| 其他任意文字 | 进入普通聊天 |

---

## 6. 配置项速查表（`.env`）

### 模型后端

| 变量 | 默认值 | 说明 |
|---|---|---|
| `DREAMAI_PROVIDER` | `openai_compat` | `openai_compat` 任意兼容接口；`local` 强制离线 |
| `DREAMAI_BASE_URL` | `https://api.deepseek.com/v1` | 接口地址 |
| `DREAMAI_API_KEY` | 空 | 留空自动回退离线占位模式 |
| `DREAMAI_MODEL` | `deepseek-chat` | 模型名 |
| `DREAMAI_SYSTEM_PROMPT` | 内置人设 | 助手的系统提示词 |

### 记忆

| 变量 | 默认值 | 说明 |
|---|---|---|
| `DREAMAI_PERSISTENCE` | `true` | 是否把会话和偏好持久化到磁盘；`false` 仅当前进程内存 |
| `DREAMAI_DATA_DIR` | `~/.dream_ai` | 记忆文件目录；可写相对路径如 `.dream_ai` |

### 工具

| 变量 | 默认值 | 说明 |
|---|---|---|
| `DREAMAI_TOOLS_ENABLED` | `true` | 工具注册表总开关 |
| `DREAMAI_FILE_ACCESS_ENABLED` | `false` | 是否开启沙箱文件读写 |
| `DREAMAI_WEB_SEARCH_ENABLED` | `false` | 是否开启联网搜索 |
| `DREAMAI_WORKSPACE_DIR` | `<数据目录>/workspace` | 文件工具的沙箱根目录 |

### 自主规划

| 变量 | 默认值 | 说明 |
|---|---|---|
| `DREAMAI_AUTONOMY_ENABLED` | `true` | 自主模式总开关；`false` 后 `/run` 不可用 |
| `DREAMAI_MAX_STEPS` | `10` | 单次任务最大工具调用次数（步数预算） |
| `DREAMAI_MAX_RETRIES` | `2` | 单步失败后的额外重试次数；`0` 不重试 |
| `DREAMAI_AUTONOMY_VERBOSE` | `false` | 是否实时打印每一步 think/act/observe/reflect 事件 |

---

## 7. 运行内置示例（不用进交互命令行）

在项目根目录执行：

```powershell
python examples/basic_chat.py      # 单轮最小聊天示例
python examples/tool_demo.py       # 列出工具并跑计算器、时钟
python examples/autonomy_demo.py   # 跑一个两步自主任务并打印计划与轨迹
```

这些示例不需要 API Key，离线即可运行。

---

## 8. 用容器运行（可选，需要 Docker）

```bash
# 拉取镜像
docker pull ghcr.io/li-guijiang/dream-ai:latest

# 离线演示模式
docker run -it --rm ghcr.io/li-guijiang/dream-ai:latest

# 接入真实模型
docker run -it --rm \
  -e DREAMAI_API_KEY=你的Key \
  -e DREAMAI_BASE_URL=https://api.deepseek.com/v1 \
  -e DREAMAI_MODEL=deepseek-chat \
  ghcr.io/li-guijiang/dream-ai:latest
```

镜像同时提供 `linux/amd64` 和 `linux/arm64` 架构。镜像包页面见
[Packages](https://github.com/Li-Guijiang/DreamAI/pkgs/container/dream-ai)。

---

## 9. 常见问题排查

| 现象 | 原因 | 处理 |
|---|---|---|
| `python 不是内部或外部命令` | Python 未加入 PATH | 重装 Python 勾选 Add to PATH，重开终端 |
| `No module named openai` | 依赖没装或虚拟环境没激活 | 激活 `.venv` 后 `pip install -e .` |
| 回复开头是 `[Local demo mode]` | 没填 `DREAMAI_API_KEY` | 在 `.env` 填 Key 后重启；这属于离线回退，不是报错 |
| 提示 Provider authentication error | Key、地址、模型名不匹配，或 Key 过期 | 核对 `.env` 三项与平台要求一致 |
| 联网搜索报错 | 网络不通或接口超时 | 检查代理/防火墙；工具本身不会让程序崩溃 |
| `Path escapes the workspace sandbox` | 文件路径越界 | 只能用工作区相对路径，不要写绝对路径或 `..` |
| `Tool error: Unknown tool: 'xxx'` | 工具名拼错或该工具被开关关闭 | 先 `/tools` 看当前注册了哪些工具 |
| 改了 `.env` 不生效 | 没有重启程序 | 退出 `/quit` 后重新 `python -m dream_ai` |
| `/run` 提示自主模式关闭 | `DREAMAI_AUTONOMY_ENABLED=false` | 改回 `true` 并重启 |

跑测试和代码检查（开发者用）：

```powershell
pytest
ruff check dream_ai tests examples
```

---

## 10. 版本路线与接下来会有什么

- **v0.5 / v0.6 ……**：在现有基础上逐步增强模型集成、计划质量与能力面。
- **v1.0.0**：稳定版——公开 API 稳定、配置与记忆备份、错误处理加固、面向普通用户的友好体验。
- **Future**：优先支持本地开源模型自托管、模型切换不丢会话与记忆、数据默认留在本地。

完整计划见 [ROADMAP.md](ROADMAP.md)，版本变更记录见 [CHANGELOG.md](../CHANGELOG.md)。
