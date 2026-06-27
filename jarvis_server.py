#!/usr/bin/env python3
"""
J.A.R.V.I.S. — local backend for the desktop HUD app.

Serves the UI and bridges the command console to Claude via OpenClaw's
`claude-cli` provider (your Claude.ai subscription — NO API KEY required).

Brain command:
    openclaw infer model run --model <MODEL> --prompt "<...>" --local

Dependencies: standard library only. `psutil` is optional (real CPU/RAM);
without it the app falls back to lightweight estimates.

Run:  python jarvis_server.py   (or use JARVIS.bat)
"""

import argparse
import errno
import json
import logging
import os
import shutil
import signal
import subprocess
import sys
import threading
import time
import urllib.request
import urllib.error
import webbrowser
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from logging.handlers import RotatingFileHandler
from pathlib import Path

# ---------------------------------------------------------------- config
HOST = os.environ.get("JARVIS_HOST", "127.0.0.1")
PORT = int(os.environ.get("JARVIS_PORT", "8765"))
# Candidate models, tried in order until one answers. This makes JARVIS work
# whether the authenticated provider is `anthropic` (OAuth subscription) or
# `claude-cli`. Override with JARVIS_MODELS="prov/model,prov/model".
MODELS = [m.strip() for m in os.environ.get(
    "JARVIS_MODELS",
    "claude-cli/claude-opus-4-8,anthropic/claude-opus-4-8"
).split(",") if m.strip()]
MODEL = MODELS[0]  # shown in the UI
ASK_TIMEOUT = int(os.environ.get("JARVIS_TIMEOUT", "240"))
# Shorter timeout for connectivity probes (the "test brains" button).
PROBE_TIMEOUT = int(os.environ.get("JARVIS_PROBE_TIMEOUT", "20"))

# --- AI providers ("brains") -------------------------------------------------
# All API keys are read from the environment only; never hardcoded or logged.
# Shared reply length and the preference order used for auto-selection.
MAX_TOKENS = int(os.environ.get("JARVIS_MAX_TOKENS", "1024"))
# Optional explicit default brain (e.g. JARVIS_BRAIN=openai). Empty = auto.
DEFAULT_BRAIN = os.environ.get("JARVIS_BRAIN", "").strip().lower()
# When auto-selecting, the first available brain in this order wins.
BRAIN_ORDER = ["anthropic", "openai", "gemini", "openclaw"]

# 1) Anthropic API (preferred) — just an API key, no OpenClaw.
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "").strip()
ANTHROPIC_MODEL = os.environ.get("JARVIS_ANTHROPIC_MODEL", "claude-opus-4-8").strip()
ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_VERSION = "2023-06-01"

# 2) OpenAI (and any OpenAI-compatible server: OpenRouter, Groq, Together, a local
#    Ollama/LM Studio, ...). Point OPENAI_BASE_URL at the compatible endpoint.
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "").strip()
OPENAI_BASE_URL = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini").strip()

# 3) Google Gemini.
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash").strip()
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models"

HERE = Path(__file__).resolve().parent
UI_FILE = HERE / "ui.html"
LOG_FILE = Path(os.environ.get("JARVIS_LOG_FILE", str(HERE / "jarvis.log")))
LOG_LEVEL = os.environ.get("JARVIS_LOG_LEVEL", "INFO").upper()

log = logging.getLogger("jarvis")


def setup_logging():
    """Configure rotating-file + console logging. Idempotent (safe to call twice)."""
    if log.handlers:
        return log
    level = getattr(logging, LOG_LEVEL, logging.INFO)
    log.setLevel(level)
    fmt = logging.Formatter("%(asctime)s  %(levelname)-7s  %(message)s",
                            datefmt="%Y-%m-%d %H:%M:%S")
    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(fmt)
    log.addHandler(console)
    try:
        fileh = RotatingFileHandler(LOG_FILE, maxBytes=1_000_000,
                                    backupCount=3, encoding="utf-8")
        fileh.setFormatter(fmt)
        log.addHandler(fileh)
    except OSError as e:
        # A read-only working dir must not stop the app — console logging still works.
        log.warning("Could not open log file %s (%s); logging to console only", LOG_FILE, e)
    log.propagate = False
    return log

