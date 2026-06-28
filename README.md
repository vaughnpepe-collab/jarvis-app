# J.A.R.V.I.S. — Desktop App

A JARVIS-style HUD assistant. Python backend + holographic UI, powered by your
choice of AI — Claude (API or subscription), OpenAI, Google Gemini, or any
OpenAI-compatible/local model. Voice in and voice out.

## How JARVIS thinks — the "brains"

JARVIS can use several AI providers ("brains"). Configure as many as you like;
it auto-selects the best available one, and you can **switch live** from the HUD
(the **AI** dropdown in the System Telemetry panel) without restarting.

| Brain | Configure with | Notes |
|-------|----------------|-------|
| **Anthropic (Claude API)** | `ANTHROPIC_API_KEY` | Preferred. `JARVIS_ANTHROPIC_MODEL` (default `claude-opus-4-8`). |
| **OpenAI / compatible** | `OPENAI_API_KEY` | `OPENAI_MODEL` (default `gpt-4o-mini`). Point `OPENAI_BASE_URL` at any OpenAI-compatible server — OpenRouter, Groq, Together, or a local Ollama / LM Studio (`http://localhost:11434/v1`). |
| **Google Gemini** | `GEMINI_API_KEY` | `GEMINI_MODEL` (default `gemini-2.0-flash`). |
| **Local model (no key)** | `JARVIS_LOCAL_MODEL` | **No API key.** Any OpenAI-compatible local server — Ollama (default) or LM Studio. Free and private. See below. |
| **Claude subscription (OpenClaw)** | install OpenClaw | **No API key.** Uses your Claude.ai subscription OAuth token. Auto-refreshes. |
| **Demo (offline)** | nothing | Always available — responds in character and tells you how to enable a real brain, so the interface is never dead. |

## The agent team

JARVIS leads a team of specialists, shown in the **Agent Team** panel:

| Agent | Speciality |
|-------|------------|
| **JARVIS** | Executive Orchestrator (default) |
| **FRIDAY** | Research & web |
| **EDITH** | Data & documents |
| **KAREN** | Comms & messaging |
| **VERONICA** | Code & automation |
| **JOCASTA** | Planning & scheduling |

Each agent is the active brain wearing a different persona, with its **own
conversation memory** and its own workspace in the console. To use them:

- **Click an agent** in the Agent Team panel → the console header shows
  "TALKING TO: …" and everything you type goes to that agent.
- Or, without switching, say/type **"ask FRIDAY …"** (or EDITH/KAREN/…) to route
  a single question to that specialist.

Replies are attributed by name in the console, and each agent shows an
**IDLE / WORKING** status while it thinks. (Backend: `GET /agents`, `POST /agent`
with `{agent, text}`.) The agents share whichever brain is active, so once a brain
is connected they all work.

### No API key? Run a model locally (free)

Install [Ollama](https://ollama.com), pull a model, then point JARVIS at it — no
key, nothing leaves your machine:

```
ollama pull llama3.2                 # one-time download
export JARVIS_LOCAL_MODEL=llama3.2   # Windows: set JARVIS_LOCAL_MODEL=llama3.2
./jarvis.sh                          # (or JARVIS.bat)
```

It appears in the **AI** dropdown as “Local model (no key)”. For **LM Studio**
instead, start its local server and add `JARVIS_LOCAL_URL=http://localhost:1234/v1`.
The other keyless route is the **Claude subscription** brain (install OpenClaw).

Set whichever you have, e.g. on macOS/Linux:
```
export ANTHROPIC_API_KEY=sk-ant-...     # Claude
export OPENAI_API_KEY=sk-...            # OpenAI / compatible
export GEMINI_API_KEY=...               # Gemini
```
(Windows `cmd`: `set ANTHROPIC_API_KEY=sk-ant-...`)

**Auto-selection order** is Anthropic → OpenAI → Gemini → Local → OpenClaw → Demo.
Pin a default with `JARVIS_BRAIN` (e.g. `JARVIS_BRAIN=local`), or pick one live from the
HUD **AI** dropdown. The active brain is shown in the HUD (the **Brain** readout:
`ONLINE` for a real brain, `DEMO` for demo) and in the backend startup log.

### See which brain actually works

A configured key isn't proof the brain works (it can be invalid, the model name
wrong, or the network down). Click **TEST** next to the AI dropdown — JARVIS pings
every configured brain in parallel and reports which ones genuinely connect and
reply, with latency: e.g. `OpenAI ✓ 420ms | Gemini ✗ key not valid | Demo ✓`.
Working brains are tagged with a ✓ in the dropdown. (Backend: `POST /brains/test`;
probe timeout via `JARVIS_PROBE_TIMEOUT`, default 20s. Each probe sends one tiny
request, so it uses a negligible amount of quota.)

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

