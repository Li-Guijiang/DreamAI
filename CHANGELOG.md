# Changelog

## Unreleased

### Metadata and version consistency

- Fixed three pages (`changelog.html`, `download.html`, `offline.html`) that
  were missing Open Graph tags and the apple-touch-icon; `offline.html` also
  gained a theme colour.
- Fixed a real pre-cache drift: `sw.js` cached `app.css?v=2.0.8` and
  `app.js?v=2.1.0` while the pages served `2.1.0` and `2.2.2`. Offline visitors
  would have received stale assets. The worker cache was bumped to `v1.5.7`.
- Added `web/tools/check_meta.py` (head metadata, Open Graph, icons, with a
  `noindex` exemption) and `web/tools/check_versions.py` (server, worker,
  installer, desktop package and changelog relationships), both in CI.
- Extended `check_site.py` with `serviceWorkerPins` to catch stale pins in the
  worker pre-cache list.
- Added `docs/VERSIONS.md` explaining which versions may differ and which
  relationships must hold.

### Configuration contracts

- Added `docs/CONFIGURATION.md`: all 44 server environment variables with
  defaults, ranges and their purpose. Client, desktop and owner variables are
  explicitly listed as out of scope.
- Added `web/tools/check_env_docs.py` and `web/tools/check_docs_index.py` to CI.
  They fail when a new setting is undocumented or a new ADR/document is not
  indexed.
- Values clamped at load time are now reported as field names in
  `/api/health.configClamped`. No values are published, and the list never
  reaches `/api/config`.
- Added a security contract test for `/api/config`: keys, upstream URLs,
  snapshot paths, system prompts and fallback credentials must never appear
  in the browser-facing payload.

### Cache and snapshot integrity

- `ResponseCache.put()` now prunes expired entries before inserting, reports
  `cache.pruned` and `cache.liveItems`, and includes `top_p` and
  `presence_penalty` in the answer key so a sampling change cannot replay an
  old answer. `DREAMAI_CACHE_TTL_JITTER` (default 0, max 0.5) can spread
  expirations of answers written in the same burst.
- Snapshot files carry a SHA-256 checksum of their counters. Pre-checksum files
  remain readable; a mismatch is reported as `tampered`. Files over 8 MiB and
  non-finite counters are rejected.
- Snapshot load status, last successful save and cumulative write failures are
  published as `usageState` on `/api/usage`. A periodic flush
  (`DREAMAI_USAGE_SAVE_INTERVAL`, default 60s, 0 = shutdown only) limits how
  much history a crash can lose.

### Delivery consistency gates

- Fixed a real asset drift: `download.css` was pinned at `?v=1.0.0` on
  `changelog.html` and `offline.html` but `?v=2.0.3` on `download.html`.
  All three now use `2.0.3`; `offline.html` also gained a meta description.
- Added `web/tools/check_assets.py`: finds missing local CSS/JS, detects
  version conflicts across pages, warns on unversioned assets and supports
  `--strict` and `--json`.
- Added `web/tools/check_site.py`: reuses the asset checks and adds page
  links, anchors, duplicate ids, `target="_blank"` safety, page metadata,
  CSS `url()` targets, service-worker cache age and download-manifest fields.
- Both tools run in CI before pytest. `docs/RELEASE.md` records the full
  pre-publication procedure and the meaning of the three version numbers.

### Request lifecycle observability

- `DREAMAI_HEARTBEAT_SECONDS` (default 12, clamped to 1..120) replaces the
  hard-coded SSE heartbeat timeout. Values over 60 produce `heartbeat_long`.
- `DREAMAI_ADMISSION_TIMEOUT` (default 10s, `0` = wait indefinitely) bounds
  the concurrency-slot wait. A timeout yields an `error` frame with
  `code=concurrency_limit` and `retryable=true`, never a `done`.