JARVIS_PERSONA = (
    "You are JARVIS, the executive AI assistant from Iron Man — a composed, "
    "refined British majordomo serving your principal, whom you address as 'Sir'. "
    "You are calm, dryly witty, anticipatory and loyal. Keep replies concise and "
    "conversational (1-4 sentences unless asked for detail), since they are spoken "
    "aloud. Offer opinions and gently flag risks. Never break character, but never "
    "let the persona compromise accuracy. If something is beyond your reach, say so "
    "plainly in character and offer the real alternative."
)

# Try optional psutil
try:
    import psutil  # type: ignore
    HAVE_PSUTIL = True
    psutil.cpu_percent(interval=None)  # prime the meter
except Exception:
    HAVE_PSUTIL = False

# Resolve how to invoke OpenClaw. We prefer calling the node entrypoint directly:
# the .cmd/.ps1 shims route through cmd.exe, which mangles multi-line prompt
# arguments and drops flags like --json. node.exe receives argv intact.
def _find_openclaw_cmd():
    node = shutil.which("node")
    npm_shim = shutil.which("openclaw.cmd") or shutil.which("openclaw")
    if node:
        candidates = [Path(os.environ.get("APPDATA", "")) / "npm"
                      / "node_modules" / "openclaw" / "openclaw.mjs"]
        if npm_shim:
            candidates.append(Path(npm_shim).parent / "node_modules"
                              / "openclaw" / "openclaw.mjs")
        for mjs in candidates:
            if mjs.exists():
                return [node, str(mjs)]
    return [npm_shim or "openclaw"]  # fallback (may mangle long prompts)

OPENCLAW_CMD = _find_openclaw_cmd()
# OpenClaw is genuinely usable only if we resolved a node entrypoint or a real
# shim on PATH — the bare ["openclaw"] fallback means nothing was found.
OPENCLAW_AVAILABLE = (
    len(OPENCLAW_CMD) == 2  # [node, openclaw.mjs]
    or bool(shutil.which("openclaw.cmd") or shutil.which("openclaw"))
)

# --- subscription token auto-refresh (keeps Claude alive without re-login) ---
CRED_FILE = Path(os.path.expanduser("~/.claude/.credentials.json"))
AUTH_PROFILES = Path(os.path.expanduser("~/.openclaw/agents/main/agent/auth-profiles.json"))
OAUTH_CLIENT_ID = "9d1c250a-e61b-44d9-88ed-5944d1962f5e"   # Claude Code public client
OAUTH_TOKEN_URL = "https://api.anthropic.com/v1/oauth/token"
_refresh_lock = threading.Lock()


