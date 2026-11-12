# Plans & Pricing — Vision Document

<p align="center"><img src="https://cdn.jsdelivr.net/gh/Li-Guijiang/DreamAI@main/assets/brand/banner-docs.webp" alt="Animated Dream AI documentation banner" width="720"></p>

<sub>[Back to the documentation index](./README.md)</sub>

> ⚠️ **These plans are a long-term vision only. Nothing is sold or available
> today.** Dream AI is free and open-source under the MIT License. This
> document records the intended direction so the community can give feedback.

## Principles

1. **Open core, forever.** The open-source code stays free and permissively
   licensed. Anyone can self-host Dream AI for free.
2. **Privacy by default.** User data belongs to the user. Self-hosted and local
   modes keep data on the user's machine.
3. **Optional convenience, not lock-in.** Paid plans add hosted convenience
   and support; they never remove access to the open-source core.
4. **Honest pricing.** Prices are published openly when plans launch, with no
   hidden fees or surprise lock-in.
5. **Sustainable development.** Optional paid plans help fund maintenance,
   infrastructure, and ongoing development.

## Plan Overview

| Capability | **Free** | **Pro** | **Team** | **Enterprise** |
|---|:---:|:---:|:---:|:---:|
| Open-source code & self-hosting | ✅ | ✅ | ✅ | ✅ |
| Local CLI / offline mode | ✅ | ✅ | ✅ | ✅ |
| Conversation history | Session only | Persistent | Persistent | Persistent |
| Long-term memory | — | ✅ | ✅ | ✅ |
| Built-in tools (search, files, calculator) | Basic | ✅ | ✅ | ✅ |
| Priority hosted model access | — | ✅ | ✅ | ✅ |
| Higher usage limits | — | ✅ | ✅ | Custom |
| Shared team workspaces | — | — | ✅ | ✅ |
| Shared knowledge base | — | — | ✅ | ✅ |
| Admin & member management | — | — | ✅ | ✅ |
| Priority support | — | ✅ | ✅ | Dedicated |
| SSO / advanced security | — | — | — | ✅ |
| SLA and custom deployment | — | — | — | ✅ |

## Plan Definitions

### Free — For everyone
- Full open-source code and self-hosting
- Local CLI and offline demo mode
- Session-only conversation history
- Basic built-in tools
- Community support

### Pro — For individuals who want more
- Everything in Free
- Persistent long-term memory
- Full tool suite
- Priority hosted model access and higher limits
- Priority support
- Personal use

### Team — For groups and classrooms
- Everything in Pro
- Shared team workspaces
- Shared knowledge base
- Member and workspace administration
- Team-level usage dashboard

### Enterprise — For organizations
- Everything in Team
- Custom usage limits and deployment options
- SSO and advanced security controls
- Dedicated support and service-level agreement
- Private/on-premise deployment options

## What Is Not Included

- Selling the open-source code itself under a proprietary license.
- Removing features from the open-source repository behind a paywall.
- Collecting or selling user conversation data.

## Status

- **Current state:** `v0.4` development; persistent memory, the tool layer, and
  the autonomous planning loop are in place; no hosted service exists.
- **Next step toward plans:** stabilize the core toward `v1.0` before any hosted
  plan is considered.
- **Feedback:** Open an issue in the repository to suggest plan features or
  fair pricing.

---

## Appendix — what a token actually costs

The plans above are about this project. The numbers below are about the model
vendors, and they are the ones `/api/usage` and `/stats` report. They are kept in
`web/app/pricing.py` and `dream_ai/pricing.py`, and a parity test compares the two.

Snapshot: 2026-11, USD per 1M tokens, list prices. Vendors change these without
notice, which is why an unknown model returns "unknown" rather than a guess.

| Model | Input | Cached input | Output |
|---|---:|---:|---:|
| `glm-4-flash` | 0.00 | — | 0.00 |
| `glm-4-plus` | 0.70 | — | 0.70 |
| `deepseek-chat` | 0.27 | 0.07 | 1.10 |
| `deepseek-reasoner` | 0.55 | 0.14 | 2.19 |
| `gpt-4o-mini` | 0.15 | 0.075 | 0.60 |
| `gpt-4o` | 2.50 | 1.25 | 10.00 |
| `claude-3-5-haiku-latest` | 0.80 | 0.08 | 4.00 |
| `claude-3-5-sonnet-latest` | 3.00 | 0.30 | 15.00 |
| `gemini-2.0-flash` | 0.10 | 0.025 | 0.40 |
| `gemini-1.5-pro` | 1.25 | 0.3125 | 5.00 |

Three things this table is careful about:

1. **Cached input is not a fixed discount.** It is a tenth at Anthropic, a quarter
   at Google, half at OpenAI and about a quarter at DeepSeek, so the table keeps a
   separate figure per model instead of one multiplier.
2. **Thinking is output.** Gemini reports `thoughtsTokenCount` outside
   `candidatesTokenCount`, and it is billed like any other completion token.
3. **No price means no number.** A model absent from the table leaves
   `costKnown=false`, and the CLI prints "at least $…" instead of a total that
   looks complete.

### Correcting a price without a release

```bash
DREAMAI_PRICE_OVERRIDES='new-model=0.5,1.5;gpt-4o=2.5,10,1.25'
```

- two numbers: input, output;
- three numbers: input, output, cached input;
- entries separated by `;`, values in USD per 1M tokens;
- malformed, negative and non-finite values are skipped rather than applied.

The override is read at startup and logged as `price overrides: …`, so an empty
log line after a restart means the variable did not reach the process.

