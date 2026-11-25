# 运维手册（OPERATIONS）

面向站点管理员的一页手册：平时看什么、出事怎么判、动哪里。所有字段都能用
`curl` 直接拿到，无需登录。

## 1. 每日巡检（两条命令）

```bash
curl -s https://liguijiang.com/api/health | python -m json.tool
curl -s https://liguijiang.com/api/usage  | python -m json.tool
```

### 1.1 `/api/health` 先看这四项

| 字段 | 正常值 | 需要处理时 |
|---|---|---|
| `ok` / `configured` | `true` / `true` | `configured=false` 说明服务端没配 `DREAMAI_FREE_API_KEY`，免费通道返回 503 |
| `upstream` | `closed` | `open` = 熔断打开，见第 2.1 节；`half-open` = 正在探测，等一轮即可 |
| `breaker.retryIn` | `0.0` | 大于 0 表示还有几秒才放行探测请求 |
| `cache.hitRate` | 0～1 | 长期为 0 且 `requests` 不低 → 大多对话温度高于 0.3，属正常；`full=true` 且 `evictions` 持续增长 → 考虑调大 `DREAMAI_CACHE_MAX_ITEMS` |

`limiter.tracked` 是当前被限流器观察的客户端数量（只有数量，不含 IP）。持续贴着
20000 的上限说明被刷，见第 2.3 节。

### 1.2 `/api/usage` 回答五个问题

| 问题 | 字段 | 判读 |
|---|---|---|
| 用了多少 | `requests` / `failures` | `failures / requests` 长期高于 10% 先看 `byModel.failureRate` 定位是哪家 |
| 花了多少 | `costUsd` / `costKnown` | `costKnown=false` 表示价格表里缺模型，总数是下限 |
| 缓存省了多少 | `cachedTokens` / `cachedShare` | 命中提示词缓存的那部分输入；占比高说明前缀稳定，成本被真正压下来了 |
| 快不快 | `avgTtft` / `ttftMax` | 平均 1s 以内正常；`ttftMax` 远高于平均值说明偶发慢轮，不是常态 |
| 在问什么 | `byIntent` | `error` 占比异常升高通常意味着上游或部署出问题，用户在排错 |
| 走的哪一家 | `byProvider` | 某一家独占失败时先看 `byProvider`，再看该家下的 `byModel.failureRate` |
| 有多少没走模型 | `local` / `blocked` / `cancelled` | `blocked` 高 = 熔断频繁；`cancelled` 高 = 用户等不及提前关页 |

### 1.3 一行日志怎么读

```
chat done id=req_1a2b3c4d tier=deep intent=error ttft=0.84s total=6.21s chars=812 model=deepseek-chat cache=miss cost=$0.0012
```

- 用户报障时先要 `X-Request-Id`（页面事件的 `requestId` 与响应头同值），
  `grep req_1a2b3c4d /www/wwwroot/liguijiang.com/logs/*.log` 即可还原整轮；
- `tier` / `intent` 来自启发式分类，只决定预算与骨架，不是用户可见的标签；
- `cache=hit` 的轮次没有成本行——它没有调用上游。

本地回答（身份问答、主人指令）也有自己的 id，日志行以 `local reply id=...` 开头。

## 2. 常见故障与处置

### 2.1 熔断打开（`upstream=open`）

**现象**：连续 3 次上游失败后，所有免费请求被快速拒绝，用户看到「上游连续失败，
已暂停约 30 秒」。

**判读**：日志里找 `breaker open state=open failures=3 openings=N cooldown=30.0s`。
`openings` 是进程累计；`lastOpenedAt` 告诉你最后一次打开的时间。

**处置顺序**：
1. 等 `retryIn` 秒让探测请求自己跑——半开状态只放一个探测，探测成功即自动闭合；
2. 探测仍失败 → 上游真挂了。去厂商控制台看状态页，或用 `curl` 直接打一次上游 API 验证 Key；
3. 若配置了 `DREAMAI_FALLBACK_*`，重试与降级已自动发生，熔断打开说明主备都过了三次失败。

### 2.2 每日额度耗尽

**现象**：免费请求返回 429，`code=daily_limit`，文案为「今天的免费额度已经用完」。

**判读**：日志每天只写一条
`daily budget exhausted: 2000 requests served for 2026-11-10`；`/api/usage` 的
`daily.count` 与 `dailyLimit` 对照即可确认。

**处置**：额度按自然日重置，无需重启。要临时放宽改 `DREAMAI_DAILY_LIMIT` 后
`systemctl restart dreamai-web`。

