# Changelog

All notable changes to Dream AI are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] — 2026-10-24

### Added
- Repository skeleton with `dream_ai`, `tests`, `examples`, and `docs` layout.
- Environment-based `Settings` loaded from `.env`.
- Pluggable `LLMProvider` interface with:
  - OpenAI-compatible hosted provider.
  - Offline local demo provider as fallback.
- In-memory session memory with system prompt and conversation history.
- `DreamAIAgent` composing provider, memory, conversation, and tool registry.
- CLI REPL with `/help`, `/clear`, `/about`, `/quit`.
- Tool registry contract for future tool use.
- Unit and smoke tests.
- Project documentation: README, roadmap, architecture, contributing guide,
  code of conduct, security policy, setup guide, and pricing vision.
- MIT License.
- CI workflow: Ruff lint and pytest across Python 3.11, 3.12, and 3.13.
- Release workflow: on a `v*` tag, build the `sdist` and `wheel`, validate
  metadata, and attach both archives to the GitHub Release.
- Package metadata in `pyproject.toml` for standard sdist and wheel builds.
- `Dockerfile` and `.dockerignore` for a non-root, slim container deployment.
- Container workflow publishing a multi-architecture image to the GitHub
  Container Registry on version tags and manual dispatch.

### Notes
- This is the initial development skeleton (`v0.1`). Real model connectivity
  requires a configured API key; offline demo mode works without one.
- The `dream_ai-0.1.0` `wheel` and `sdist` archives are attached to the
  [v0.1.0 Release](https://github.com/Li-Guijiang/DreamAI/releases/tag/v0.1.0).
