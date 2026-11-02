# 0003 — Owner identity, personal memory, and privacy boundaries

- **Status:** Accepted
- **Date:** 2026-11-02

## Context

`DEFAULT_SYSTEM_PROMPT` was a three-sentence English string: it named Li Guijiang
as the creator and told the model to answer concisely. Everything else — the
owner's profile, writing style, interests, privacy rules, and the commands the
owner expects (`【查看我的全部档案】` and friends) — lived only in chat history,
so it evaporated between sessions.

Two questions had to be answered before writing anything:

1. where the owner's facts live, so both the CLI and the web service see the same
   truth without duplicating strings;
2. how those facts are kept from leaking, given that the web surface is public
   and the system prompt is the one place a model will happily quote back.

## Decision 1 — One identity module, rendered into the prompt

`dream_ai/identity.py` holds the owner record as data (`OWNER`), the style rules,
interests, current situation, and the privacy clause. Rendering happens through
three functions:

| Function | Used by | Content |
|---|---|---|
| `render_identity_block()` | `DEFAULT_SYSTEM_PROMPT` | name, roles, priority rule, answer style |
| `render_profile_block()` | the 档案 command, and memory context | school, contacts, interests, situation |
| `privacy_clause()` | `DEFAULT_SYSTEM_PROMPT` | what may never be disclosed, and how to refuse |

`DEFAULT_SYSTEM_PROMPT` is composed from the original English base plus these
blocks at import time, so `settings.system_prompt` — and therefore the CLI, the
desktop shell, and the FastAPI service — all inherit the same identity without
any of them being edited.

## Decision 2 — Facts the owner adds persist as preferences

`PreferenceMemory` already persists a de-duplicated list to
`<data_dir>/preferences.json` and is already appended to the system prompt on
every turn. Owner-added facts therefore go through the same store instead of a
second one:

- `【更新档案】<text>` appends a fact (de-duplicated, whitespace-normalised);
- `【查看我的全部档案】` returns the rendered block plus the appended facts;
- `【清空档案】` clears the appended facts but never the built-in record, so the
  identity cannot be erased by a command from a chat session.

A cap of 200 facts keeps the prompt bounded; the store refuses beyond that with a
clear message rather than silently truncating.

## Decision 3 — Privacy is enforced in code, not only in the prompt

A prompt instruction is a request; a public surface needs a guarantee. Contact
details are rendered into the prompt because the owner needs them available, but
two additional defences sit around it:

1. `mask_contacts(text)` replaces every known phone, QQ number, and address with
   `〔已隐藏〕`;
2. `DreamAIAgent.public_surface` defaults to `True` for the web process and
   `False` for the CLI/desktop; when it is true, model output passes through the
   mask before it is shown.

The refusal wording is fixed in `privacy_clause()` so the answer is identical
every time: state who the owner is, decline the contact details, offer nothing
further.

## Decision 4 — Commands are recognised before the model runs

`parse_owner_command()` matches the three bracketed commands exactly. The agent
handles them locally and never forwards them to the provider: a command that
depends on the model can fail, be paraphrased, or be refused, and "clear my
profile" must not depend on a completion.

## Consequences

- The identity is one edit away (`identity.py`), not scattered across prompts.
- The web surface keeps working unchanged; it simply receives a richer system
  prompt.
- A public session can still read the *fact* that Li Guijiang is the creator —
  that is intended — but cannot extract the phone number, the QQ account, or the
  email addresses.
- `【清空档案】` cannot remove the built-in identity, only what was added; the owner
  can change the built-in record only by editing the source, which is the point of
  "others have no right to alter the underlying settings".