### 2.3 限流（`code=rate_limited`）

单 IP 在 600 秒窗口内最多 30 次请求。响应带 `Retry-After` 与
`X-RateLimit-Remaining`，规规矩矩的客户端会自己降速。`limiter.tracked` 贴着
20000 上限且大量 429 → 大概率被刷：在 Nginx 层加黑名单，不要靠应用层扛。

### 2.4 上游 404

**现象**：用户看到「没有找到这个接口或模型：请检查 base_url 是否需要以 /v1 结尾，
以及模型名是否拼写正确」。

这类错误**不会重试**（重试同样的地址永远失败）。排查顺序：
1. 启动日志里的 `routing: ...` 行——确认 `DREAMAI_MODEL_BY_TIER` 已被读取且
   没有出现 `tier map names models this site does not serve` 告警；
2. `curl` 直接打上游的 `/models` 接口确认模型名存在；
3. Key 有权限但模型名打错时，同样表现为 404。

### 2.5 想临时关缓存

`DREAMAI_CACHE_TTL=0` 并重启。缓存关闭后 `cache.enabled=false`、`hitRate` 恒为 0，
misses 不再计数（没有查询发生，不算流量）。改回正数即恢复。

## 3. 重启与部署

```bash
cd /www/wwwroot/liguijiang.com && git pull && bash web/deploy/install.sh
systemctl restart dreamai-web
```

计数器（`/api/usage` 的所有数字）是进程级的：重启即清零，`uptime` 字段就是为此
而存在的。每日额度也随进程重置——这是已知边界，不是缺陷。

## 4. 日志速查表

服务日志（`journalctl -u dreamai-web` 或站点日志目录）里值得 grep 的行：

| 想知道什么 | 命令 |
|---|---|
| 某一轮请求的完整轨迹 | `grep req_1a2b3c4d`（id 来自响应头 / `requestId` 事件） |
| 熔断什么时候开过 | `grep "breaker open"` |
| 每日额度是否耗尽过 | `grep "daily budget exhausted"` |
| 疑似提示注入 | `grep "possible injection"` |
| 本地回答流量 | `grep "local reply"` |
| 慢轮（首 token 超 2 秒） | `grep "chat done" \| grep -E "ttft=[2-9][0-9]*\."` |

## 5. 用户看到的文案 → 含义对照

| 用户看到的句子 | 状态 | 谁的问题 |
|---|---|---|
| 「Key 无效、无权限或余额不足」 | 401 / 402 / 403 | 用户自己的 Key 或站点 Key 配置 |
| 「请求太频繁了，等十几秒再试」 | 429 | 频率限制，等即可 |
| 「等上游响应超时了」 | 408 | 网络/上游，可重试 |
| 「没有找到这个接口或模型」 | 404 | 配置：base_url 或模型名 |
| 「上游认为请求的格式不对」 | 400 / 422 | 参数超出模型支持范围 |
| 「这个模型已经下线」 | 410 | 模型被厂商移除：换模型或更新配置清单，重试无用 |
| 「这次请求的内容太长了」 | 413 | 输入太长，分段发送 |
| 「上游连续失败，已暂停约 30 秒」 | 熔断打开 | 上游连续失败，等 `retryIn` |
| 「今天的免费额度已经用完啦」 | 每日预算 | 等次日或填自己的 Key |
| 「请求体不符合要求（…）」 | 400 校验 | 客户端发的 JSON 不符合接口约定 |

文案由 `web/app/errors.py` 的 `final_message` 统一决定：400 / 422 保留厂商原话
（它知道是哪个参数被拒），其余用我们自己的句子；JSON、HTML、traceback 永远不进
聊天气泡。

## 6. 本地端排查

CLI / 桌面端没有 HTTP 接口，排查靠三样东西：

1. `/stats`——会话用了多少模型轮次、输入输出各多少 token、缓存命中多少、花了多少钱，
   以及上一问落在哪个难度档；
2. `/about`——当前 provider 与配置；
3. 历史折叠是请求时行为：`/clear` 之前存储的历史永远完整，
   长会话变慢先想到折叠（摘要以「以下是本轮之前的对话摘要」开头）。

本地端给 provider 传的 `max_tokens` 随难度变化：light ≤ 768、deep = 配置值 + 1024
（封顶 8192）。如果回答明显被截断，先确认问题没有被误判成 light
（一眼判据：`/stats` 的 `last tier`）。

## 7. token 与成本一直是 0 怎么办

按顺序排查，四步能定位绝大多数情况：