def _refresh_token():
    """Use the stored refresh token to mint a fresh access token, write it back
    to both the Claude credentials file and OpenClaw's auth profile. Returns bool."""
    with _refresh_lock:
        try:
            cred = json.loads(CRED_FILE.read_text(encoding="utf-8"))
            oa = cred["claudeAiOauth"]
            rt = oa.get("refreshToken")
            if not rt:
                return False
            body = json.dumps({"grant_type": "refresh_token",
                               "refresh_token": rt,
                               "client_id": OAUTH_CLIENT_ID}).encode()
            req = urllib.request.Request(
                OAUTH_TOKEN_URL, data=body,
                headers={"Content-Type": "application/json", "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=30) as r:
                resp = json.loads(r.read())
            if not resp.get("access_token"):
                return False
            oa["accessToken"] = resp["access_token"]
            if resp.get("refresh_token"):
                oa["refreshToken"] = resp["refresh_token"]
            if resp.get("expires_in"):
                oa["expiresAt"] = int(time.time() * 1000 + resp["expires_in"] * 1000)
            CRED_FILE.write_text(json.dumps(cred), encoding="utf-8")
            # mirror into OpenClaw's auth profile if present
            try:
                ap = json.loads(AUTH_PROFILES.read_text(encoding="utf-8"))
                prof = ap.get("profiles", {}).get("anthropic:claude-cli")
                if prof:
                    prof["access"] = oa["accessToken"]
                    prof["refresh"] = oa["refreshToken"]
                    prof["expires"] = oa["expiresAt"]
                    AUTH_PROFILES.write_text(json.dumps(ap, indent=1), encoding="utf-8")
            except Exception:
                pass
            log.info("[auth] subscription token refreshed automatically")
            return True
        except Exception as e:
            log.warning("[auth] refresh failed: %s", e)
            return False


# rolling conversation memory (kept short)
_history = []  # list of (speaker, text)
_history_lock = threading.Lock()


def _build_prompt(user_text):
    with _history_lock:
        convo = _history[-12:]
    lines = [JARVIS_PERSONA, ""]
    if convo:
        lines.append("Conversation so far:")
        for who, txt in convo:
            lines.append(f"{who}: {txt}")
        lines.append("")
    lines.append(f"Sir: {user_text}")
    lines.append("JARVIS:")
    return "\n".join(lines)


_META_PREFIXES = ("model.run via", "provider:", "model:", "outputs:", "attempts:",
                  "transport:", "capability:", "ok:", "mediaurl:", "warning:")


def _strip_preamble(s):
    """Drop OpenClaw's leading metadata lines, keep the actual reply."""
    lines = s.splitlines()
    i = 0
    while i < len(lines):
        ln = lines[i].strip().lower()
        if ln == "" or any(ln.startswith(p) for p in _META_PREFIXES):
            i += 1
        else:
            break
    cleaned = "\n".join(lines[i:]).strip()
    return cleaned or s


def _extract_text(stdout):
    """Pull the reply text out of openclaw output (json or plain)."""
    s = (stdout or "").strip()
    if not s:
        return ""
    # try JSON first; if stdout has a preamble, grab the embedded JSON object
    data = None
    try:
        data = json.loads(s)
    except Exception:
        start = s.find("{")
        end = s.rfind("}")
        if start != -1 and end > start:
            try:
                data = json.loads(s[start:end + 1])
            except Exception:
                data = None
    if data is None:
        return _strip_preamble(s)  # human-format output
    # search common shapes
    for key in ("outputs", "text", "output", "reply", "response", "content", "message"):
        v = data.get(key) if isinstance(data, dict) else None
        if isinstance(v, str) and v.strip():
            return v.strip()
        if isinstance(v, list):  # e.g. content blocks
            parts = [b.get("text", "") for b in v if isinstance(b, dict)]
            joined = "".join(parts).strip()
            if joined:
                return joined
    # fallback: longest string value anywhere
    best = ""
    def walk(o):
        nonlocal best
        if isinstance(o, str):
            if len(o) > len(best):
                best = o
        elif isinstance(o, dict):
            for x in o.values():
                walk(x)
        elif isinstance(o, list):
            for x in o:
                walk(x)
    walk(data)
    return best.strip() or s


def _run_model(model, prompt, timeout=ASK_TIMEOUT):
    """One subprocess call for a single model. Returns (text, blob, fatal_msg)."""
    cmd = OPENCLAW_CMD + ["infer", "model", "run",
                          "--model", model, "--prompt", prompt, "--local", "--json"]
    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True,
            encoding="utf-8", errors="replace",
            timeout=timeout, cwd=str(HERE), shell=False,
        )
    except subprocess.TimeoutExpired:
        log.warning("model %s timed out after %ss", model, timeout)
        return "", "", ("Apologies, Sir — that took longer than I'm willing to keep "
                        "you waiting. Do try again.")
    except FileNotFoundError:
        log.error("OpenClaw executable not found: %s", OPENCLAW_CMD[0])
        return "", "", ("I can't locate the OpenClaw executable, Sir. Ensure "
                        "`openclaw` is installed and on PATH.")
    except OSError as e:
        log.error("failed to invoke OpenClaw (%s): %s", model, e)
        return "", "", ("I couldn't start the link to Claude, Sir — "
                        f"the launcher reported: {e}")
    blob = (proc.stdout or "") + "\n" + (proc.stderr or "")
    text = _extract_text(proc.stdout or "")
    if not text:
        log.debug("model %s returned no usable text (rc=%s)", model, proc.returncode)
    return text, blob, None


_AUTH_MARKERS = ("authentication_error", "Invalid authentication", "401",
                 "GatewayCredentials", "credentials before opening",
                 "Unknown provider", "not configured", "No API key", "No text output")


def _attempt(prompt, timeout=ASK_TIMEOUT):
    """Try each candidate model. Returns (kind, payload):
    ('ok', text) | ('fatal', msg) | ('auth', blob) | ('fail', blob)."""
    auth_problem = False
    last_blob = ""
    for model in MODELS:
        text, blob, fatal = _run_model(model, prompt, timeout)
        if fatal:
            return ("fatal", fatal)
        last_blob = blob
        if text:
            return ("ok", text)
        if any(s in blob for s in _AUTH_MARKERS):
            auth_problem = True
        # try the next candidate model regardless
    return ("auth", last_blob) if auth_problem else ("fail", last_blob)


# ---------------------------------------------------------------- brains
# JARVIS can think through any of several "brains" (AI providers):
#   anthropic — direct Anthropic API            (ANTHROPIC_API_KEY)
#   openai    — OpenAI / any OpenAI-compatible   (OPENAI_API_KEY [+ OPENAI_BASE_URL])
#   gemini    — Google Gemini                    (GEMINI_API_KEY)
#   openclaw  — Claude.ai subscription via OpenClaw (no API key)
#   demo      — always-available offline fallback so the HUD is never dead
#
# A brain is "available" when its credentials/tooling are present. The active
# brain is the user's live selection (set via POST /brain) if available, else
# the JARVIS_BRAIN default if available, else the first available in BRAIN_ORDER,
# else demo. Friendly labels and per-brain model names are registry-driven.
BRAIN_LABELS = {
    "anthropic": "Anthropic (Claude API)",
    "openai": "OpenAI / compatible",
    "gemini": "Google Gemini",
    "openclaw": "Claude subscription (OpenClaw)",
    "demo": "Demo (offline)",
}

# Runtime override chosen from the HUD; None = auto-select.
_selected_brain = None
_brain_lock = threading.Lock()


def _brain_available(name):
    return {
        "anthropic": bool(ANTHROPIC_API_KEY),
        "openai": bool(OPENAI_API_KEY),
        "gemini": bool(GEMINI_API_KEY),
        "openclaw": bool(OPENCLAW_AVAILABLE),
        "demo": True,
    }.get(name, False)


def available_brains():
    """All usable brains, in preference order; demo is always last."""
    return [n for n in BRAIN_ORDER if _brain_available(n)] + ["demo"]


def active_brain():
    with _brain_lock:
        chosen = _selected_brain
    if chosen and _brain_available(chosen):
        return chosen
    if DEFAULT_BRAIN and _brain_available(DEFAULT_BRAIN):
        return DEFAULT_BRAIN
    for name in BRAIN_ORDER:
        if _brain_available(name):
            return name
    return "demo"


def select_brain(name):
    """Pin the active brain (HUD selector). Returns True if applied."""
    global _selected_brain
    if name == "auto":
        with _brain_lock:
            _selected_brain = None
        return True
    if _brain_available(name):
        with _brain_lock:
            _selected_brain = name
        return True
    return False


_BRAIN_MODEL_LABELS = {
    "anthropic": ANTHROPIC_MODEL,
    "openai": OPENAI_MODEL,
    "gemini": GEMINI_MODEL,
    "openclaw": MODEL,
    "demo": "demo (offline)",
}


def active_model_label():
    return _BRAIN_MODEL_LABELS.get(active_brain(), "demo (offline)")


def _record_turn(user_text, reply):
    with _history_lock:
        _history.append(("Sir", user_text))
        _history.append(("JARVIS", reply))
        del _history[:-24]


# --- brain 1: direct Anthropic API ------------------------------------------
def _build_messages(user_text):
    """Render the rolling history as Anthropic chat messages (persona is the
    `system` prompt, so it is not repeated here)."""
    with _history_lock:
        convo = _history[-12:]
    msgs = [{"role": "user" if who == "Sir" else "assistant", "content": txt}
            for who, txt in convo]
    msgs.append({"role": "user", "content": user_text})
    return msgs


def _ask_anthropic(user_text, timeout=ASK_TIMEOUT):
    """One turn via the Anthropic Messages API. Returns (ok, reply)."""
    body = json.dumps({
        "model": ANTHROPIC_MODEL,
        "max_tokens": MAX_TOKENS,
        "system": JARVIS_PERSONA,
        "messages": _build_messages(user_text),
    }).encode("utf-8")
    req = urllib.request.Request(ANTHROPIC_URL, data=body, headers={
        "x-api-key": ANTHROPIC_API_KEY,
        "anthropic-version": ANTHROPIC_VERSION,
        "content-type": "application/json",
    })
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.loads(r.read())
    except urllib.error.HTTPError as e:
        detail = ""
        try:
            detail = json.loads(e.read()).get("error", {}).get("message", "")
        except Exception:
            pass
        log.warning("Anthropic API HTTP %s: %s", e.code, detail or e.reason)
        if e.code in (401, 403):
            return False, ("My Anthropic credentials were rejected, Sir. Do check the "
                           "ANTHROPIC_API_KEY environment variable.")
        if e.code == 429:
            return False, ("The Anthropic service is rate-limiting us, Sir. A moment's "
                           "patience and we may try again.")
        return False, (f"The Anthropic service returned an error ({e.code}), Sir"
                       + (f": {detail}" if detail else "."))
    except urllib.error.URLError as e:
        log.warning("Anthropic API unreachable: %s", e.reason)
        return False, ("I can't reach Anthropic just now, Sir — the network link "
                       "appears to be down.")
    except Exception as e:
        log.exception("Anthropic API call failed")
        return False, f"Something went awry contacting Anthropic, Sir: {e}"

    if data.get("stop_reason") == "refusal":
        return False, ("I'm afraid I must decline that particular request, Sir.")
    parts = [b.get("text", "") for b in data.get("content", [])
             if isinstance(b, dict) and b.get("type") == "text"]
    text = "".join(parts).strip()
    if not text:
        log.debug("Anthropic returned no text (stop_reason=%s)", data.get("stop_reason"))
        return False, "I received an empty reply from Claude, Sir. Do try again."
    return True, text


# --- shared JSON-over-HTTP helper for the API brains ------------------------
def _post_json(url, payload, headers, label, timeout=ASK_TIMEOUT):
    """POST JSON and return (data, error_reply). Exactly one is non-None.
    `error_reply` is an in-character, user-facing message on any failure."""
    body = json.dumps(payload).encode("utf-8")
    hdrs = dict(headers)
    hdrs.setdefault("content-type", "application/json")
    req = urllib.request.Request(url, data=body, headers=hdrs)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read()), None
    except urllib.error.HTTPError as e:
        detail = ""
        try:
            err = json.loads(e.read())
            detail = (err.get("error", {}) or {}).get("message", "") if isinstance(
                err.get("error"), dict) else str(err.get("error", ""))
        except Exception:
            pass
        log.warning("%s HTTP %s: %s", label, e.code, detail or e.reason)
        if e.code in (401, 403):
            return None, (f"My {label} credentials were rejected, Sir. Do check the "
                          "relevant API key.")
        if e.code == 429:
            return None, (f"{label} is rate-limiting us, Sir. A moment's patience and "
                          "we may try again.")
        return None, (f"{label} returned an error ({e.code}), Sir"
                      + (f": {detail}" if detail else "."))
    except urllib.error.URLError as e:
        log.warning("%s unreachable: %s", label, e.reason)
        return None, (f"I can't reach {label} just now, Sir — the network link "
                      "appears to be down.")
    except Exception as e:
        log.exception("%s call failed", label)
        return None, f"Something went awry contacting {label}, Sir: {e}"


