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


def ask_claude(user_text):
    """Run one turn; auto-refresh the subscription token and retry once on auth failure."""
    prompt = _build_prompt(user_text)
    kind, payload = _attempt(prompt)
    if kind == "auth" and _refresh_token():
        kind, payload = _attempt(prompt)  # retry with fresh token

    if kind == "ok":
        with _history_lock:
            _history.append(("Sir", user_text))
            _history.append(("JARVIS", payload))
            del _history[:-24]
        return {"ok": True, "reply": payload}
    if kind == "fatal":
        return {"ok": False, "reply": payload}
    if kind == "auth":
        return {"ok": False, "reply":
                "My link to Claude won't authenticate even after a refresh, Sir. The "
                "subscription login may need redoing:  openclaw.cmd infer model auth "
                "login --provider anthropic"}
    snippet = payload.strip().splitlines()[-1] if payload.strip() else "no output"
    return {"ok": False, "reply": f"Something went awry, Sir: {snippet[:300]}"}


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
        "model": MODEL,
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
            self._send(200, json.dumps({"ok": True, "model": MODEL,
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
    log.info("J.A.R.V.I.S. backend online")
    log.info("Model    : %s  (Claude subscription — no API key)", MODEL)
    log.info("Telemetry: %s", "psutil (real)" if HAVE_PSUTIL
             else "estimated (install psutil for real)")
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