1. 上游是否支持 `stream_options.include_usage`。少数网关见到这个字段就返回 400
   （文案为「上游认为请求的格式不对」）。此时设 `DREAMAI_STREAM_USAGE=0` 并重启：
   流式回答照常，但 token / 成本按设计保持为 0——这是取舍，不是故障；
2. 用 `curl -N` 看一轮 SSE 的末尾有没有 `event: usage`。没有说明厂商没给计数，
   与本站无关；
3. 有 `usage` 但 `/api/usage` 仍为 0：检查该轮是否被熔断、缓存命中或提前取消，
   这三种情况不产生新的上游计数；
4. 计数在、`costUsd` 为 0 且 `costKnown=false`：价格表里没这个模型。用
   `DREAMAI_PRICE_OVERRIDES=模型名=输入单价,输出单价` 补上（单位为美元/百万 token），
   重启后启动日志会打印 `price overrides: 模型名`。多个条目用分号隔开。
   怕缓存价不准就再给第三个数：`模型名=输入,输出,缓存输入`，见第 9 节。

示例：

```bash
DREAMAI_PRICE_OVERRIDES='new-model=0.5,1.5;gpt-4o=2.5,10'
```

`costKnown=false` 只代表「有模型没价格」，不代表「没拿到 usage」；免费模型
单价为 0 是已知价格，不会误标。

## 8. 事故时间线的两端

日志里现在成对出现：

```
breaker open state=open failures=3 openings=2 cooldown=30.0s
breaker recovered state=closed openings=2
```

`breaker recovered` 由半开状态那一个探测请求成功后写入；只有正常轮次不会打这一行。
`possible injection id=... severity=high` 是规则覆盖或身份切换的尝试，
`severity=low` 只是想看系统提示，两者都加固了 system prompt 且都不写缓存。

## 9. 提示词缓存：为什么账上的数字变小了

四家厂商都做提示词缓存，但报账口径不同，`web/app/adapters.py` 已经把差异抹平，
运维只需要认三个字段：

| 字段 | 含义 | 与 `promptTokens` 的关系 |
|---|---|---|
| `promptTokens` | 本轮所有输入 | 总数 |
| `completionTokens` | 本轮所有输出，含思考 | 总数 |
| `cachedTokens` | 其中由缓存提供的那部分输入 | 子集，不叠加 |

判读要点：

1. `cachedTokens` 永远不会大于 `promptTokens`。看到更大的数，说明上游报错了口径，
   代码会按 `promptTokens` 截断，账单不会被压低；
2. `cachedShare` 才是有效指标。系统提示 + 历史前缀稳定时它应该逐步上升；
   一直为 0 说明每轮前缀都在变（例如把时间戳写进了 system prompt），缓存等于没用；
3. `costUsd` 下降不等于故障。缓存命中的输入按更低的单价计费，价格表里
   `CACHE_PRICES` 记录的就是这个单价；没有该单价的模型按原价计，属于保守估计；
4. Anthropic 的缓存写入（cache creation）按 1.25 倍计费，本系统把它并入
   `promptTokens` 按原价算，因此这一部分会略微低估，属于已知取舍（ADR 0014）。

本地端（CLI / 桌面）的 `/stats` 多两行，含义与上面一致：

```
tokens          in 2,000 / out 100 / cached 1,500 (75%)
cost            $0.0041
```

当出现 `unmeasured`（provider 没有返回计数）或 `unpriced`（价格表没有该模型）时，
`cost` 会写成 `at least $…` 或 `unknown (…)`，而不是一个看起来完整的数字。

## 10. 回答写到一半就断了

SSE 正常结束不等于回答完整：模型达到 `max_tokens` 时同样会干净地关闭连接。
现在每轮 `done` 事件带两个字段：`finish`（`length` / `stop` / `filter` / `other`）
与 `truncated`（布尔值，始终存在）。日志里对应 `finish=length`。

排查顺序：

1. 看 `/api/usage` 的 `truncated` 与 `truncationRate`。偶发的几条不需要处理；
   长期高于 5% 说明回答预算偏紧；
2. 看 `truncatedByTier`。集中在 `deep` 就调 deep 档的预算，不要动全局
   `DREAMAI_MAX_TOKENS`；集中在 `light` 多半是难度误判，先查问题分类；
3. 看 `byFinish.filter`。出现 `filter` 不是截断，是上游安全策略拦了内容，
   与预算无关，不要靠加 token 解决；