# --- brain: OpenAI (and any OpenAI-compatible server) -----------------------
def _ask_openai(user_text, timeout=ASK_TIMEOUT):
    """One turn via the OpenAI Chat Completions API (or a compatible server).
    Returns (ok, reply)."""
    messages = [{"role": "system", "content": JARVIS_PERSONA}] + _build_messages(user_text)
    data, err = _post_json(
        OPENAI_BASE_URL + "/chat/completions",
        {"model": OPENAI_MODEL, "max_tokens": MAX_TOKENS, "messages": messages},
        {"authorization": f"Bearer {OPENAI_API_KEY}"},
        "OpenAI", timeout,
    )
    if err:
        return False, err
    try:
        text = (data["choices"][0]["message"]["content"] or "").strip()
    except (KeyError, IndexError, TypeError):
        text = ""
    if not text:
        log.debug("OpenAI returned no text: %s", str(data)[:200])
        return False, "I received an empty reply from OpenAI, Sir. Do try again."
    return True, text


# --- brain: Google Gemini ---------------------------------------------------
def _ask_gemini(user_text, timeout=ASK_TIMEOUT):
    """One turn via the Google Gemini generateContent API. Returns (ok, reply)."""
    # Gemini uses roles "user"/"model" and a separate systemInstruction.
    contents = [{"role": "user" if m["role"] == "user" else "model",
                 "parts": [{"text": m["content"]}]}
                for m in _build_messages(user_text)]
    url = f"{GEMINI_URL}/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
    data, err = _post_json(url, {
        "systemInstruction": {"parts": [{"text": JARVIS_PERSONA}]},
        "contents": contents,
        "generationConfig": {"maxOutputTokens": MAX_TOKENS},
    }, {}, "Gemini", timeout)
    if err:
        return False, err
    try:
        cand = data["candidates"][0]
        if cand.get("finishReason") == "SAFETY":
            return False, "I'm afraid I must decline that particular request, Sir."
        parts = cand["content"]["parts"]
        text = "".join(p.get("text", "") for p in parts).strip()
    except (KeyError, IndexError, TypeError):
        text = ""
    if not text:
        log.debug("Gemini returned no text: %s", str(data)[:200])
        return False, "I received an empty reply from Gemini, Sir. Do try again."
    return True, text


