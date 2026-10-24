# Local Setup Guide

A step-by-step guide to run Dream AI on your own machine. Windows steps are
primary; macOS and Linux notes are included where they differ.

## Prerequisites

- **Python 3.11 or newer** installed. Check in a terminal:

  ```bash
  python --version
  ```

- **Git** installed and logged in to GitHub.

## 1. Get the Code

```bash
git clone https://github.com/Li-Guijiang/DreamAI.git
cd DreamAI
```

## 2. Create a Virtual Environment

**Windows (PowerShell):**

```powershell
python -m venv .venv
.venv\Scripts\activate
```

**macOS / Linux:**

```bash
python -m venv .venv
source .venv/bin/activate
```

When activated, your terminal prompt shows `(.venv)`.

## 3. Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

For development (tests and linting):

```bash
pip install -r requirements-dev.txt
```

## 4. Configure the Model

Copy the example environment file:

**Windows:**

```powershell
copy .env.example .env
```

**macOS / Linux:**

```bash
cp .env.example .env
```

Open `.env` and fill in:

- `DREAMAI_API_KEY`: your provider API key.
- `DREAMAI_BASE_URL`: the provider endpoint (defaults to DeepSeek).
- `DREAMAI_MODEL`: the model name.
- `DREAMAI_SYSTEM_PROMPT`: the assistant persona.

> Leave `DREAMAI_API_KEY` empty to run offline demo mode. The agent still
> starts, but replies come from the local placeholder provider, not a real model.

## 5. Run Dream AI

```bash
python -m dream_ai
```

Type a message and press Enter. Commands inside the chat:

| Command | Action |
|---|---|
| `/help` | Show available commands |
| `/clear` | Clear conversation history |
| `/about` | Show provider and session info |
| `/quit` or `/exit` | Exit |

## 6. Run the Example

```bash
python examples/basic_chat.py
```

## 7. Run Tests and Lint

```bash
pytest
ruff check dream_ai tests
```

## Common Issues

### `python` is not recognized
Install Python from python.org, enable "Add Python to PATH" during install,
then reopen the terminal.

### `No module named openai`
Make sure the virtual environment is activated, then reinstall dependencies:

```bash
pip install -r requirements.txt
```

### The agent replies with "[Local demo mode]"
No API key was detected. Fill `DREAMAI_API_KEY` in `.env` and restart.

### Provider authentication error
Verify the API key, `DREAMAI_BASE_URL`, and `DREAMAI_MODEL` match the chosen
provider, and that the key has not expired.

### Port or network blocked
Check your proxy or firewall settings if a hosted endpoint cannot be reached.