4. `cache.hitRate` 突然下降但 `truncated` 上升，是正常联动：被截断的回答
   **不写缓存**，同一个问题再问一次会重新走上游，这是设计而非缓存失效。

判定要点：

- `X-Cache: MISS` 连续出现在同一个问题上，配合 `finish=length`，符合预期；
- `done.finish` 缺失说明上游这个网关根本不报结束原因，此时 `truncated=false`
  只代表「未知」，不代表「完整」；换一个网关或查看上游文档；
- 本地端 `/stats` 的 `truncated` 行由 SDK 的 `finish_reason` 得出，与 web 端
  共用同一张归一映射，测试锁住两份副本不会漂移。

调整示例（提高 deep 档上限，不影响其它档）：

```bash
DREAMAI_MAX_TOKENS=4096
```

改完重启，观察一轮 `truncationRate`；不要在事故中同时改价目表和预算，
否则无法判断是哪个改动起了作用。

## 11. 超时、重试与跨重启的计数

本轮新增两个开关，均不改动页面：

| 变量 | 默认值 | 作用 |
|---|---|---|
| `DREAMAI_UPSTREAM_READ_TIMEOUT` | `240` | 流式响应「等待下一个字节」的秒数，允许范围 10～900，超出会被夹到边界；按请求生效，不影响共享连接池 |
| `DREAMAI_USAGE_STATE` | 空 | 用量计数快照文件的路径；留空表示关闭，重启计数归零 |

### 11.1 超时与重试

- `httpx` 读超时现在记为 `408`、其它传输错误记为 `503`，两者都在可重试集合内，
  只在**首个 token 之前**重试一次；失败日志末尾带 `status=408` 一类的字段。
- 排查时先区分 `status=408`（等上游等太久）与 `status=401`（Key 问题），
  两者处置完全不同；`status` 缺省表示请求从未到达 HTTP 响应，按快速失败处理。
- 若上游是慢推理模型且日志频繁出现 `status=408`，先调高
  `DREAMAI_UPSTREAM_READ_TIMEOUT`，而不是调高重试次数；重试不会让慢模型变快。
- 熔断器半开探测若因客户端断连而没有回执，最多一个冷却周期后自动释放槽位，
  不会再出现「`upstream=half-open` 且此后所有请求被拒」的僵死状态。

### 11.2 用量快照

启用示例（Linux 部署）：

```bash
DREAMAI_USAGE_STATE=/var/lib/dreamai/usage.json
```

判定要点：

1. `/api/usage` 的 `usagePersisted=true` 才说明开关已生效；为 false 时重启仍归零。
2. 文件采用临时文件 + `os.replace` 原子写入，只含聚合计数与原始累加量，
   **不含** IP、消息、请求 ID 或任何文本内容；可以安全纳入常规备份。
3. 写入时机为进程正常退出，以及每累计 25 轮一次；硬杀进程最多丢失 24 轮。
4. 文件损坏、版本不符或字段非法时，启动日志打印
   `usage snapshot: none` 或 `usage snapshot rejected`，服务照常启动、计数从 0 开始，
   不会带着一个看似合理的错误总数继续运行。
5. `uptime` 始终是当前进程的运行时间，不从快照恢复；这是刻意区分的：
   「今天服务重启过几次」和「本周累计花了多少钱」是两个问题。
6. 快照只适合单实例。多副本部署时须为每个实例配置不同路径，否则后写者覆盖前者。

## 12. 启动自检与错误分类

### 12.1 配置自检

服务启动时执行 `validation.check_settings()`，结果同时写入日志与
`/api/health` 的 `configChecks` 数组。判定要点：

1. 日志首行 `config checks: clean` 表示无发现；否则为
   `config checks: N warning(s), M info`，随后每条一行
   `config check <code>: <说明>`。
2. `severity=warning` 表示配置可用但存在隐患，**不会阻止启动**；
   `severity=info` 只是记录某个开关的状态。
3. 常见 code 与处置：

   | code | 含义 | 处置 |
   |---|---|---|
   | `fallback_partial` | 备用上游只配了部分字段 | 补全 base URL、Key、模型三者，或全部留空 |
   | `cooldown_shorter_than_timeout` | 熔断冷却远短于一次读超时 | 调大 `DREAMAI_BREAKER_COOLDOWN` |
   | `daily_below_window` | 日限额低于单窗口限额 | 确认这是有意为之，否则调大 `DREAMAI_DAILY_LIMIT` |
   | `system_prompt_empty` | 身份与安全规则为空 | 立即恢复 `DREAMAI_SYSTEM_PROMPT` |
   | `price_overrides_invalid` | 价格修正条目被忽略 | 按 `模型=输入,输出[,缓存]` 格式修正 |
   | `price_table_inconsistent` | 价格表内部矛盾 | 见下方第 5 点 |
   | `cache_capacity_low` | 缓存容量过小 | 调大 `DREAMAI_CACHE_MAX_ITEMS` |
   | `rate_window_short` | 限流窗口不足一分钟 | 调大 `DREAMAI_RATE_WINDOW` |
   | `max_concurrency_over_limit` | 并发数超过限流额度 | 降低 `DREAMAI_MAX_CONCURRENCY` |

