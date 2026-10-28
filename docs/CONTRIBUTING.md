# Contributing to Dream AI

<sub>[Back to the documentation index](./README.md)</sub>

Thank you for helping build Dream AI. Contributions of all kinds are welcome:
code, documentation, bug reports, ideas, and feedback.

## Getting Started

1. Fork the repository and clone your fork.
2. Create a virtual environment and install dev dependencies:

   ```bash
   python -m venv .venv
   # Windows:        .venv\Scripts\activate
   # macOS / Linux:  source .venv/bin/activate
   pip install -r requirements-dev.txt
   ```

3. Copy `.env.example` to `.env` for local testing (leave the API key empty to
   use offline demo mode).

## Development Workflow

- Create a short, descriptive branch from `main`, e.g. `feat/persistent-memory`.
- Keep changes focused: one feature or fix per pull request.
- Add or update tests for behavior you change.
- Run the checks before opening a PR:

  ```bash
  pytest
  ruff check dream_ai tests examples web/app web/tools
  ruff format --check dream_ai tests examples
  ```

  `web/tools/archive/` is excluded from lint and format checks: those are
  one-off operational scripts kept for traceability (see `web/tools/README.md`).

## Commit Message Style

Use short imperative messages, prefixed by a type:

- `feat: add persistent session memory`
- `fix: handle empty API key gracefully`
- `docs: update roadmap for v0.2`
- `test: cover tool registry lookup errors`
- `refactor: split provider factory from CLI`

## Code Style

- Python 3.11+ type hints.
- Follow the existing module layout under `dream_ai/`.
- Keep the agent core free of provider-specific details.
- Public interfaces should be documented with a short docstring.

## Pull Request Checklist

- [ ] `pytest` passes locally.
- [ ] `ruff check` reports no errors on the paths CI checks.
- [ ] `ruff format --check dream_ai tests examples` reports no changes.
- [ ] New behavior has tests.
- [ ] Documentation is updated for user-facing changes.
- [ ] No secrets, API keys, or personal data are committed.

## Reporting Issues

- Use the issue templates when available.
- Include steps to reproduce, expected behavior, and actual behavior.
- Attach logs or screenshots where helpful.

## Code of Conduct

By participating, you agree to uphold our [Code of Conduct](./CODE_OF_CONDUCT.md).