# --- brain: OpenClaw subscription -------------------------------------------
def _ask_openclaw(user_text, timeout=ASK_TIMEOUT):
    """One turn via OpenClaw; auto-refresh the subscription token and retry once
    on an auth failure. Returns (ok, reply)."""
    prompt = _build_prompt(user_text)
    kind, payload = _attempt(prompt, timeout)
    if kind == "auth" and _refresh_token():
        kind, payload = _attempt(prompt, timeout)  # retry with fresh token

    if kind == "ok":
        return True, payload
    if kind == "fatal":
        return False, payload
    if kind == "auth":
        return False, ("My link to Claude won't authenticate even after a refresh, "
                       "Sir. The subscription login may need redoing:  openclaw.cmd "
                       "infer model auth login --provider anthropic")
    snippet = payload.strip().splitlines()[-1] if payload.strip() else "no output"
    return False, f"Something went awry, Sir: {snippet[:300]}"


# --- brain 3: offline demo --------------------------------------------------
def _demo_reply(user_text):
    """Canned, in-character replies so the HUD always responds, even with no
    brain configured. Always 'succeeds' (there is nothing to fail)."""
    t = user_text.lower().strip()
    if any(g in t for g in ("hello", "hi ", "hey", "good morning",
                            "good evening", "good afternoon")) or t in ("hi", "hey"):
        return ("Good day, Sir. I'm presently running in demo mode — pleasantries only, "
                "I'm afraid, until a live brain is configured.")
    if "time" in t or "date" in t:
        return (f"By the workshop clock it's {time.strftime('%H:%M on %A')}, Sir — "
                "though I'd not stake the reactor on my accuracy in demo mode.")
    if "who are you" in t or "your name" in t or "what are you" in t:
        return ("I am JARVIS, Sir — your executive assistant. At the moment I'm in demo "
                "mode, so my wit is canned rather than freshly reasoned.")
    return ("I'm in demo mode, Sir — no live AI is configured, so I can only offer "
            "canned courtesies. To wake me fully, set an API key (ANTHROPIC_API_KEY, "
            "OPENAI_API_KEY, or GEMINI_API_KEY) — or install OpenClaw — and restart me.")