4. `configChecks` 不含任何密钥、带凭据的 URL 或系统提示词内容，可安全展示。
5. `price_table_inconsistent` 表示价格表本身矛盾：价格不是有限非负数、
   缓存输入单价高于原价、或某模型只有缓存价没有原价。多由
   `DREAMAI_PRICE_OVERRIDES` 的第三个数字写错引起；修正后重启即可。
   `stream_usage_off` / `cache_off` / `usage_state_on` 三条为 `severity=info`，
   仅记录开关状态，无需处置。

### 12.2 错误事件的分类

SSE 的 `error` 事件除 `message` 外还带 `code`、`status`、`retryable`，
完整取值与处置见 `docs/API.md` 第 4 节。排障时按 `code` 而非中文句子判断：

- `auth` / `address`：配置问题，重试无意义；
- `payload`：请求参数或长度问题；
- `rate_limit` / `breaker` / `upstream`：等待后重试，`retryable=true`；
- `internal`：服务内部异常，查日志中的 `chat failed` 行与 `status=` 字段。

重要变更：上游失败现在**一定**产生 `error` 事件，并计入熔断器失败数，
不再以 `chars=0` 的 `done` 收尾。若仍观察到「空白回答但事件是 done」，
说明运行的是旧版本或异常未从流式泵传播，应先核对 `/api/health` 的 `version`。

私有档案会话（有效 owner cookie）的回答不会写入共享响应缓存，
因此 `X-Cache` 对同一问题连续两次均为 `MISS` 属于预期行为。

## 13. 免费额度与请求边界

### 13.1 免费额度现在真正生效

此前日限判断误用了 `Upstream.kind`（协议类型 `openai`），而免费上游的
标识是 `provider.id == "free"`，因此 `DREAMAI_DAILY_LIMIT` 一直没有生效。
修复后的判定要点：

1. `/api/usage` 的 `daily.count` 与 `/api/health` 的 `freeRemaining`
   会随免费请求变化；长期不动说明请求走的是 BYOK，或版本仍为旧版。
2. 达到上限后返回 HTTP 429，响应体 `code=daily_limit`；
   BYOK 请求不消耗免费额度，不受该上限影响。
3. 开启 `DREAMAI_USAGE_STATE` 后，同一天重启会从快照恢复已用额度，
   **不会重新发放一次配额**；跨天自动归零。
4. 快照中的 `daily.count` 会被裁剪到 `DREAMAI_DAILY_LIMIT`，
   手工编辑文件无法放大额度；若快照日期不是今天，恢复逻辑直接忽略。
5. 若部署中原本依赖「日限不生效」，升级后会首次出现 429；
   应先核对 `DREAMAI_DAILY_LIMIT` 与预期流量，再决定是否调大。

### 13.2 请求被拒时的定位

`/api/chat` 的参数校验失败返回 HTTP 400 与 `code=invalid_body`，
`error` 中带字段位置。常见触发：

| 现象 | 原因 |
|---|---|
| `temperature` 相关 | 超出 0.0–2.0 |
| `messages` 相关且末条为 assistant | 历史最后一条必须是 user |
| `memory` / `context` / `style` 相关 | 单条长度或条数超过上限 |
| `maxTokens` 相关 | 不在 128–8192 之间 |

完整字段约束见 `docs/API.md` 第 2.1 节。客户端不应依赖中文句子判断
失败原因，应读取 `code` 与字段位置。

## 14. 背压、缓存内存与日志边界

### 14.1 流式队列

| 变量 | 默认值 | 作用 |
|---|---|---|
| `DREAMAI_STREAM_QUEUE_SIZE` | `64` | 上游泵与 SSE 写入器之间的队列容量，允许范围 8～512 |

队列有界后，慢读者会让泵暂停读取上游，而不是让待发送 token 无限堆积。
运维判据：

