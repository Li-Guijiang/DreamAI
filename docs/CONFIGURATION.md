# 服务端配置说明

本文列出 Web 服务读取的全部 `DREAMAI_*` 环境变量。它们由
`web/app/config.py` 的 `load_settings()` 解析，启动即固定，修改后须重启服务。
命令行版本的配置见 [SETUP.md](./SETUP.md)，其中 `DREAMAI_API_KEY`、
`DREAMAI_MODEL` 等变量属于本地客户端，与本文的 Web 服务端变量不是同一套。

未设置时均使用表中默认值。数值经过上下限裁剪，超限不会报错而是取边界值。
启动时的建议项显示在 `/api/health.configChecks` 与启动日志中。

`web/tools/check_env_docs.py` 检查本文是否覆盖代码里的每一个配置项，
避免新增配置后文档漏写。

## 1. 核心模型与输出

| 变量 | 默认值 | 作用 | 约束 |
|---|---|---|---|
| `DREAMAI_TEMPERATURE` | `0.7` | 默认采样温度；仅温度不高于 0.3 的请求会查答案缓存 | 裁剪到 0～2；请求可覆盖 |
| `DREAMAI_MAX_TOKENS` | `4096` | 单次生成的上限 | 最小 256 |
| `DREAMAI_TOP_P` | 未设置 | 核采样参数；设置后参与缓存键 | 合法浮点数，未设置时不发送该参数 |
| `DREAMAI_PRESENCE_PENALTY` | 未设置 | 重复内容惩罚；设置后参与缓存键 | 合法浮点数，未设置时不发送该参数 |
| `DREAMAI_SYSTEM_PROMPT` | 内置人格文本 | 追加到所有请求前的系统提示 | 不写入日志与公开配置 |
| `DREAMAI_STREAM_USAGE` | `true` | 是否请求上游在流末返回 token 用量 | 关闭后 token 与成本统计不可用 |
| `DREAMAI_PROMPT_CACHE` | `true` | 是否向上游发送提示词缓存标记 | 供应商不支持时会自动忽略 |

## 2. 免费上游

| 变量 | 默认值 | 作用 | 约束 |
|---|---|---|---|
| `DREAMAI_FREE_API_KEY` | 空 | 免费档供应商密钥 | 为空时免费聊天返回 503；密钥不会写入日志或公开配置 |
| `DREAMAI_FREE_BASE_URL` | `https://open.bigmodel.cn/api/paas/v4` | 免费档接口地址 | 必须是 HTTP(S) URL，启动时会校验 |
| `DREAMAI_FREE_MODEL` | `glm-4-flash` | 免费档模型名 | 会被原样发送给供应商，不得含空白或控制字符 |
| `DREAMAI_FREE_LABEL` | `GLM-4-Flash` | 公开配置中展示的档位名称 | 仅用于界面显示 |
| `DREAMAI_FREE_KEY_URL` | 智谱控制台地址 | 公开配置中引导用户申请密钥的链接 | 必须为 HTTP(S) URL |

## 3. BYOK、模型表与价格覆盖

| 变量 | 默认值 | 作用 | 约束 |
|---|---|---|---|
| `DREAMAI_BYOK_BASE_URL` | `https://api.deepseek.com/v1` | 自带密钥档的接口地址 | 必须为 HTTP(S) URL |
| `DREAMAI_BYOK_KEY_URL` | DeepSeek 控制台地址 | 申请自带密钥的引导链接 | 必须为 HTTP(S) URL |
| `DREAMAI_BYOK_LABEL` | `DeepSeek` | 自带密钥档的展示名称 | 仅用于界面显示 |
| `DREAMAI_BYOK_MODELS` | 内置两项 | 自带密钥档可选模型列表 | JSON 数组，每项含 `id` / `label`；模型 id 不得含空白 |
| `DREAMAI_MODEL_BY_TIER` | 空 | 难度档位到模型的映射 | 形如 `simple=模型,medium=模型,complex=模型`；未知档位会告警 |
| `DREAMAI_PRICE_OVERRIDES` | 空 | 覆盖内置价格表 | JSON 对象，每项为正数价格；非有限数会被拒绝 |

## 4. 备用上游与传输

| 变量 | 默认值 | 作用 | 约束 |
|---|---|---|---|
| `DREAMAI_FALLBACK_BASE_URL` | 空 | 主用失败后切换的接口地址 | 必须与 `FALLBACK_API_KEY`、`FALLBACK_MODEL` 同时设置才生效 |
| `DREAMAI_FALLBACK_API_KEY` | 空 | 备用上游密钥 | 不写入日志或公开配置 |
| `DREAMAI_FALLBACK_MODEL` | 空 | 备用模型名 | 不得含空白或控制字符 |
| `DREAMAI_UPSTREAM_READ_TIMEOUT` | `240` 秒 | 上游单次流读取超时 | 裁剪到不超过 900 秒；超时会按可重试错误处理 |

## 5. 限流、配额与输入边界

| 变量 | 默认值 | 作用 | 约束 |
|---|---|---|---|
| `DREAMAI_RATE_LIMIT` | `30` | 每个客户端在窗口内的请求数 | 最小 1 |
| `DREAMAI_RATE_WINDOW` | `600` 秒 | 限流窗口长度 | 最小 30 秒 |
| `DREAMAI_DAILY_LIMIT` | `2000` | 全站每日免费请求上限 | `0` 表示不限 |
| `DREAMAI_MAX_CONCURRENCY` | `6` | 同时处理的最大请求数 | 最小 1；超出后按 `ADMISSION_TIMEOUT` 等待 |
| `DREAMAI_MAX_INPUT_CHARS` | `12000` | 单轮用户输入的字符上限 | 最小 500；超限返回 400 |
| `DREAMAI_MAX_HISTORY_MESSAGES` | `30` | 参与提示词构建的历史消息数 | 最小 2 |
| `DREAMAI_MAX_HISTORY_CHARS` | `60000` | 参与提示词构建的历史字符数 | 最小 2000 |