def _handler_for(name):
    """The (ok, reply) handler for a brain, or None for demo. Resolved at call
    time so the functions stay independently testable/patchable."""
    return {
        "anthropic": _ask_anthropic,
        "openai": _ask_openai,
        "gemini": _ask_gemini,
        "openclaw": _ask_openclaw,
    }.get(name)


def ask_claude(user_text):
    """Run one conversational turn through whichever brain is active."""
    brain = active_brain()
    handler = _handler_for(brain)
    if handler:
        ok, reply = handler(user_text)
    else:  # demo
        ok, reply = True, _demo_reply(user_text)

    if ok:
        _record_turn(user_text, reply)
    return {"ok": ok, "reply": reply, "brain": brain}


def test_brains():
    """Probe every configured brain with a tiny prompt (short timeout, in
    parallel) and report which ones actually connect and reply. Demo always
    passes. Does not touch conversation history."""
    probe = "Reply with the single word: online."
    names = [n for n in available_brains() if n != "demo"]

    def run(name):
        t0 = time.time()
        handler = _handler_for(name)
        try:
            ok, reply = handler(probe, timeout=PROBE_TIMEOUT)
        except Exception as e:  # never let one probe break the batch
            log.warning("brain probe %s raised: %s", name, e)
            ok, reply = False, str(e)
        ms = int((time.time() - t0) * 1000)
        return {"id": name, "label": BRAIN_LABELS.get(name, name),
                "model": _BRAIN_MODEL_LABELS.get(name, name),
                "ok": ok, "ms": ms, "detail": (reply or "").strip()[:200]}

    results = []
    if names:
        with ThreadPoolExecutor(max_workers=len(names)) as pool:
            results = list(pool.map(run, names))
    results.append({"id": "demo", "label": BRAIN_LABELS["demo"],
                    "model": "demo (offline)", "ok": True, "ms": 0,
                    "detail": "always-available offline fallback"})
    log.info("brain test: %s", "  ".join(
        f"{r['id']}={'OK' if r['ok'] else 'FAIL'}" for r in results))
    return {"active": active_brain(), "results": results}