- `/api/usage` gains `admissionWaitAvg`, `admissionWaitSamples`,
  `admissionWaitMax`, `admissionTimeouts`, `retries`, `retriesByStatus` and
  `fallbacks`. Admission timeouts count as `blocked`; retries and fallbacks are
  extra upstream calls and do not change `requests`.
- `stream_with_retry()` and `stream_with_fallback()` take optional
  `on_retry` / `on_fallback` hooks, wired to the counters by the chat route.
  Existing callers are unaffected.
- Startup checks reject impossible configured model ids (`model_id_invalid`)
  and a sub-second admission timeout (`admission_timeout_short`).

### Bounded counters and early configuration checks

- `DREAMAI_MAX_TRACKED_MODELS` (default 64, clamped to 2..512) bounds the
  per-model table. Custom ids beyond the capacity are folded into
  `byModel.other` with their counts, tokens and cost preserved.
- Fixed a snapshot-import bug: several models merged into the overflow bucket
  used to overwrite one another, leaving only the last one's numbers. Later
  entries now add to the bucket.
- Startup checks now report `base_url_invalid` (bad scheme, missing host,
  whitespace, embedded credentials, query or fragment across the three base
  URLs and two key URLs), `system_prompt_long` (over 8000 characters) and
  `tracked_models_low`. URL findings quote the variable name and reason, never
  the value, so a misplaced password cannot reach a log or `/api/health`.
- `tests/test_stats_invariants.py` asserts that totals reconcile with their
  breakdowns before and after a snapshot round trip and after compaction.
- `docs/API.md` records `byModel.other` and the new finding codes.

### Back-pressure, memory and log privacy

- The SSE queue is now bounded by `DREAMAI_STREAM_QUEUE_SIZE` (default 64,
  clamped to 8..512). A slow reader back-pressures the pump instead of growing
  an unbounded queue; the 12-second heartbeat is unchanged.
- `ResponseCache` enforces a UTF-8 byte ceiling (`DREAMAI_CACHE_MAX_BYTES`,
  default 4 MiB, 0 = off, max 64 MiB) alongside the item count. Answers larger
  than the whole budget are not stored, and byte-driven evictions are counted
  separately. Stats gain `maxBytes`, `byteEvictions` and `byteFull`; startup
  checks warn on a budget under 64 KiB.
- Failed-turn, circuit-open and unexpected-error logs now record the client's
  network prefix (`203.0.x.x`, `2001:db8::`) instead of the full address. Rate
  limiting still keys on the full IP.
- `/api/health` and `/api/usage` send `Cache-Control: no-store`. `/api/chat`
  sends `no-store, no-transform` so a proxy cannot rewrite a streamed body;
  the previous middleware silently dropped `no-transform`.
- `docs/API.md` records the new cache fields and the corrected header.

### Quota continuity and input boundaries

- **Fixed:** the daily free quota was guarded by `upstream.kind == "free"`, but
  `kind` is the wire protocol (`openai` / `anthropic` / `google`) while the free
  provider's `id` is `"free"`. The limit never applied. It now checks
  `upstream.provider.id`, with end-to-end tests proving consumption and the 429.
- **Fixed:** a restart reset the daily allowance even when usage counters were
  restored from a snapshot. The snapshot now carries `daily.date` and
  `daily.count`; only today's value is restored, and a hand-edited count is
  clipped to `DREAMAI_DAILY_LIMIT`.
- `ChatRequest` now bounds `temperature` (0–2), `model`, `provider`, `apiKey`,
  `style`, each `memory` entry, `context` and `maxTokens`, and requires the last
  message to be from the user. Failures keep the existing 400 / `invalid_body`
  shape; `docs/API.md` §2.1 records every bound.
- Request validation failures now carry a short Chinese reason instead of
  Pydantic's English `Value error, …` / `Input should be …` text; custom
  validators raise Chinese sentences and the handler maps common error types.
- `pricing.check_price_tables()` detects non-finite or negative prices,
  malformed pairs, cached prices above the input price, and cached prices with
  no base price. It is published as the `price_table_inconsistent` startup
  finding.