| Variable                | Default                  | Purpose                                   |
|-------------------------|--------------------------|-------------------------------------------|
| `ANTHROPIC_API_KEY`     | (unset)                  | Enables the Anthropic (Claude API) brain  |
| `JARVIS_ANTHROPIC_MODEL`| `claude-opus-4-8`        | Model for the Anthropic brain             |
| `OPENAI_API_KEY`        | (unset)                  | Enables the OpenAI / compatible brain     |
| `OPENAI_MODEL`          | `gpt-4o-mini`            | Model for the OpenAI brain                |
| `OPENAI_BASE_URL`       | `https://api.openai.com/v1` | Point at any OpenAI-compatible server  |
| `GEMINI_API_KEY`        | (unset)                  | Enables the Google Gemini brain           |
| `GEMINI_MODEL`          | `gemini-2.0-flash`       | Model for the Gemini brain                |
| `JARVIS_LOCAL_MODEL`    | (unset)                  | Enables the keyless Local brain (name of a pulled model, e.g. `llama3.2`) |
| `JARVIS_LOCAL_URL`      | `http://localhost:11434/v1` | Local server URL (Ollama default; LM Studio = `:1234/v1`) |
| `JARVIS_LOCAL_API_KEY`  | (unset)                  | Only if your local server requires a token (usually not) |
| `JARVIS_BRAIN`          | (auto)                   | Pin a default brain (`anthropic`/`openai`/`gemini`/`openclaw`) |
| `JARVIS_MAX_TOKENS`     | `1024`                   | Max reply length for the API brains       |
| `JARVIS_PROBE_TIMEOUT`  | `20`                     | Per-brain timeout (s) for the TEST button  |
| `JARVIS_HOST`           | `127.0.0.1`              | Bind address                              |
| `JARVIS_PORT`           | `8765`                   | Bind port                                 |
| `JARVIS_MODELS`         | `claude-cli/...,anthropic/...` | OpenClaw models, tried in order     |
| `JARVIS_TIMEOUT`        | `240`                    | Seconds to wait for a model reply         |
| `JARVIS_OPEN`           | (unset)                  | `1` to auto-open the window (same as `--open`) |
| `JARVIS_LOG_FILE`       | `jarvis.log` (next to the script) | Log file path                    |
| `JARVIS_LOG_LEVEL`      | `INFO`                   | `DEBUG`/`INFO`/`WARNING`/`ERROR`          |

API keys are read from the environment only — never hardcoded and never written
to the log. Logs go to both the console and a rotating log file (1 MB × 3
backups); no secrets are written to the log.

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
- **Brain / model**: see *How JARVIS thinks* above. With an API key, set the model
  via `JARVIS_ANTHROPIC_MODEL`; on the OpenClaw path, set `JARVIS_MODELS`.
- **Conversation memory** is kept for the session in the backend (last ~12 turns).
- If JARVIS says his "link to Claude has lapsed," re-run the auth login command above.
- On the OpenClaw path this uses *your* Claude subscription via the `claude-cli`
  provider; on the API path it uses your `ANTHROPIC_API_KEY`. Either way, usage
  counts against that account.
