# Getting help

<p align="center"><img src="https://github.com/user-attachments/assets/9ec27a73-47d4-489f-b71e-106a84e1b70c" alt="Animated Dream AI documentation banner" width="720"></p>

<sub>[Back to the documentation index](./README.md)</sub>

Work through the steps below in order — most problems are resolved by the first two. If you are still stuck, pick a channel in section 4.

<p align="center"><img src="../assets/brand/divider.gif" alt="" width="640"></p>

## 1. Check the documentation first

| Your question | Where to look |
|---|---|
| How do I install and run it? | [SETUP.md](./SETUP.md) for step-by-step setup, [GUIDE.md](./GUIDE.md) for a guided walkthrough |
| How does a command work, and why did it fail? | [GUIDE.md](./GUIDE.md) section 5 (command reference) and section 9 (troubleshooting) |
| What does this setting do, and what is the default? | [.env.example](../.env.example), plus section 6 of [GUIDE.md](./GUIDE.md) |
| How is the code organised? | [ARCHITECTURE.md](./ARCHITECTURE.md) |
| When will a feature land? | [ROADMAP.md](./ROADMAP.md) |
| Web deployment, nginx, systemd | [web/README.md](../web/README.md), [web/deploy/](../web/deploy) |
| Desktop packaging, icons, signing | [desktop/README.md](../desktop/README.md) |

<p align="center"><img src="../assets/brand/divider.gif" alt="" width="640"></p>

## 2. Rule out the environment

```bash
python --version          # 3.11 or newer is required
pip show dream-ai         # confirm which version is installed
python -m dream_ai        # a banner means it starts correctly
```

With no API key Dream AI runs in **offline demo mode**: replies come from a placeholder provider. That is expected behaviour — set `DREAMAI_API_KEY` and restart to reach a real model.

<p align="center"><img src="../assets/brand/divider.gif" alt="" width="640"></p>

## 3. Three checks that resolve most reports

1. Search the repository issues (including closed ones) for the key phrase in your error.
2. Re-run with `DREAMAI_AUTONOMY_VERBOSE=true` to see which phase fails.
3. For tool problems, confirm the tool is registered with `/tools`, then reproduce it alone with `/tool <name> <json>`.

<p align="center"><img src="../assets/brand/divider.gif" alt="" width="640"></p>

## 4. Pick a channel

| Situation | Channel | Expectation |
|---|---|---|
| Reproducible defect | [Open a bug report](https://github.com/Li-Guijiang/DreamAI/issues/new?template=bug_report.yml) | Fill in the form; reports without steps are sent back |
| Feature suggestion | [Open a feature request](https://github.com/Li-Guijiang/DreamAI/issues/new?template=feature_request.yml) | Check the roadmap first to avoid duplicates |
| Security vulnerability | The private channel in [SECURITY.md](./SECURITY.md) | Do not open a public issue |
| Just want to try it | <https://liguijiang.com> | No installation needed |

<p align="center"><img src="../assets/brand/divider.gif" alt="" width="640"></p>

## 5. What to include

1. Operating system and Python / Node version;
2. the exact command you ran;
3. the complete error output (do not truncate the stack trace);
4. what you already tried.

**Never paste API keys, server addresses, or passwords.** When you need to show configuration, replace the values with `***`.

<p align="center"><img src="../assets/brand/footer.gif" alt="" width="720"></p>
