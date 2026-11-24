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

## 6. 缓存与熔断

| 变量 | 默认值 | 作用 | 约束 |
|---|---|---|---|
| `DREAMAI_CACHE_TTL` | `300` 秒 | 答案缓存有效期；`0` 关闭缓存 | 关闭后 `get()` / `put()` 为空操作 |
| `DREAMAI_CACHE_TTL_JITTER` | `0` | TTL 的随机浮动比例 | 裁剪到 0～0.5；非 0 时同批写入不会同时过期 |
| `DREAMAI_CACHE_MAX_ITEMS` | `128` | 缓存条目数上限 | 最小 1 |
| `DREAMAI_CACHE_MAX_BYTES` | `4194304` | 缓存 UTF-8 字节预算 | `0` 表示不按字节限制 |
| `DREAMAI_BREAKER_THRESHOLD` | `3` | 连续失败多少次后打开熔断 | 最小 1 |
| `DREAMAI_BREAKER_COOLDOWN` | `30` 秒 | 熔断打开后的冷却时间 | 正数 |

## 7. 流时序与背压

| 变量 | 默认值 | 作用 | 约束 |
|---|---|---|---|
| `DREAMAI_HEARTBEAT_SECONDS` | `12` 秒 | 上游静默多久后发送 `: ping` | 裁剪到 1～120 秒；超过 60 秒会告警 |
| `DREAMAI_ADMISSION_TIMEOUT` | `10` 秒 | 等待并发槽位的截止时间 | 裁剪到 0～120 秒；`0` 表示无限等待 |
| `DREAMAI_STREAM_QUEUE_SIZE` | `64` | 单请求的有界事件队列容量 | 裁剪到 8～512；满队列会记录背压并丢弃最旧的非关键事件 |

## 8. 站点展示与持久化

| 变量 | 默认值 | 作用 | 约束 |
|---|---|---|---|
| `DREAMAI_SITE_TITLE` | `Dream AI` | 公开配置中的站点标题 | 仅展示 |
| `DREAMAI_SITE_TAGLINE` | `让每一个想法，都被认真对待` | 公开配置中的标语 | 仅展示 |
| `DREAMAI_REPO_URL` | 本项目 GitHub 地址 | 公开配置中的源码链接 | 必须为 HTTP(S) URL |
| `DREAMAI_USAGE_STATE` | 空 | 用量快照文件路径 | 为空表示不启用；文件只含聚合计数 |
| `DREAMAI_USAGE_SAVE_INTERVAL` | `60` 秒 | 快照周期性刷新间隔 | 裁剪到 0～3600 秒；`0` 表示仅关闭时写入 |
| `DREAMAI_MAX_TRACKED_MODELS` | `64` | 统计表中保留的模型名数量 | 裁剪到 2～512；超出部分归入 `other` |

## 9. 不属于本文的变量

以下变量属于命令行客户端或桌面端，在 [SETUP.md](./SETUP.md) 说明：
`DREAMAI_API_KEY`、`DREAMAI_MODEL`、`DREAMAI_PROVIDER`、`DREAMAI_DATA_DIR`、
`DREAMAI_PERSISTENCE`、`DREAMAI_TOOLS_ENABLED`、`DREAMAI_FILE_ACCESS_ENABLED`、
`DREAMAI_WEB_SEARCH_ENABLED`、`DREAMAI_WORKSPACE_DIR`、`DREAMAI_AUTONOMY_ENABLED`、
`DREAMAI_MAX_STEPS`、`DREAMAI_MAX_RETRIES`、`DREAMAI_AUTONOMY_VERBOSE`、
`DREAMAI_ANIMATIONS`、`DREAMAI_ANIMATION_SPEED`。

所有者认证使用 `DREAMAI_OWNER_SECRET`、`DREAMAI_OWNER_TOKEN` 与
`DREAMAI_OWNER_PROFILE`，详见 [OPERATIONS.md](./OPERATIONS.md)。
