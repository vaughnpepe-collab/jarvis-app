# J.A.R.V.I.S. — Desktop App

A JARVIS-style HUD assistant. Python backend + holographic UI, powered by **Claude
through your OpenClaw subscription — no API key required**. Voice in and voice out.

```
jarvis-app/
├─ JARVIS.bat        ← double-click to launch
├─ jarvis_server.py  ← Python backend (the brain bridge + telemetry)
├─ ui.html           ← the HUD interface
└─ requirements.txt  ← optional (psutil for real CPU/RAM)
```

## Auth — Claude with NO API key

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

**Double-click `JARVIS.bat`.** It will:
1. start the Python backend (minimized window),
2. open JARVIS in a frameless app window (Chrome → Edge → default browser).

Or manually:

```
python jarvis_server.py      # then open http://127.0.0.1:8765
```

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
