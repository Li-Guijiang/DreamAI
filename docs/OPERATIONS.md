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
| 快不快 | `avgTtft` / `ttftMax` | 平均 1s 以内正常；`ttftMax` 远高于平均值说明偶发慢轮，不是常态 |
| 在问什么 | `byIntent` | `error` 占比异常升高通常意味着上游或部署出问题，用户在排错 |
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