1. 客户端长期不读时，上游生成变慢属于预期，不应伴随 RSS 持续上涨。
2. 心跳仍为每 12 秒一次 `: ping`；若心跳也消失，问题在泵或上游，不在队列。
3. 不要把容量调到 8 试图「减少延迟」；太小会让正常网络抖动触发背压。

### 14.2 缓存的内存上限

`DREAMAI_CACHE_MAX_BYTES` 默认 4194304（4 MiB），`0` 表示仅按条数限制，
上限 64 MiB。`/api/usage` 与 `/api/health` 的 `cache` 对象新增三个字段：

| 字段 | 含义 |
|---|---|
| `maxBytes` | 当前字节预算，0 表示未启用 |
| `byteEvictions` | 因字节预算淘汰的条目数（与按条数淘汰分开计数） |
| `byteFull` | 当前占用是否已达预算 |

排查要点：

1. `items` 远小于 `capacity` 却不断 miss，先看 `byteEvictions`；
   字节预算先于条数上限触发是正常的。
2. 单条回答超过整个预算时不会被缓存，也不淘汰任何已有条目；
   长回答类请求持续 miss 属于预期。
3. 启动时出现 `cache_bytes_small` 说明预算低于 64 KiB，
   先确认是否由 `DREAMAI_CACHE_MAX_BYTES` 误填导致。
4. `bytes` 统计 UTF-8 字节而非字符数；中文回答的字节数约为字符数的三倍。

### 14.3 日志中的客户端地址

失败日志只记录网段：`ip=203.0.x.x id=req_...`。IPv4 保留前两段，
IPv6 保留前两段十六进制；限流仍按完整地址计数，行为不变。
排障时用 `id` 关联同一请求的多条日志，用网段判断某片网络是否异常。
完整 IP 不再出现在 `chat failed`、`circuit open` 与
`unexpected chat error` 三类日志中。

### 14.4 响应缓存头

`/api/health` 与 `/api/usage` 返回 `Cache-Control: no-store`；
`/api/chat` 返回 `Cache-Control: no-store, no-transform`。
`no-transform` 禁止代理改写流式响应体，若自建反向代理启用了压缩或缓冲，
应先确认它没有忽略该指令。

## 15. 按模型统计的上限与配置自检补充

### 15.1 模型名与 other 桶

| 变量 | 默认值 | 作用 |
|---|---|---|
| `DREAMAI_MAX_TRACKED_MODELS` | `64` | 按模型统计表的条目上限，允许范围 2～512 |

自定义模型名按原样接受（网关的模型清单无法枚举），但统计表不能因此无限增长。
超出上限的模型统一计入 `byModel.other`，token、费用与请求数都在该行累加。

判读要点：

1. `requests` **不是** `byModel` 各行之和；`blocked` 的请求从未到达模型，
   没有对应的模型行。
2. `other` 行占比高，说明正在使用大量自定义模型名；若关心具体分布，
   调大 `DREAMAI_MAX_TRACKED_MODELS` 后重启，但旧快照中的明细已经归并，
   无法回溯拆分。
3. 启动时出现 `tracked_models_low`，说明上限低于 4，绝大多数模型会落进
   `other`，应核对变量是否误填。
4. 快照来自更高上限的进程时，导入会自动压缩到当前上限且保持总量不变。

### 15.2 URL 与系统提示词

新增三条启动发现：

| code | 含义 | 处置 |
|---|---|---|
| `base_url_invalid` | 某个 base URL 或 Key 链接缺少 scheme、缺少 host、含空格、含凭据或带 query/fragment | 改为 `https://host/path` 形式；凭据应放在独立的 Key 变量中 |
| `system_prompt_long` | 系统提示词超过 8000 字符 | 缩短；它每轮都重发，会挤占回答预算 |
| `tracked_models_low` | 见上一节 | 调大模型表上限 |

`base_url_invalid` 的 message 只写**变量名与原因**，不回显 URL 本身，
因此即使误把密码写进 URL，也不会泄漏到日志或 `/api/health.configChecks`。
自检只报告、不阻止启动；配置错误仍会在下一次真实请求中表现为失败。

### 15.3 统计不变量

排障时可以用以下关系判断计数是否自洽：

```
requests     == sum(byModel.requests) + blocked
failures     == sum(byModel.failures) + blocked
truncated    == sum(byModel.truncated) == sum(truncatedByTier)
promptTokens == sum(byModel.promptTokens)
```

`tests/test_stats_invariants.py` 在实时快照、快照往返和超限归并三种情况下
都会验证这些等式；若修改统计代码后等式不再成立，应先修统计再发版。

