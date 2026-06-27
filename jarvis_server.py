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

# Direct Anthropic API (works out of the box with just an API key — no OpenClaw).
# The key is read from the environment only; it is never hardcoded or logged.
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "").strip()
ANTHROPIC_MODEL = os.environ.get("JARVIS_ANTHROPIC_MODEL", "claude-opus-4-8").strip()
ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_VERSION = "2023-06-01"
ANTHROPIC_MAX_TOKENS = int(os.environ.get("JARVIS_MAX_TOKENS", "1024"))

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


def _run_model(model, prompt):
    """One subprocess call for a single model. Returns (text, blob, fatal_msg)."""
    cmd = OPENCLAW_CMD + ["infer", "model", "run",
                          "--model", model, "--prompt", prompt, "--local", "--json"]
    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True,
            encoding="utf-8", errors="replace",
            timeout=ASK_TIMEOUT, cwd=str(HERE), shell=False,
        )
    except subprocess.TimeoutExpired:
        log.warning("model %s timed out after %ss", model, ASK_TIMEOUT)
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


def _attempt(prompt):
    """Try each candidate model. Returns (kind, payload):
    ('ok', text) | ('fatal', msg) | ('auth', blob) | ('fail', blob)."""
    auth_problem = False
    last_blob = ""
    for model in MODELS:
        text, blob, fatal = _run_model(model, prompt)
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
# JARVIS can think through one of three "brains", chosen automatically:
#   1. anthropic — a direct Anthropic API call (needs only ANTHROPIC_API_KEY)
#   2. openclaw  — the Claude.ai subscription via OpenClaw (no API key)
#   3. demo      — an always-available offline fallback so the HUD is never dead
def active_brain():
    if ANTHROPIC_API_KEY:
        return "anthropic"
    if OPENCLAW_AVAILABLE:
        return "openclaw"
    return "demo"


def active_model_label():
    brain = active_brain()
    if brain == "anthropic":
        return ANTHROPIC_MODEL
    if brain == "openclaw":
        return MODEL
    return "demo (offline)"


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


def _ask_anthropic(user_text):
    """One turn via the Anthropic Messages API. Returns (ok, reply)."""
    body = json.dumps({
        "model": ANTHROPIC_MODEL,
        "max_tokens": ANTHROPIC_MAX_TOKENS,
        "system": JARVIS_PERSONA,
        "messages": _build_messages(user_text),
    }).encode("utf-8")
    req = urllib.request.Request(ANTHROPIC_URL, data=body, headers={
        "x-api-key": ANTHROPIC_API_KEY,
        "anthropic-version": ANTHROPIC_VERSION,
        "content-type": "application/json",
    })
    try:
        with urllib.request.urlopen(req, timeout=ASK_TIMEOUT) as r:
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


# --- brain 2: OpenClaw subscription -----------------------------------------
def _ask_openclaw(user_text):
    """One turn via OpenClaw; auto-refresh the subscription token and retry once
    on an auth failure. Returns (ok, reply)."""
    prompt = _build_prompt(user_text)
    kind, payload = _attempt(prompt)
    if kind == "auth" and _refresh_token():
        kind, payload = _attempt(prompt)  # retry with fresh token

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
    return ("I'm in demo mode, Sir — no live link to Claude is configured, so I can only "
            "offer canned courtesies. To wake me fully, set an ANTHROPIC_API_KEY "
            "environment variable (or install OpenClaw) and restart me.")


def ask_claude(user_text):
    """Run one conversational turn through whichever brain is available."""
    brain = active_brain()
    if brain == "anthropic":
        ok, reply = _ask_anthropic(user_text)
    elif brain == "openclaw":
        ok, reply = _ask_openclaw(user_text)
    else:
        ok, reply = True, _demo_reply(user_text)

    if ok:
        _record_turn(user_text, reply)
    return {"ok": ok, "reply": reply, "brain": brain}


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
    brain_desc = {
        "anthropic": f"Anthropic API ({ANTHROPIC_MODEL})",
        "openclaw": f"OpenClaw subscription ({MODEL}) — no API key",
        "demo": "DEMO MODE — no brain configured "
                "(set ANTHROPIC_API_KEY or install OpenClaw for real replies)",
    }[brain]
    log.info("J.A.R.V.I.S. backend online")
    log.info("Brain    : %s", brain_desc)
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
