# Architecture

Dream AI is a small full-stack assistant with three runtimes:

```
Browser / Electron renderer
        │  HTTPS + SSE
        ▼
FastAPI service (app/)  ──►  OpenAI-compatible model endpoint
        │
        ├─ static site (web/)
        └─ /api/read  ──► public web pages (SSRF guarded)

Electron main (desktop/electron/)
        ├─ local file tools      workspace only
        ├─ document engine       docx / xlsx / pptx / pdf / md
        ├─ coding agent          workspace/Dream AI 项目
        └─ tray / updater
```

## Web service (`app/`)

- `main.py` — routes, rate limiting, daily budget, SSE streaming, memory / context injection, `/api/read`.
- `llm.py` — streaming client for any OpenAI-compatible endpoint; emits `content`, `reasoning` and `usage`.
- `config.py` — environment-driven settings and public model catalog.
- Static files live in `web/` and are served by Nginx in production; Uvicorn serves the entry points during local development.

### Chat request flow

1. Browser posts `POST /api/chat` with messages, model, provider and optional `memory` / `context`.
2. Server resolves the upstream (site free model or the user's BYOK key), applies style and safety prompts.
3. Upstream SSE chunks become `meta`, `delta`, `reasoning`, `usage`, `done` or `error` events.
4. The client renders Markdown, records local usage, and keeps the conversation in `localStorage`.

### Client-only AI features

| Feature | Where it lives | Notes |
| --- | --- | --- |
| Long-term memory | `localStorage` | Injected into the system prompt per request |
| Knowledge base | `localStorage` + BM25 in `app.js` | Top 4 chunks become `context`, citations shown in chat |
| Artifact canvas | sandboxed iframe | HTML / SVG / Markdown only, no same-origin access |
| Prompt library | `localStorage` | Presets + user prompts, `/` command menu |
| Usage dashboard | `localStorage` + `/api/usage` | Local counts and aggregate server counters |
| PWA shell | `web/sw.js` | Network-first navigation, cache-first assets, `/api/*` never cached |

## Desktop (`desktop/`)

- `electron/main.js` — window, IPC, tray, global shortcut, update check.
- `electron/local-tools.js` — scan / organise / rename inside the selected workspace.
- `electron/documents.js` — pure-JS document generation; PDF through `printToPDF`.
- `electron/agent.js` — coding agent: project directories, file writes, command execution, dev servers.
- `electron/update.js` — version / `latest.yml` helpers used by tests.

### Coding mode

1. The renderer asks the model for a project plan (JSON).
2. It creates `workspace/Dream AI 项目/<name>` through IPC.
3. Files are generated in small batches and written with path containment checks.
4. Setup commands run with a timeout, output cap and a command log.
5. A dev server is started, its output is polled, failures trigger a fix-and-retry loop.
6. The user can open the folder, open the URL, or stop the server from the chat card.

## Deployment

- Nginx serves `web/` at `https://liguijiang.com`, proxies `/api/` to `127.0.0.1:8010` with buffering disabled.
- `dreamai-web.service` runs Uvicorn with two workers.
- `/lsl/` is a sibling static directory with its own Nginx location (teacher tools).
- Desktop installers and `latest.yml` live under `web/downloads/`.

## Local development

```bash
# web
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt
.venv/Scripts/uvicorn app.main:app --port 8787

# desktop
cd desktop && pnpm install && pnpm start
```

## 一次请求的完整链路

`POST /api/chat` 从进入到结束共十步，每一步都能单独测试，因为它们都被拆成了纯函数
或小类，不依赖网络：

```
POST /api/chat
  ├─ 1. 校验：消息条数、单条长度（maxInputChars）、频率限制、每日额度
  ├─ 2. 选上游：站点免费模型，或用户自带 Key（free / deepseek / openai / ...）
  ├─ 3. 清洗历史：去验证令牌与主人档案 → 联系方式脱敏 → 长文本裁剪
  │      → 折叠重复轮次 → 超长时保留最近 6 轮、其余转摘要
  ├─ 4. 组提示词：人格 + 语气 + 作答策略 + 题型骨架 + 分级提示 + 追问提示
  ├─ 5. 定参数：难度分级 → 温度 / token 上限 / 是否换模型
  ├─ 6. 查缓存：温度 ≤ 0.3 时按 (供应商, 模型, 消息, 参数) 求哈希
  ├─ 7. 过熔断：打开状态直接返回“稍后再试”，不再打上游
  ├─ 8. 调上游：重试（首 token 前）→ 必要时降级备用上游 → SSE 解析
  ├─ 9. 推流：delta / reasoning 事件；静默 12 秒发一次 `: ping`
  └─ 10. 收尾：记录 usage、成本、TTFT，写缓存，发 done
```

## 提示词的分层

系统提示不是一句话，而是按“先想、再写、最后给样板”的顺序叠加：

| 层 | 作用 | 位置 |
|---|---|---|
| 人格与语气 | 说话方式、禁用词、表情预算 | `identity.py` / `web/app/config.py` |
| 作答策略 | 判断题类型、先声明假设、核对覆盖、不编造 | `render_decision_block()` |
| 推理契约 | 何时展开思考、思考与答案的分界 | `render_reasoning_block()` |
| 答案结构 | 结论先行、分点、表格、代码块 | `render_quality_block()` |
| 对照示例 | 两组“不要这样 / 应该这样” | `render_example_block()` |
| 本轮补充 | 分级提示、题型骨架、追问、语言、注入加固 | 路由内动态追加 |

示例放最后，因为模型对末尾内容更敏感，而示例最接近“照着写”。

## 三个零成本的启发式

都不调用模型：

1. **难度分级**（`quality.classify_tier`）：长度、代码块、问号数、权衡类词汇
   → light / standard / deep → 温度、token 上限、提示语；
2. **题型分类**（`insight.classify_intent`）：报错 / 方案 / 代码 / 写作 / 解释 / 闲聊
   → 各给一个答题骨架；报错优先于方案，因为“怎么改”两类都命中而用户要修法；
3. **重复检测**（`insight.is_repeat`）：中文重叠二元组 + 英文单词重合度 ≥75%
   → 提示换角度，而不是复述同一段答案。

## 流式输出的三个坑

1. **首 token 延迟**：先发 `meta`，客户端立刻知道“开始了”；
2. **代理超时**：静默 12 秒发 SSE 注释行 `: ping`，浏览器忽略、代理计为流量；
3. **取消**：上游经 `asyncio.Queue` 泵送，客户端断开即取消上游，避免为没人读的 token 付费。

## 稳定性四层

| 层 | 机制 | 触发 | 用户看到 |
|---|---|---|---|
| 重试 | `stream_with_retry` | 首 token 前 408/429/5xx | 无感 |
| 降级 | `stream_with_fallback` | 主上游首 token 前失败 | 备用模型的答案 |
| 熔断 | `CircuitBreaker` | 连续 3 次失败 | “暂停约 30 秒” |
| 缓存 | `ResponseCache` | 同问、温度 ≤ 0.3 | 秒回，`X-Cache: HIT` |

顺序有意义：重试解决抖动，降级解决单点，熔断解决雪崩，缓存解决重复。
一旦已输出 token，后三者都不再介入——半截答案拼接比报错更糟。

## 成本与可观测性

- `pricing.py` 按模型单价（美元/百万 token）估算；未知模型返回 `None`，
  `/api/usage` 用 `costKnown=false` 明说“有模型没价”；价格表可用
  `DREAMAI_PRICE_OVERRIDES=model=输入价,输出价;...` 在启动时纠正，无需改代码；
- token 数来自上游：OpenAI 兼容端点要带 `stream_options.include_usage` 才会在流的
  末尾给出 `usage`；Anthropic 分在 `message_start` / `message_delta` 两处；Gemini
  的 `usageMetadata` 会重复出现。三种格式由 `adapters.usage_from_chunk` 归一，
  `llm._stream_raw` 用 `max()` 累加后只发一个 `usage` 事件。JSON 事件不参与文本合流；
- 每轮一行日志：`chat done id=req_xxx tier=deep intent=error ttft=0.84s total=6.21s chars=812 model=... cache=miss cost=$0.0012`；
- `X-Request-Id` 与事件体同值，用户截图即可定位日志；
- `/api/health` 暴露熔断状态与缓存计数，`/api/usage` 暴露 token、成本、命中率。

### 计数落在哪里

计数不再散在 `main.py` 的字符串键里，而是集中在 `web/app/stats.py`：

| 方法 | 何时调用 | 记的是什么 |
|---|---|---|
| `record_turn` | 每轮结束（含失败） | 请求数、失败数、按模型分行、按供应商、按难度分级、按题型、首 token 时间 |
| `record_cancelled` | 客户端中途断开 | 单独计数：token 花了，但既不算成功也不算失败 |
| `record_usage` | 上游回了 usage 字段 | 提示/补全 token、成本；无价模型清 `costKnown` |
| `record_local` | 身份问答、主人指令 | 不经过模型的回答，另记 `local` 行 |
| `record_blocked` | 熔断拒绝 | 一次请求 + 一次失败，单列 `blocked` |

`snapshot()` 是唯一对外形状，两个状态接口共用它，所以加一个数字只改一处。

几个刻意的选择：

1. **按模型分行**带 token 与成本，账单可以解释“这 900 个 token 是推理模型花的”；
2. **平均 TTFT 只统计真的产出首 token 的轮次**，缓存命中与早期失败不计入，
   否则慢下来的那一周看起来很快；样本数 `ttftSamples` 一并给出，避免用一条样本当趋势；
3. **缓存未命中拆成三种**：从没问过、过期、被容量挤掉（`expired` / `evictions`），
   只有后两种说明 TTL 太短或容量太小；
4. **熔断的 `openings` 是进程级累计**，失败计数会被下一次成功清零，看不出“反复抖”。

`/api/usage` 因此回答六个问题：用了多少（requests）、花了多少（costUsd / byModel，
每行自带失败率）、快不快（avgTtft / ttftMax——平均会藏住一次 40 秒的等待，
最差值不会）、在问什么（byIntent）、走的是哪一家（byProvider）、
多少没走模型（local / blocked / cancelled）。

`costKnown=false` 只表示「有模型没价格」，不表示「这一轮没拿到 usage」——没拿到
usage 时根本不会碰这个标志。免费模型单价为 0 且已知，同样不会误标成未知。

限流器也有自己的快照：`/api/health` 的 `limiter.tracked` 是正在被观察的客户端数——
只有数量，不含 IP；`X-RateLimit-Remaining` 头把剩余额度告诉客户端，
让它能在被拒绝之前自己降速。

## 本地端（CLI / 桌面）一轮的路径

网页版是流式的，本地端不是：本地端拿到整段回答，因此能改写、能重试、能补代码块闭合。
`dream_ai/core/agent.py` 的 `chat()` 顺序如下：

1. `capture_preference` / `handle_owner_command`：`记住：…`、`【更新档案】…` 直接本地回答，不掉模型；
2. `trim_long_input`：长粘贴只留头、关键行、尾，再进历史；
3. `compress_history`：超过 `max_history_chars` 的历史折叠成摘要——最新几轮原样保留，
   更早的变成带角色标注的摘要（只作用于发给模型的副本，存储不动）；
4. `classify_tier` + `reply_budget`：判定难度并折算 token 预算（light 封顶 768，deep 在配置值上加 1024，
   再封顶 8192），**预算相对配置值收放，不是替换配置**；
5. 提示拼装：`tier_hint` + `intent_prompt` + 重复检测 + 语言跟随（英文问题附英文提示）
   + 指代检测（折叠后追问时指明「对象在摘要里」），全部拼进 system prompt 末尾；
6. 调 provider（带上 `max_tokens`）。老式一参签名仍可用：只吞掉指名 `max_tokens` 的 `TypeError`；
7. 后处理：`strip_filler` → `limit_emoji` → `close_fences` → `dedupe_sentences`；
8. `looks_empty`：空回答重试一次，仍空则明说“没生成有效内容”；
9. `mask_contacts`（公开面）→ 写入会话历史；`turn_count` 只数真正调模型的轮次，
   CLI 的 `/stats` 读它与 `last_tier`。

与网页版的差别值得记住：网页版在流式过程中无法改写已发出的字，所以它把力气花在
“发之前”（提示词、预算、缓存、熔断）；本地端能改全文，所以把力气花在“收之后”（去套话、闭代码块、去重复）。

## 模型接入的分层

```
providers.py   声明：谁、地址、鉴权方式、模型清单、Key 页面
     ↓
adapters.py    构造请求 / 解析 SSE：OpenAI 兼容、Anthropic、Gemini
     ↓
llm.py         HTTP、重试、降级、错误映射
     ↓
main.py        业务：提示词、参数、缓存、熔断、事件
```

新增一家 OpenAI 兼容厂商只改 `providers.py` 的一张表；换协议才动 `adapters.py`。

## 建议的阅读顺序

1. `docs/adr/0004`～`0008`：每个决策解决了什么现象；
2. `web/app/main.py` 的 `chat()`：对照上面的十步；
3. `quality.py` / `insight.py`：最短、最独立，适合改着玩；
4. `llm.py` + `adapters.py`：三种协议的差异；
5. 动手从“加一条测试”开始，每个模块都有对应的 `tests/test_*.py`。

## 已知边界

- 启发式分类会漏判生僻说法，代价是结构普通，不是答案错误；
- 价格表是快照，会过期，`costKnown` 是提醒；
- 语义缓存被明确放弃：错答比不答更贵；
- 注入检测只覆盖明显话术，不追求穷举。