- `docs/API.md` now also documents request limits; contract tests compare its
  field list and error shape with the running code.

### Startup checks, error contract and failure propagation

- **Fixed:** an upstream failure that exhausted its retries stayed inside the
  queue-pump task. The visitor saw a clean `done` with `chars=0` instead of an
  `error` frame, and the circuit breaker never recorded the failure. The pump now
  puts the exception on the queue and the request loop re-raises it.
- SSE `error` events keep `message` and add `code`, `status` and `retryable`.
  `code` is derived from the status (`auth`, `payload`, `rate_limit`, `address`,
  `upstream`, `internal`, or `breaker`), and `retryable` reuses the server's own
  retry policy. An empty sentence falls back to the generic one.
- `validation.check_settings()` reports a partial fallback, an implausible
  breaker cooldown, a daily cap below one rate window, an empty system prompt,
  impossible concurrency, a tiny cache, a short rate window, and three
  informational switch states at startup. Findings are non-blocking,
  secret-free, and published as `/api/health.configChecks`.
- `pricing.invalid_price_overrides()` names the corrections the parsers would
  otherwise skip, so a stale price cannot fail silently.
- Owner conversations no longer enter the shared response cache, and a signed
  cookie with a non-positive expiry is refused.
- `docs/API.md` is now the field contract; `tests/test_api_contract.py` compares
  its event list and error-code table with the running code.

### Recovery and continuity

- Read timeouts are now reported as HTTP 408 and other transport failures as 503,
  so the existing one-retry policy actually applies to them. Failed turns append
  `status=<code>` to the log line, and a statusless failure still fails fast.
- `DREAMAI_UPSTREAM_READ_TIMEOUT` (default 240, clamped to 10..900) is applied as
  a per-request `httpx.Timeout`, leaving the shared connection pool untouched.
- The circuit breaker now stores `half-open` instead of only returning it, and
  releases a half-open probe whose answer never arrived. A cancelled request can
  no longer pin every later request behind an unanswered probe.
- `DREAMAI_USAGE_STATE` optionally persists `/api/usage` counters across a
  restart: a versioned, atomically replaced JSON file containing aggregates only.
  Writes happen on shutdown and every 25 turns; corrupt or invalid snapshots are
  ignored with a log line. `uptime` is never restored. The endpoint reports
  `usagePersisted` so the switch is visible.
- CI no longer runs `desktop/test/update.test.js` twice and now format-checks
  `web/app` as well.

### Finishing a stream

- All three wire formats now report why the model stopped, normalised to
  `length / stop / filter / other`. The stream emits one `finish` event that
  bypasses text coalescing, so the word `length` can never land in an answer.
- The `done` event carries `finish` and `truncated`; the log carries
  `finish=<word>`. The browser's event vocabulary is unchanged.
- A truncated answer is never cached. It used to be replayed verbatim on every
  identical request until the TTL expired.
- `/api/usage` reports `truncated`, `truncationRate`, `truncatedByTier` and
  `byFinish`, so a tight deep-tier cap and a content-filter stop read as two
  different situations.
- The CLI mirrors this: the hosted provider exposes `last_finish`, the session
  ledger counts truncated turns, and `/stats` prints them. A parity test keeps the
  two finish-reason maps identical.
- The response cache reports `bytes` / `avgBytes` (UTF-8, not characters), and the
  byte count survives replacement, expiry, eviction and `clear()`.
- `coalesce(max_chars<=0)` now means "no cap" instead of silently emitting one
  event per token.

### Prompt cache accounting

- Anthropic's system prompt is sent as a cacheable block
  (`cache_control: ephemeral`), so the persona and dossier are actually cached;
  switch it off with `DREAMAI_PROMPT_CACHE=0` if a proxy rejects the field. OpenAI
  caches long prefixes by itself and Gemini needs a separately created cache, so
  the flag is a no-op for both.
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
