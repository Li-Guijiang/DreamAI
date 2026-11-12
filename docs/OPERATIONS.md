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