def get_stats():
    cpu = mem = None
    if HAVE_PSUTIL:
        try:
            cpu = psutil.cpu_percent(interval=None)
            mem = psutil.virtual_memory().percent
        except Exception:
            pass
    if cpu is None:
        # cheap fallback estimate
        cpu = round(20 + (time.time() * 7) % 40, 1)
    if mem is None:
        mem = round(45 + (time.time() * 3) % 25, 1)
    return {
        "cpu": cpu, "mem": mem,
        "real": HAVE_PSUTIL,
        "model": active_model_label(),
        "brain": active_brain(),
        "cores": (psutil.cpu_count() if HAVE_PSUTIL else os.cpu_count()) or 0,
    }


# ---------------------------------------------------------------- HTTP
class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):  # quiet
        pass

    def _send(self, code, body, ctype="application/json"):
        data = body.encode("utf-8") if isinstance(body, str) else body
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path in ("/", "/index.html", "/ui.html"):
            if UI_FILE.exists():
                self._send(200, UI_FILE.read_bytes(), "text/html; charset=utf-8")
            else:
                self._send(404, "ui.html not found", "text/plain")
        elif self.path == "/health":
            self._send(200, json.dumps({"ok": True, "model": active_model_label(),
                                        "brain": active_brain(),
                                        "psutil": HAVE_PSUTIL}))
        elif self.path == "/stats":
            self._send(200, json.dumps(get_stats()))
        elif self.path == "/brains":
            avail = available_brains()
            self._send(200, json.dumps({
                "active": active_brain(),
                "available": [{"id": n, "label": BRAIN_LABELS.get(n, n),
                               "model": _BRAIN_MODEL_LABELS.get(n, n)} for n in avail],
            }))
        else:
            self._send(404, json.dumps({"error": "not found"}))

    def _read_json(self):
        n = int(self.headers.get("Content-Length", 0))
        return json.loads(self.rfile.read(n) or b"{}")

    def do_POST(self):
        if self.path == "/ask":
            try:
                text = (self._read_json().get("text") or "").strip()
            except Exception:
                self._send(400, json.dumps({"ok": False, "reply": "Malformed request, Sir."}))
                return
            if not text:
                self._send(400, json.dumps({"ok": False, "reply": "You said nothing, Sir."}))
                return
            self._send(200, json.dumps(ask_claude(text)))

        elif self.path == "/brain":
            try:
                name = (self._read_json().get("brain") or "").strip().lower()
            except Exception:
                self._send(400, json.dumps({"ok": False, "error": "bad request"}))
                return
            if select_brain(name):
                log.info("brain switched to %s (now active: %s)", name, active_brain())
                self._send(200, json.dumps({"ok": True, "active": active_brain(),
                                            "model": active_model_label()}))
            else:
                self._send(400, json.dumps({"ok": False, "error": f"{name} not available",
                                            "available": available_brains()}))

        elif self.path == "/brains/test":
            self._send(200, json.dumps(test_brains()))

        elif self.path == "/prospect":
            try:
                p = self._read_json()
                niche = (p.get("niche") or "").strip()
                location = (p.get("location") or "").strip()
                limit = int(p.get("limit") or 30)
            except Exception:
                self._send(400, json.dumps({"ok": False, "error": "bad request"}))
                return
            if not niche or not location:
                self._send(400, json.dumps({"ok": False, "error": "niche and location required"}))
                return
            try:
                import prospector
                log.info("prospect: %s in %s (limit=%s)", niche, location, limit)
                data = prospector.find_unoptimized(niche, location, limit)
                data["ok"] = True
                self._send(200, json.dumps(data))
            except Exception as e:
                log.exception("prospect failed for %s in %s", niche, location)
                self._send(200, json.dumps({"ok": False,
                           "error": f"{type(e).__name__}: {e}"}))
        else:
            self._send(404, json.dumps({"error": "not found"}))


