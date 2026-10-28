# Security Policy

<sub>[Back to the documentation index](./README.md)</sub>

## Reporting a Vulnerability

If you discover a security vulnerability in Dream AI, please report it
**privately** so it can be fixed before public disclosure:

- Prefer GitHub: open a **Security Advisory** from the repository's
  `Security → Report a vulnerability` page.
- If that is unavailable, open a private issue or contact the maintainer
  directly. Do not post exploit details in a public issue.

## What to Include

- A clear description of the vulnerability and its impact.
- Steps to reproduce, if possible.
- Suggested fix or mitigation, if you have one.

## Scope

In scope: code in this repository, configuration handling, and the agent's
tool execution model.

Out of scope: vulnerabilities in third-party providers, operating system
issues unrelated to this project, or reports that only describe theoretical
risks with no concrete impact.

## Expectations

- Reports are reviewed promptly.
- Credit is given to reporters who wish to be acknowledged after a fix.
- We do not guarantee a fixed response time, but we treat valid reports
  seriously.

## Safe Development Reminders

- Never commit API keys, `.env`, or personal data (see `.gitignore`).
- Tools that touch the filesystem or network are added only behind explicit
  user consent and allowlists (planned in `v0.3`).
