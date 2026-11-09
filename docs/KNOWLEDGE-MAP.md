# 知识地图：这个仓库用到的知识，以及怎么亲手验证

这份文档不是教程，是一张地图。每条列三件事：这里用到了什么、它在代码里的位置、
以及一个十分钟内能做完的验证。按顺序读，前后能接上。

---

## 1. 一条消息要过几层网络

```
浏览器 → DNS → TCP → TLS → HTTP → 你的 FastAPI 进程 → httpx → 上游模型厂商
```

### 1.1 DNS

浏览器不知道 `liguijiang.com` 在哪里，先去问 DNS：递归解析器 → 根服务器 → `.com`
顶级域 → 你的权威 DNS，最后拿到一个 IP。

- 代码位置：不在代码里。这是部署的一部分（域名解析记录）。
- 验证：`nslookup liguijiang.com`；再 `nslookup liguijiang.com 8.8.8.8` 对比，
  看是不是同一个答案（DNS 缓存与 TTL 的直接体现）。

### 1.2 TCP 三次握手

建立连接要三次往返，为什么不是两次：

1. 客户端 `SYN`（我想连，我的序号是 x）；
2. 服务端 `SYN+ACK`（收到，我的序号是 y，确认 x）；
3. 客户端 `ACK`（收到 y）。

两次不够，是因为服务端无法确认「客户端收到了我的序号」——历史上有过因延迟重发的
旧 SYN 包建立出半开连接的问题。三次是双方都确认「我能发、你能收、你能发、我能收」
的最小次数。

- 代码位置：`web/app/llm.py` 里 `httpx.Timeout(connect=15.0, ...)`，`connect` 超时
  就是卡在这一步。
- 验证：`curl -v https://liguijiang.com` 看输出里的 `Connected to ...`；
  再 `netstat -an | grep 443`（Windows：`netstat -ano | findstr 443`）看连接状态。

### 1.3 TLS 握手

TCP 通了只是「能送字节」，TLS 才让它「送得安全」。要点三条：

1. **证书链**：服务器出示证书，浏览器用内置根证书逐级验签，确认「这个公钥确实属于
   这个域名」。验不过就是 `ERR_CERT_*`，此时不该继续。
2. **密钥交换**：现代 TLS 1.3 用 ECDHE，双方各出一份临时密钥，算出同一个会话密钥。
   临时密钥用完即弃，所以过去的流量不能靠日后拿到私钥来解密（前向保密）。
3. **握手成本**：TLS 1.3 是一次往返（1-RTT），会话复用时可以 0-RTT。

- 代码位置：这一段由 Nginx 与 httpx 代劳。你要管的是**不要把 Key 放进前端**——
  一旦进了 JS，它就要经过 HTTP 才能用，等于公开。
- 验证：`curl -vI https://liguijiang.com 2>&1 | grep -i "SSL\|TLS"`；
  或在浏览器里点地址栏的小锁 → 证书 → 看颁发者与有效期。

### 1.4 HTTP 与状态码语义

一个请求由「方法 + 路径 + 头 + 体」组成，响应由「状态码 + 头 + 体」组成。

状态码不是装饰，它决定程序该做什么：

| 码 | 含义 | 这里怎么处理 |
|---|---|---|
| 401 / 402 / 403 | Key 无效 / 欠费 / 无权限 | 不重试，直接告诉用户改 Key |
| 404 | 地址或模型名不对 | 不重试，提示检查 `base_url` 是否要 `/v1` |
| 408 / 425 / 429 | 超时 / 太早 / 太频繁 | 重试一次，带退避 |
| 5xx | 上游自己坏了 | 重试，再降级，再熔断 |

- 代码位置：`web/app/errors.py`（`RETRYABLE_STATUS`、`CURATED_STATUS`、`final_message`）。
- 验证：`curl -i https://liguijiang.com/api/health` 看头；再请求一个不存在的接口
  `curl -i https://liguijiang.com/api/nope`，观察 404 的两种分支（接口返回 JSON）。

---

## 2. 流式输出：为什么不是一个完整 JSON

模型生成是逐 token 的。如果等全部生成完再返回，用户要盯着空白等十几秒。
SSE（`text/event-stream`）把每个片段立刻推给浏览器。

```
data: {"t":"你"}

data: {"t":"好"}

```

三个必须处理的坑：

1. **代理缓冲**：Nginx 默认攒够一批才转发，于是「流式」变成「一次性」。
   → `X-Accel-Buffering: no` + `Cache-Control: no-transform`。
2. **静默超时**：上游十几秒不出字，中间的代理会掐断连接。
   → 每 12 秒发一行注释 `: ping`，浏览器忽略、代理算作流量。
3. **断开即止损**：用户关页面后还在生成，是纯粹的浪费。
   → 上游经 `asyncio.Queue` 泵送，客户端断开就取消上游任务。

- 代码位置：`web/app/main.py` 的 `event_stream()`；`web/assets/js/app.js` 的读取循环。
- 验证：`curl -N -X POST https://liguijiang.com/api/chat -H "Content-Type: application/json" -d '{"messages":[{"role":"user","content":"用一句话说明 SSE"}]}'`，
  加 `-N` 才能看到逐段到达；不加的话 curl 可能等到结束才打印。

### 2.1 异步与事件循环

FastAPI 跑在 asyncio 事件循环上：一个线程轮流推进成百上千个协程。规则只有一条——
**不要在里面做阻塞调用**（`time.sleep`、同步 IO、CPU 重活），否则整个进程一起卡住。

- 代码位置：`async def` 全是协程；`await` 是「我让出，别人先跑」的位置。
- 验证：把 `main.py` 里某个 `await asyncio.sleep(1)` 改成 `time.sleep(1)`，
  同时开两个请求，第二个会被第一个堵住。

---

## 3. 并发控制：三个限流器各管一件事

| 限流器 | 管什么 | 位置 | 超限表现 |
|---|---|---|---|
| 滑动窗口 | 单个 IP 的请求频率 | `RateLimiter` | 429 + `Retry-After` |
| 信号量 | 同时进行的上游调用数 | `asyncio.Semaphore` | 排队，不报错 |
| 每日预算 | 全站每天的总次数 | `consume_daily_budget` | 503 + 提示 |

为什么要三个：频率防刷、并发防打爆上游与自己内存、预算防一觉醒来账单超标。

- 验证：`for i in $(seq 1 40); do curl -s -o /dev/null -w "%{http_code}\n" -X POST https://liguijiang.com/api/chat -H "Content-Type: application/json" -d '{"messages":[{"role":"user","content":"hi"}]}'; done`
  观察前若干个 200、后面开始出现 429。
