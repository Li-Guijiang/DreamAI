# Dream AI 接口契约

本文件是网页端与服务端之间字段约定的唯一说明。服务未启用 OpenAPI 文档
（`docs_url=None`），因此字段的新增、删除与含义变化须在本文件同步登记。

## 1. 兼容性约定

1. 事件名与已有字段只增不改：新增字段不得改变已有字段的类型或含义。
2. `done` 是流的最后一个事件；`error` 出现后不再发送 `done`。
3. 所有金额单位为美元，所有 token 数为整数，时间字段单位为秒。
4. 客户端遇到未知事件或未知字段应忽略，而不是中断渲染。

## 2. 端点

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/chat` | 流式对话，返回 `text/event-stream` |
| GET | `/api/health` | 服务状态、模型清单、限流与配置自检结果 |
| GET | `/api/usage` | 请求数、token、成本、缓存与截断统计 |
| GET | `/api/download/*` | 静态下载资源 |

`/api/chat` 的响应头：`X-Request-Id`、`X-Cache`（`HIT` / `MISS`）、
`X-RateLimit-Remaining`、`Cache-Control: no-store, no-transform`（禁止缓存，
也禁止代理改写流式响应体）。

### 2.1 `/api/chat` 请求体约束

| 字段 | 约束 |
|---|---|
| `messages` | 1–40 条；每条 `role` 只能是 `user` / `assistant`，`content` 去空白后 1–20000 字符；**最后一条必须是 `user`** |
| `model` | 可选，不超过 128 字符 |
| `provider` | 可选，不超过 64 字符，默认 `free` |
| `apiKey` | 可选，不超过 200 字符 |
| `temperature` | 可选，0.0–2.0 |
| `maxTokens` | 可选，128–8192 |
| `memory` | 可选，不超过 30 条，每条不超过 500 字符 |
| `context` | 可选，不超过 20000 字符 |
| `style` | 可选，不超过 32 字符 |
| `thinking` | 布尔值 |

校验失败返回 HTTP 400，响应体为
`{"error": 中文句子（含字段位置）, "code": "invalid_body"}`，
不使用 FastAPI 默认的 422 与 pydantic 错误数组。

## 3. SSE 事件

<!-- EVENTS
meta
delta
reasoning
usage
error
done
-->

| 事件 | 字段 | 说明 |
|---|---|---|
| `meta` | `model`, `version`, `tier`, `intent`, `requestId`, `cache` | 首个事件，`cache` 为 `hit` / `miss` |
| `delta` | `t` | 正文片段；已合流，一个片段可含多个 token |
| `reasoning` | `t` | 思考过程片段；与正文分开渲染 |
| `usage` | `prompt_tokens`, `completion_tokens`, `cached_tokens` | 上游实际计数，缺省字段表示上游未报告 |
| `error` | `message`, `code`, `status`, `retryable` | 见第 4 节 |
| `done` | `tier`, `intent`, `requestId`, `chars`, `elapsed`, `model`, `truncated` | 可选：`finish`、`usage`、`cost` |

`done.finish` 取值 `length` / `stop` / `filter` / `other`；`done.truncated`
恒为布尔值，`true` 表示回答达到 token 上限，此类回答不会进入响应缓存。
`done.cost` 为 `{"usd": 数值, "text": 展示文本}`。熔断直接拒绝时 `done`
为简化形式，仅含 `tier`、`intent`、`chars`、`elapsed`、`model`、`blocked`，
且不发送 `meta` 以外的其它内容事件。

## 4. error 事件

| 字段 | 类型 | 说明 |
|---|---|---|
| `message` | string | 面向访问者的中文句子，内容与旧版一致 |
| `code` | string | 稳定分类，不随文案变化 |
| `status` | integer 或 null | 上游 HTTP 状态；无状态（内部异常、熔断）时为 null |
| `retryable` | boolean | 是否值得稍后重试，与服务端重试策略同源 |

`code` 取值：

| 值 | 触发条件 | 建议处置 |
|---|---|---|
| `auth` | 401 / 402 / 403 | 更换或充值 Key |
| `payload` | 400 / 413 / 422 | 缩短输入或调整参数 |
| `rate_limit` | 429 | 等待后重试 |
| `address` | 404 / 410 | 检查 base_url 与模型名 |
| `upstream` | 408 / 425 / 5xx 及其它 | 稍后重试 |
| `internal` | 无状态的服务内部异常 | 稍后重试；若持续出现请查日志 |
| `breaker` | 熔断器打开，请求未发往上游 | 等待冷却后重试 |

## 5. 非流式错误响应

参数校验与限流拒绝返回普通 JSON，字段为 `{"error": 中文句子, "code": 稳定分类}`，
对应 HTTP 400 / 413 / 429 / 503。SSE 连接建立后的错误一律走第 4 节的
`error` 事件，不再改变 HTTP 状态。

## 6. 状态端点新增字段

| 端点 | 字段 | 说明 |
|---|---|---|
| `/api/health` | `configChecks` | 启动配置自检结果数组，元素为 `{code, severity, message}`；`severity` 为 `warning` / `info` |
| `/api/usage` | `usagePersisted` | 是否启用用量快照持久化 |
| `/api/usage` | `truncated`, `truncatedByTier`, `byFinish` | 截断计数、按难度分布、结束原因分布 |
| `/api/usage` | `cachedTokens`, `cachedShare` | 提示词缓存命中的输入及其占比 |

`configChecks` 中不包含任何密钥、URL 凭据或系统提示词内容。

### 6.1 `configChecks` 的 code 取值

<!-- CHECK_CODES
fallback_partial
cooldown_shorter_than_timeout
daily_below_window
system_prompt_empty
max_concurrency_over_limit
cache_capacity_low
cache_bytes_small
rate_window_short
price_overrides_invalid
price_table_inconsistent
stream_usage_off
cache_off
usage_state_on
-->

前九项为 `severity=warning`，后三项为 `severity=info`（仅记录开关状态）。
各 code 的含义与处置见 `docs/OPERATIONS.md` 第 12.1 节。
