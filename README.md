# J.A.R.V.I.S. — Desktop App

A JARVIS-style HUD assistant. Python backend + holographic UI, powered by **Claude
through your OpenClaw subscription — no API key required**. Voice in and voice out.

```
jarvis-app/
├─ JARVIS.bat            ← Windows: double-click to launch
├─ jarvis.sh             ← macOS/Linux: ./jarvis.sh to launch
├─ jarvis_server.py      ← Python backend (brain bridge, telemetry, window-opener)
├─ ui.html               ← the HUD interface
├─ requirements.txt      ← optional (psutil for real CPU/RAM)
├─ requirements-dev.txt  ← optional (pytest; tests also run on the stdlib alone)
└─ tests/                ← unit tests for the backend

JARVIS talks to Claude through OpenClaw's `claude-cli` provider using your
**Claude.ai subscription OAuth token** (no API key). The backend **auto-refreshes
that token** when it expires, so normally you never touch this.

If the subscription login is ever fully lost, re-link it once in a terminal:

```
openclaw.cmd infer model auth login --provider anthropic
```
(choose the **Claude CLI / subscription** option, not API key).

Notes for Windows PowerShell:
- Use `openclaw.cmd ...` (the `.ps1` form is blocked by the script-execution policy),
  or run once: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`.
- The backend invokes OpenClaw via `node openclaw.mjs` directly — the `.cmd` shim
  mangles multi-line prompts, so don't change that.

## Run

**Windows:** double-click `JARVIS.bat`.
**macOS / Linux:** run `./jarvis.sh` (`chmod +x jarvis.sh` the first time).

Either launcher will:
1. start the Python backend,
2. open JARVIS in a frameless app window (Chrome → Edge → Chromium → default browser).

The window-opening logic lives in `jarvis_server.py` (`--open`), so every platform
shares one implementation.

Or run the backend directly:

```
python jarvis_server.py            # backend only — open http://127.0.0.1:8765 yourself
python jarvis_server.py --open     # backend + auto-open the HUD window
python jarvis_server.py --no-open  # never open a browser
```

It shuts down cleanly on Ctrl-C or SIGTERM. If the port is already taken, it says
so plainly instead of dumping a traceback.

## Configuration (environment variables)

| Variable          | Default                  | Purpose                                   |
|-------------------|--------------------------|-------------------------------------------|
| `JARVIS_HOST`     | `127.0.0.1`              | Bind address                              |
| `JARVIS_PORT`     | `8765`                   | Bind port                                 |
| `JARVIS_MODELS`   | `claude-cli/...,anthropic/...` | Comma-separated models, tried in order |
| `JARVIS_TIMEOUT`  | `240`                    | Seconds to wait for a model reply         |
| `JARVIS_OPEN`     | (unset)                  | `1` to auto-open the window (same as `--open`) |
| `JARVIS_LOG_FILE` | `jarvis.log` (next to the script) | Log file path                    |
| `JARVIS_LOG_LEVEL`| `INFO`                   | `DEBUG`/`INFO`/`WARNING`/`ERROR`          |

Logs go to both the console and a rotating log file (1 MB × 3 backups). No
secrets are written to the log.

## Tests

The suite uses only the standard library — no install required:

```
python -m unittest discover -s tests
```

Or, if you prefer pytest (`pip install -r requirements-dev.txt`):

```
python -m pytest tests
```

The OpenClaw/model boundary is mocked, so tests are fast and never make a real
network or subprocess call.

## Using it

- **Type** in the console and press Enter — replies come from real Claude, in character.
- **🎙 Mic** — click, then say **"Jarvis, …"** followed by your request (wake-word gated).
- **🔊 Speaker** — mute / restore JARVIS's spoken replies.
- Live telemetry, arc-reactor core (pulses faster while thinking), activity log.

## Notes & limits

- **Voice needs Chrome or Edge** (Web Speech API). The mic also needs microphone
  permission and an internet connection for recognition.
- **Telemetry**: install `psutil` (`pip install psutil`) for real CPU/RAM; otherwise
  estimated values are shown.
- **Model**: defaults to `claude-cli/claude-opus-4-8`. Override with an env var:
  `set JARVIS_MODEL=claude-cli/claude-sonnet-4-6` before launching.
- **Conversation memory** is kept for the session in the backend (last ~12 turns).
- If JARVIS says his "link to Claude has lapsed," re-run the auth login command above.
- This uses *your* Claude subscription via OpenClaw's `claude-cli` provider; usage
  counts against your normal plan.
