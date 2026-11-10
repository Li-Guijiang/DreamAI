# Architecture Decision Records (ADR)

<p align="center"><img src="https://cdn.jsdelivr.net/gh/Li-Guijiang/DreamAI@main/assets/brand/banner-docs.webp" alt="Animated Dream AI documentation banner" width="720"></p>

<sub>[Back to the documentation index](../README.md)</sub>

This folder stores short, dated records of important architecture decisions.

Each ADR answers: what was decided, why, and what alternatives were rejected.
New decisions should be added as numbered Markdown files, e.g. `0001-pluggable-provider.md`.

| [0002](./0002-version-check-and-install-detection.md) | Version checks, in-app updates, install detection |
| [0003](./0003-owner-identity-and-personal-memory.md) | Owner identity, personal memory, and privacy boundaries |
| [0004](./0004-answer-quality-and-reasoning.md) | Answer quality: reasoning, structure, and a natural voice |
| [0005](./0005-reply-planning-and-resilience.md) | Reply quality: plan the turn, keep the context, survive a bad minute |
| [0006](./0006-answer-shape-and-input-hygiene.md) | Answer shape: classify the question, clean the input, notice repeats |
| [0007](./0007-serving-behaviour.md) | Serving behaviour: fail fast, repeat free, stay connected |
| [0008](./0008-routing-cost-and-failover.md) | Routing, money and the second upstream |
| [0009](./0009-usage-accounting.md) | Counting the service: what each number means |
| [0010](./0010-local-reply-sizing.md) | Local reply sizing: the same question gets the same room |
| [0011](./0011-local-parity.md) | Local parity: fold history, follow language, keep both copies honest |
