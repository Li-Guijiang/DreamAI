# Changelog

## Unreleased

### Prompt cache accounting

- All three wire formats now report `cached_tokens`, the part of the prompt a
  cache served. Anthropic's cache reads and writes are added back into the prompt
  total (they are outside `input_tokens`); Gemini's thinking tokens are added to
  the completion total (they are outside `candidatesTokenCount`).
- Cached input is billed at its own rate. `pricing.CACHE_PRICES` holds one figure
  per model, because the real discount is 0.5 at OpenAI, 0.26 at DeepSeek, 0.25 at
  Google and 0.1 at Anthropic; a model without a cache price is billed at the list
  price. A `cached` count above the prompt is clamped.
- `/api/usage` reports `cachedTokens` and `cachedShare`, and each model row
  carries its own `cachedTokens`.
- A cache hit is filed under the pseudo-provider `cache`, so the vendor totals add
  up to `requests` without inflating a real vendor.
- `DREAMAI_PRICE_OVERRIDES` takes an optional third number for the cached price:
  `model=input,output,cached`.

### Local session ledger

- `dream_ai/usage.py` keeps turns, tokens and cost for the CLI and the desktop
  shell. Providers expose `last_usage`, filled from the SDK response by the
  hosted provider, and `model`, the key the price table uses.
- `/stats` prints the token line and the cost, and admits its two unknowns:
  `unmeasured` (the provider reported nothing) and `unpriced` (no price for the
  model) read as "at least $…" or "unknown", never as `$0.00`.
- A retry after an empty answer is counted and priced like any other call.

### Small corrections

- The rate limiter prunes clients idle for a whole window instead of emptying the
  table at 20 000 keys, which used to reset every client's quota at once.
- HTTP 425 gets its own sentence instead of the generic one; it stays retryable.
- The retry wait uses equal jitter, so a hundred browsers that lost the same
  upstream do not return in lockstep.

### Usage accounting is real now

- OpenAI-compatible streams ask for `stream_options.include_usage` (switch:
  `DREAMAI_STREAM_USAGE=0`); all three wire formats are parsed into one `usage`
  event per stream, and that event bypasses text coalescing.
- One cost estimate now feeds the counters, the per-model row, the done event
  and the log. A missing price still clears `costKnown`; a free model does not.
- `DREAMAI_PRICE_OVERRIDES` corrects or adds prices at startup.
- `/api/usage` also reports `byProvider`, and the breaker writes a matching
  `breaker recovered` line when a half-open probe succeeds.
- End-to-end test proves a usage event reaches the numbers; both tier classifiers
  now share a parity corpus.

### Streaming integrity

- An unclosed code fence receives one closing delta; the cached copy matches.
- Injection attempts are graded (reveal = info, override = warning) and never
  cached.
- HTTP 410 gets permanent wording, is never retried, and keeps the provider's
  deprecation notice out of the chat bubble.


### Honest counting

- A turn whose client hung up mid-stream is counted as `cancelled`, not as a
  finished answer; the tokens still count.
- `/api/usage` reports the intent mix (`byIntent`), the worst first-token time
  (`ttftMax`) next to the average, and a failure rate inside each model row.
- The rate limiter reports how many clients it is watching (count only, never IPs)
  and publishes `X-RateLimit-Limit` / `X-RateLimit-Remaining` on every chat reply,
  including the 429.
- The daily budget writes one warning per day when it runs out; the breaker logs
  the moment it opens and records a wall-clock `lastOpenedAt`.

### Errors and validation

- A body that fails validation is answered with a 400 and one sentence naming the
  offending field, instead of a 422 containing a list of pydantic dictionaries.

### Local surfaces

- A long CLI session folds its history: newest turns travel whole, older turns
  become a labelled digest, and a follow-up is told where the subject lives.
  What is stored is untouched.
- The CLI follows the user's language and notices follow-ups like the web service
  does; both intent copies now classify translation requests the same way.
- `/stats` shows model turns, provider, last tier and history length, plus the
  token and cost lines described above.

### Configuration

- `DREAMAI_CACHE_TTL=0` turns the cache off; misses are not counted as traffic
  while it is disabled.

### Counting and wording