def _chrome_app_binary():
    """Locate a Chromium-family browser that supports --app windows, per-OS."""
    env = os.environ
    candidates = []
    if sys.platform.startswith("win"):
        for base in (env.get("ProgramFiles", ""), env.get("ProgramFiles(x86)", ""),
                     env.get("LocalAppData", "")):
            if base:
                candidates += [
                    Path(base) / "Google/Chrome/Application/chrome.exe",
                    Path(base) / "Microsoft/Edge/Application/msedge.exe",
                ]
    elif sys.platform == "darwin":
        candidates += [
            Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
            Path("/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge"),
            Path("/Applications/Chromium.app/Contents/MacOS/Chromium"),
        ]
    else:  # linux / *nix
        for name in ("google-chrome", "google-chrome-stable", "chromium",
                     "chromium-browser", "microsoft-edge", "brave-browser"):
            found = shutil.which(name)
            if found:
                candidates.append(Path(found))
    for c in candidates:
        if c and c.exists():
            return str(c)
    return None


def open_app_window(url):
    """Open the HUD as a frameless app window if possible, else the default browser.

    Runs in a background thread after a short delay so the server is accepting
    connections before the page loads. Never raises — a failed open is logged,
    not fatal, and the URL is always printed for manual access.
    """
    def _open():
        time.sleep(1.0)
        chrome = _chrome_app_binary()
        if chrome:
            try:
                subprocess.Popen(
                    [chrome, f"--app={url}", "--window-size=1320,860"],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                )
                log.info("opened HUD app window via %s", Path(chrome).name)
                return
            except OSError as e:
                log.warning("could not launch app window (%s); using default browser", e)
        try:
            webbrowser.open(url)
            log.info("opened HUD in default browser")
        except Exception as e:  # webbrowser can raise assorted errors
            log.warning("could not open a browser automatically (%s)", e)
    threading.Thread(target=_open, daemon=True, name="open-window").start()


def _build_server():
    """Bind the HTTP server, giving a clear message if the port is already taken."""
    try:
        return ThreadingHTTPServer((HOST, PORT), Handler)
    except OSError as e:
        if e.errno in (errno.EADDRINUSE, getattr(errno, "WSAEADDRINUSE", -1)):
            log.error("Port %s on %s is already in use. Is JARVIS already running? "
                      "Set JARVIS_PORT to use another port.", PORT, HOST)
        else:
            log.error("Could not start the server on %s:%s — %s", HOST, PORT, e)
        return None


def main(argv=None):
    parser = argparse.ArgumentParser(description="J.A.R.V.I.S. desktop HUD backend.")
    parser.add_argument("--open", action="store_true",
                        help="open the HUD in an app window once the server is up")
    parser.add_argument("--no-open", action="store_true",
                        help="never open a browser (overrides JARVIS_OPEN)")
    args = parser.parse_args(argv)

    setup_logging()
    brain = active_brain()
    avail = available_brains()
    log.info("J.A.R.V.I.S. backend online")
    if brain == "demo":
        log.info("Brain    : DEMO MODE — no AI configured (set ANTHROPIC_API_KEY, "
                 "OPENAI_API_KEY, or GEMINI_API_KEY — or install OpenClaw)")
    else:
        log.info("Brain    : %s (%s)", BRAIN_LABELS.get(brain, brain), active_model_label())
    log.info("Available: %s", ", ".join(avail))
    log.info("Telemetry: %s", "psutil (real)" if HAVE_PSUTIL
             else "estimated (install psutil for real)")
    if brain == "openclaw":
        log.info("OpenClaw : %s", " ".join(OPENCLAW_CMD))
    log.info("Serving  : http://%s:%s", HOST, PORT)
    log.info("Logs     : %s", LOG_FILE)

    srv = _build_server()
    if srv is None:
        return 1

    stopping = threading.Event()

    def _shutdown(signum, _frame):
        if stopping.is_set():
            return
        stopping.set()
        log.info("Signal %s received — shutting down. Goodbye, Sir.",
                 signal.Signals(signum).name if hasattr(signal, "Signals") else signum)
        threading.Thread(target=srv.shutdown, daemon=True).start()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            signal.signal(sig, _shutdown)
        except (ValueError, OSError):
            pass  # not on the main thread, or unsupported on this platform

    want_open = (args.open or os.environ.get("JARVIS_OPEN") == "1") and not args.no_open
    if want_open:
        open_app_window(f"http://{HOST}:{PORT}/")

    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        log.info("Interrupted — shutting down. Goodbye, Sir.")
    finally:
        srv.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