## 16. 心跳、并发准入与重试

### 16.1 时序配置

| 变量 | 默认值 | 作用 |
|---|---|---|
| `DREAMAI_HEARTBEAT_SECONDS` | `12` | 上游静默多久后发送 `: ping`，允许 1～120 秒 |
| `DREAMAI_ADMISSION_TIMEOUT` | `10` | 等待并发槽位的秒数；`0` 表示无限等待（旧行为） |

判据：

1. 浏览器一直收不到首个 token，但每 12 秒有一条 `: ping`：连接正常，
   上游在思考或响应很慢。
2. `admissionTimeouts` 上升且 SSE 收到 `code=concurrency_limit`：
   请求在队列里超时，未到上游。应检查是否有客户端长期占用连接，
   或调大 `DREAMAI_MAX_CONCURRENCY`。
3. `heartbeat_long` 表示心跳超过 60 秒，常见反向代理会先关闭连接，
   应把心跳调短。
4. `admission_timeout_short`（0～1 秒）通常意味着正常排队也被误判为拒绝，
   除非明确需要快速失败，否则应调大。

### 16.2 新增统计字段

`/api/usage` 新增：

| 字段 | 含义 |
|---|---|
| `admissionWaitAvg` / `admissionWaitMax` / `admissionWaitSamples` | 等待并发槽位的平均、最大时长与样本数（秒） |
| `admissionTimeouts` | 等待超时次数；计入 `blocked` |
| `retries` / `retriesByStatus` | 上游重试次数及按 HTTP 状态分组（`none` 表示无状态码） |
| `fallbacks` | 主用上游失败后切换备用模型的次数 |

`admissionWait*` 与 `avgTtft` 是两种不同的时间：前者发生在请求进入上游之前，
后者从请求开始算到首个 token。慢在排队还是慢在上游，靠这两个字段区分。

`retries` 与 `fallbacks` 是额外的**上游**请求，不计入 `requests`。
若供应商账单里的调用次数高于 `requests`，先看这两个字段再怀疑计费错误。

### 16.3 模型名自检

`model_id_invalid` 表示免费模型、备用模型或某个 BYOK 模型的 id 为空、
含空白、超过 128 字符或含控制字符。message 只写原因，不回显模型名。
模型名会被原样发送给供应商，启动阶段发现拼写问题比第一次聊天再失败更省事。

## 17. 发布前的一致性检查

以下两条命令在 CI 每条推送上运行，发布前应再手动执行一次：

```bash
python web/tools/check_assets.py
python web/tools/check_site.py
```

第一条检查静态资源文件是否存在、同一资源的 `?v=` 是否一致；
第二条在此基础上检查页面链接、`#anchor`、重复 `id`、
`target="_blank"` 的安全属性、页面元信息、CSS 本地引用、
service worker 缓存版本与下载清单。

常见失败与处置：

| 输出标签 | 含义 | 处置 |
|---|---|---|
| `MISSING ASSET` | HTML 引用了不存在的 CSS/JS | 补文件，或修正路径 |
| `VERSION CONFLICT` | 两个页面给同一个文件标了不同版本 | 统一到最新 `?v=`，并确认该版本文件已更新 |
| `BROKEN PAGE LINK` / `BROKEN ANCHOR` | 页面或锚点目标不存在 | 同步修改导航或 `id` |
| `STALE SERVICE WORKER` | `sw.js` 的缓存版本低于服务端 `VERSION` | 提升 `dreamai-shell-vX.Y.Z`，否则访客会继续拿到旧页面 |
| `BAD MANIFEST` | 下载清单的版本、文件名、哈希、大小或日期不自洽 | 修正 `downloads/latest.json` |
| `unversioned (warning)` | 本地图片没有 `?v=` | 默认不阻断；需要全量管控时用 `--strict` |

完整的发布顺序、三个版本号的关系与发布后验证见 `docs/RELEASE.md`。

## 19. 配置项被裁剪时如何发现

服务端配置在加载时对数值设定了上下限。超出范围的输入不会导致启动失败，
而是取边界值并记入 `/api/health.configClamped`：

```json
{"configClamped": ["temperature", "cacheTtlJitter", "heartbeatSeconds"]}
```

判据：

1. 列表为空表示所有环境变量都在支持范围内。
2. 出现字段名说明该变量的实际生效值与设置值不同。先核对
   `docs/CONFIGURATION.md` 中该变量的约束，再修正环境变量。