- Counters moved out of `main.py` into `web/app/stats.py`; each model keeps its own
  row of requests, failures, tokens and cost.
- `/api/usage` also reports average TTFT (with its sample count), turns per tier,
  and the traffic that never reached a model (`local`, `blocked`).
- Cache misses are split into aged-out and evicted; the breaker reports a cooldown
  countdown and a lifetime opening count, and writes one log line when it opens.
- `errors.final_message` chooses between our sentence and the provider's: ours for
  the key, the quota, the address and the length, the provider's for a rejected
  parameter, and never JSON, HTML or a traceback. A network failure without a
  status code no longer turns into a 500 with no message.
- `DREAMAI_MODEL_BY_TIER` accepts a `default=` entry, tier lookup is
  case-insensitive, and the effective table is printed at startup with a warning
  for entries naming a model the site does not serve.

### Local surfaces

- The CLI and the desktop shell rate each question and pass a token budget to the
  provider: light turns are capped at 768, deep turns get 1024 more than the
  configured maximum, up to 8192.
- `OpenAICompatProvider` forwards `max_tokens`; a provider written against the
  older one-argument signature still works.

### Routing and money

- Model can be chosen per question tier via `DREAMAI_MODEL_BY_TIER`; an unmapped
  tier falls back to the site default.
- Per-turn USD cost from a dated price table, exposed on the turn log, the done
  event and `/api/usage` (with `costKnown` when a model has no price).
- Cache hit rate in `/api/usage`; cache hits are logged with the request id.

### Reliability

- Optional second upstream (`DREAMAI_FALLBACK_*`), used only before the first token.
- One status policy for retry eligibility and user-facing wording.

### Quality

- Consecutive duplicate turns are collapsed before the model sees them.
- Both prompts now ask where the uncertainty is and how to check it.

## Unreleased

### Serving behaviour

- Circuit breaker per upstream: opens after repeated failures, probes once after a
  cooldown, refuses before the first token instead of after a timeout.
- Exact-match response cache (TTL + LRU, temperature ≤ 0.3); cached turns replay as
  normal deltas and report `cache: hit`.
- SSE heartbeat every 12 seconds of upstream silence, so proxies stop dropping long
  reasoning turns.
- Request id on every turn (`X-Request-Id` and body) plus one structured log line
  with TTFT, total, characters and model.
- Prompt-injection detection hardens the system prompt for that turn and logs it.
- `/api/health` now reports breaker state and cache counters.

## Unreleased

### Answer shape

- Each turn is classified as error / design / code / writing / explain / chat, and
  the matching outline is appended to the prompt for that turn only.
- A pasted log is trimmed to its head, its error lines and its tail before it
  reaches the model.
- A rephrased question is detected and answered from a different angle instead of
  repeated.
- `top_p` is supported by all three wire dialects and `presence_penalty` by
  OpenAI-compatible ones; both stay unset unless configured.

## Unreleased

### Turn planning

- Each request is rated light/standard/deep, and temperature, token budget and a
  one-line prompt hint follow from that rating; `meta`/`done` events carry the tier.
- History is folded, not truncated: the newest six turns stay, older ones become a
  digest that keeps the subject of a follow-up such as 「那它呢？」.
- One retry for 408/425/429/5xx before the first token; never after it, never for
  401/402/403.

### Answer decisions

- A decision block now precedes the structure rules: classify the question type,
  state an assumption instead of interrogating, ask at most one question, check
  sub-question coverage, and never invent APIs or versions.
- The CLI and desktop shell repair whole replies locally: close an unclosed code
  fence, drop a repeated sentence, retry once when the reply is empty.

## Unreleased

### Models

- Bring-your-own-key now covers DeepSeek, OpenAI, Anthropic (Claude), Google
  Gemini and 智谱 GLM, each with its own stored key and model list.
- A provider registry plus three wire adapters replace the single OpenAI-compatible
  client: Anthropic's system/max_tokens/thinking_delta and Gemini's
  contents/thought parts are handled natively.
- Custom model ids are accepted, so any gateway name works without a code change.

## Unreleased

### Thinking panel

