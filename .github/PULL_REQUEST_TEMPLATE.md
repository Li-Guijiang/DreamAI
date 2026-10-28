## What this changes

<!-- What does the PR do, and why is it needed? Link the issue with "Closes #123". -->

Closes #

## Type

- [ ] Feature (feat)
- [ ] Bug fix (fix)
- [ ] Documentation (docs)
- [ ] Refactor or tooling (refactor / chore)
- [ ] Formatting only (style)

## Affected areas

<!-- Tick what applies, so reviewers know what to verify. -->

- [ ] CLI package `dream_ai/`
- [ ] Web service `web/app/`
- [ ] Web front end `web/web/`
- [ ] Desktop app `desktop/`
- [ ] Documentation `docs/`
- [ ] CI / packaging / dependencies

## Verification

<!-- Paste the commands you ran and their result. "Tested locally" alone is not enough. -->

```bash
pytest
ruff check dream_ai tests examples web/app web/tools
ruff format --check dream_ai tests examples
```

Manual steps, screenshots, or recordings:

## Checklist

- [ ] Read the [contributing guide](../docs/CONTRIBUTING.md)
- [ ] New or changed behaviour has tests
- [ ] User-facing changes update the documentation and `CHANGELOG.md`
- [ ] Configuration changes keep `.env.example` and the docs in sync
- [ ] No API keys, passwords, or server addresses are included
- [ ] Commits are split by concern and use the `type: summary` format