3. `configClamped` 只发布字段名，不发布变量值；它不会出现在
   `/api/config` 中。
4. 目前记录裁剪的字段：`temperature`、`cacheTtlJitter`、
   `heartbeatSeconds`、`admissionTimeout`、`streamQueueSize`、
   `usageSaveInterval`。其它配置由 `_env_int` 等工具在解析阶段裁剪，
   不在该列表中。

文档本身也有守卫：`python web/tools/check_env_docs.py` 会检查
`docs/CONFIGURATION.md` 是否覆盖全部 44 个变量，并核对表中写成纯数字的
默认值；`python web/tools/check_docs_index.py` 会检查 ADR 与文档索引，
以及 ADR 编号是否连续、是否重复。两者均在 CI 中运行。

## 20. 元数据与版本的发布前检查

```bash
python web/tools/check_meta.py        # head 元数据、Open Graph、图标、manifest
python web/tools/check_versions.py    # 四个版本号的关系、预缓存目标存在性
python web/tools/check_site.py        # 含 serviceWorkerPins 预缓存版本比对
python web/tools/check_dom_refs.py    # JS 中的 id 选择器是否有对应节点
```

`check_meta.py` 判读：

1. `missing og:*`：公开页面缺少社交预览标签，分享时卡片为空白。`noindex`
   页面（如 `offline.html`）豁免此检查，但必须有基础 head 字段。
2. `missing rel=apple-touch-icon`：添加到主屏时使用通用图标。
3. `og:title ... != <title>`：分享标题与页面标题不一致。
4. `manifest theme_color differs`：PWA 安装后的状态栏颜色与页面不一致。

`check_versions.py` 只检查必须成立的关系，不要求四个版本相等：

1. SW 缓存版本不得低于服务端 `VERSION`；
2. `latest.json` 与 `desktop/package.json` 版本必须相同；
3. changelog 最新里程碑不得低于服务端版本；
4. `check_site.py` 的 `serviceWorkerPins` 会抓出 SW 预缓存里过时的 `?v=`——
   这类问题在线上几乎不可见，因为浏览器命中旧缓存后拿到的就是旧资源。

四个版本各自的含义与发布顺序见 `docs/VERSIONS.md`。

`check_dom_refs.py` 报告 `UNRESOLVED: 脚本 #id` 时，表示脚本查询的节点
不存在，相关功能会静默失效。若该节点由桌面外壳在运行时注入，
须在工具的 `DESKTOP_INJECTED` 白名单中登记并写明原因，不能删除检查。

## 18. 用量快照的健康状态

`/api/usage.usageState` 是快照持久化的状态，不再只能靠日志判断：

| 字段 | 含义 |
|---|---|
| `enabled` | 是否配置了 `DREAMAI_USAGE_STATE` |
| `loadStatus` | 启动时的读取结果，见下文 |
| `lastSaveAt` | 最近一次成功写入的 Unix 时间；尚未写入为 `null` |
| `saveFailures` | 累计写入失败次数 |

`loadStatus` 判读：

1. `disabled` / `absent`：未配置或首次运行，属于正常初始状态。
2. `restored`：计数与当日配额已恢复。
3. `corrupt`：JSON 损坏或版本不兼容；文件保留，不会被覆盖读取。
4. `tampered`：校验和不匹配，文件内容曾被改动。
5. `oversized`：超过 8 MiB，启动时不解析。
6. `unreadable`：路径权限导致无法访问。
7. `rejected`：JSON 合法但计数不合法，未导入。

写入相关：

1. `DREAMAI_USAGE_SAVE_INTERVAL`（默认 60 秒，允许 0～3600）控制周期性刷新；
   `0` 表示只在关闭时写一次。
2. `saveFailures` 持续增加通常意味着磁盘满或目录不可写；快照失败不影响聊天，
   但计数会在重启后丢失最近一段时间的部分数据。
3. `cache.items` 可能包含尚未清理的过期条目，判断当前可用容量看
   `cache.liveItems`；`cache.pruned` 是写入前主动清理的数量。
4. 缓存键包含供应商、模型、消息、温度、`top_p`、`presence_penalty` 与预算；
   修改采样配置后不会命中旧答案。
5. `DREAMAI_CACHE_TTL_JITTER`（默认 0，允许 0～0.5）给每条缓存的 TTL
   加上随机浮动。若大量答案在同一时刻写入，默认值会让它们同时过期，
   造成瞬时回源；设置 0.1 左右可把过期时刻分散开。该值在
   `cache.ttlJitter` 中回显，便于确认配置已生效。