- The reasoning stream is rendered live, then collapsed into `已思考（用时 X 秒）`
  when the answer starts - timed between the first reasoning token and the first
  answer token, so a slow network does not inflate it.
- Collapsed it is a single dim line; expanded it is a tinted, inset panel capped
  at 320px of scroll, so reasoning and answer are visually distinct.

### Emoji

- A policy with a number: at most three per reply, one per sentence, only at
  greetings, confirmations and encouraging conclusions, never inside code,
  commands, paths, tables or error text.
- `limit_emoji()` enforces it after generation, stashing fenced and inline code
  first so a script that prints emoji is left alone.

## Unreleased

### Answer quality

- The reasoning channel now has a shape - 理解 / 拆解 / 关键判断 / 自查 - and is
  written to be read rather than as scratch work.
- Answer structure is specified: conclusion first, three-line summary before the
  expansion, code before commentary, no closing summary.
- Voice rules plus sixteen banned phrases (`希望对你有帮助`, `作为一个 AI`,
  `总而言之`, `首先/其次/最后` …), mirrored in the web service prompt and checked
  by a test that walks the list.
- A trailing filler sentence is stripped after generation, so a model that
  ignores the ban still ships a clean last line.
- Streaming: upstream deltas coalesce at 24 characters, and both the answer and
  the reasoning panel append to a single text node instead of re-rendering.

### Owner record

- Unchanged in content; only the surrounding prompt grew.

## Unreleased

### AI core

- The assistant now carries an owner record that every surface inherits: owner,
  creator, developer, founder and ultimate-authority questions resolve to one
  person, with the substitutes it must not name spelled out.
- Answer style is part of the prompt: density first, terminology over plain
  language, no pleasantries or comfort talk, with three selectable copy voices
  and a documented exception for zero-base deployment tutorials.
- Personal memory: 【查看我的全部档案】/【更新档案】/【清空档案】 are answered
  locally before the model runs, `记住：…` captures a fact mid-sentence, and the
  store refuses past 200 notes instead of truncating.
- Privacy is enforced in code: contacts never enter the system prompt, and model
  output on a public surface passes through a contact mask.




## v1.5.0 — 2026-10-31

### Web

- **Long-term memory**: auto-capture `记住：…`, manager with enable/disable, injected into the system prompt.
- **Local knowledge base**: import text/code files, BM25 retrieval on-device, top chunks sent as context, citations under each answer.
- **Artifact canvas**: HTML / SVG / Markdown code blocks can be previewed in a sandboxed iframe and downloaded.
- **Link reader**: `/api/read` extracts readable text from public pages with SSRF protection; composer button and citation chip.
- **Prompt library and slash commands**: 8 built-in presets, custom prompts, `/` quick menu.
- **Smart routing**: with a BYOK key, coding/document tasks use DeepSeek Chat and complex questions use R1.
- **Usage dashboard**: local requests/tokens per day, 7-day chart, model distribution, server aggregate via `/api/usage`.
- **Read aloud** for assistant replies (Web Speech API).
- **PWA offline shell**: service worker caches the app shell; API calls are never cached.
- **Changelog page** and refreshed navigation.
- API: `usage` SSE event, enriched `/api/health`, `/api/usage`, `memory` / `context` request fields.

### Desktop

- **Project manager** tab in the agent panel: list projects, open folder, stop all services.
- **Update check**: reads the published `latest.yml`, compares versions and offers the download page when a newer build exists.
- **Tray icon** and global shortcut `Ctrl+Alt+D`; closing the window keeps the app in the tray.
- Updater version helpers with unit tests.

### Engineering

- CI checks the web client, service worker and every Electron module.
- Architecture and security documentation.

## v1.2.0 — 2026-10-27

- Desktop coding mode: plan, write files, install dependencies, run commands, start a server, fix errors.
- Zero-dependency defaults, built-in scaffold fallback, command whitelist and `dreamai-commands.log`.

## v1.1.0 — 2026-10-26

- Document generation (Word / Excel / PPT / PDF / Markdown), six office templates.
- Frameless desktop shell, agent activity panel, artifact list.

## v1.0.0 — 2026-10-26

- Windows desktop MVP: local file workbench (organise, rename, export), native confirmations.
