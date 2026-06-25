#!/usr/bin/env python3
"""
J.A.R.V.I.S. — local backend for the desktop HUD app.

Serves the UI and bridges the command console to Claude via OpenClaw's
`claude-cli` provider (your Claude.ai subscription — NO API KEY required).

Specialist agent team (see agents.py):
  F.R.I.D.A.Y.  — Research & Intelligence
  E.D.I.T.H.    — Security & Threat Analysis
  H.O.M.E.R.    — Code & Engineering
  V.I.S.I.O.N.  — Writing & Communications
  D.U.M.E.      — Data & Analytics

Run:  python jarvis_server.py   (or use JARVIS.bat)
"""

import collections
import json
import os
import shutil
import subprocess
import sys
import threading
import time
import urllib.request
import urllib.error
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import agents as agent_team
import pepper as pepper_coordinator
import shopify_agent

# ---------------------------------------------------------------- config
HOST = os.environ.get("JARVIS_HOST", "127.0.0.1")
PORT = int(os.environ.get("JARVIS_PORT", "8765"))
MODELS = [m.strip() for m in os.environ.get(
    "JARVIS_MODELS",
    "claude-cli/claude-opus-4-8,anthropic/claude-opus-4-8"
).split(",") if m.strip()]
MODEL = MODELS[0]
ASK_TIMEOUT = int(os.environ.get("JARVIS_TIMEOUT", "240"))
HERE = Path(__file__).resolve().parent
UI_FILE = HERE / "ui.html"

# Try optional psutil
try:
    import psutil  # type: ignore
    HAVE_PSUTIL = True
    psutil.cpu_percent(interval=None)
except Exception:
    HAVE_PSUTIL = False

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
    return [npm_shim or "openclaw"]

OPENCLAW_CMD = _find_openclaw_cmd()

# --- subscription token auto-refresh ---
CRED_FILE = Path(os.path.expanduser("~/.claude/.credentials.json"))
AUTH_PROFILES = Path(os.path.expanduser("~/.openclaw/agents/main/agent/auth-profiles.json"))
OAUTH_CLIENT_ID = "9d1c250a-e61b-44d9-88ed-5944d1962f5e"
OAUTH_TOKEN_URL = "https://api.anthropic.com/v1/oauth/token"
_refresh_lock = threading.Lock()


def _refresh_token():
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
            print("  [auth] subscription token refreshed automatically")
            return True
        except Exception as e:
            print(f"  [auth] refresh failed: {e}")
            return False


# rolling conversation memory
_history = []
_history_lock = threading.Lock()

# active agent state (for /status polling)
_active_agent = {"id": "jarvis", "name": "JARVIS", "title": "Executive AI", "color": "#39c7ff"}
_active_lock = threading.Lock()

# ── activity log & per-agent stats ────────────────────────────────────────────
_activity_log = collections.deque(maxlen=150)
_activity_lock = threading.Lock()

_agent_stats = {aid: {"tasks": 0, "last_ts": "", "last_query": ""}
                for aid in list(agent_team.TEAM.keys()) + ["jarvis"]}
_stats_lock = threading.Lock()

_current_pipeline: list = []
_pipeline_lock = threading.Lock()


def _log_event(agent_id: str, event: str,
               query: str = "", reply: str = "", pipeline: list | None = None):
    """Append one entry to the activity log and update per-agent stats."""
    now = time.time()
    a = agent_team.TEAM.get(agent_id, {})
    entry = {
        "ts": now,
        "ts_str": time.strftime("%H:%M:%S"),
        "agent_id": agent_id,
        "agent_name": a.get("name", "JARVIS"),
        "agent_color": a.get("color", "#39c7ff"),
        "agent_emoji": a.get("emoji", "🤖"),
        "event": event,      # routing|start|done|error|pipeline_start|pipeline_stage|pipeline_done
        "query": query[:80],
        "reply": reply[:140],
        "pipeline": pipeline,
    }
    with _activity_lock:
        _activity_log.appendleft(entry)
    if event in ("done", "pipeline_done"):
        sid = agent_id if agent_id in _agent_stats else "jarvis"
        with _stats_lock:
            _agent_stats[sid]["tasks"] += 1
            _agent_stats[sid]["last_ts"] = entry["ts_str"]
            _agent_stats[sid]["last_query"] = query[:60]


def _set_active(agent_id: str):
    with _active_lock:
        if agent_id == "jarvis":
            _active_agent.update({"id": "jarvis", "name": "JARVIS",
                                   "title": "Executive AI", "color": "#39c7ff"})
        else:
            a = agent_team.TEAM[agent_id]
            _active_agent.update({"id": agent_id, "name": a["name"],
                                   "title": a["title"], "color": a["color"]})


_META_PREFIXES = ("model.run via", "provider:", "model:", "outputs:", "attempts:",
                  "transport:", "capability:", "ok:", "mediaurl:", "warning:")


def _strip_preamble(s):
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
    s = (stdout or "").strip()
    if not s:
        return ""
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
        return _strip_preamble(s)
    for key in ("outputs", "text", "output", "reply", "response", "content", "message"):
        v = data.get(key) if isinstance(data, dict) else None
        if isinstance(v, str) and v.strip():
            return v.strip()
        if isinstance(v, list):
            parts = [b.get("text", "") for b in v if isinstance(b, dict)]
            joined = "".join(parts).strip()
            if joined:
                return joined
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
    cmd = OPENCLAW_CMD + ["infer", "model", "run",
                          "--model", model, "--prompt", prompt, "--local", "--json"]
    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True,
            encoding="utf-8", errors="replace",
            timeout=ASK_TIMEOUT, cwd=str(HERE), shell=False,
        )
    except subprocess.TimeoutExpired:
        return "", "", ("Apologies, Sir — that took longer than I'm willing to keep "
                        "you waiting. Do try again.")
    except FileNotFoundError:
        return "", "", ("I can't locate the OpenClaw executable, Sir. Ensure "
                        "`openclaw` is installed and on PATH.")
    blob = (proc.stdout or "") + "\n" + (proc.stderr or "")
    return _extract_text(proc.stdout or ""), blob, None


_AUTH_MARKERS = ("authentication_error", "Invalid authentication", "401",
                 "GatewayCredentials", "credentials before opening",
                 "Unknown provider", "not configured", "No API key", "No text output")


def _attempt(prompt):
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
    return ("auth", last_blob) if auth_problem else ("fail", last_blob)


def _agent_result_or_error(kind, payload, agent_id):
    """Convert an _attempt result into the final response dict."""
    if kind == "ok":
        return kind, payload
    if kind == "fatal":
        return "fatal", payload
    return kind, payload


def ask_claude(user_text):
    """Route the request to the right specialist and run it."""
    with _history_lock:
        convo = list(_history[-12:])

    _log_event("jarvis", "routing", query=user_text)

    # ── check for multi-agent pipeline first ──────────────────────────────
    pipeline = agent_team.route_pipeline(user_text)
    if pipeline:
        return _run_pipeline(user_text, convo, pipeline)

    # ── single-agent routing ───────────────────────────────────────────────
    agent_id = agent_team.route(user_text)
    _set_active(agent_id)
    _log_event(agent_id, "start", query=user_text)

    prompt = agent_team.build_prompt(user_text, convo, agent_id)
    kind, payload = _attempt(prompt)
    if kind == "auth" and _refresh_token():
        kind, payload = _attempt(prompt)

    _set_active("jarvis")  # back to idle

    if kind == "ok":
        agent_info = agent_team.TEAM.get(agent_id, {})
        speaker = agent_info.get("name", "JARVIS")
        _log_event(agent_id, "done", query=user_text, reply=payload)
        with _history_lock:
            _history.append(("Sir", user_text))
            _history.append((speaker, payload))
            del _history[:-24]
        return {
            "ok": True,
            "reply": payload,
            "agent": agent_id,
            "agent_name": agent_info.get("name", "JARVIS"),
            "agent_title": agent_info.get("title", "Executive AI"),
            "agent_color": agent_info.get("color", "#39c7ff"),
            "pipeline": False,
        }

    _log_event(agent_id, "error", query=user_text, reply=str(payload)[:120])
    if kind == "fatal":
        return {"ok": False, "reply": payload}
    if kind == "auth":
        return {"ok": False, "reply":
                "My link to Claude won't authenticate even after a refresh, Sir. "
                "Re-run: openclaw.cmd infer model auth login --provider anthropic"}
    snippet = payload.strip().splitlines()[-1] if payload.strip() else "no output"
    return {"ok": False, "reply": f"Something went awry, Sir: {snippet[:300]}"}


def _run_pipeline(user_text: str, convo: list, pipeline: list) -> dict:
    """Run a multi-agent pipeline: each agent's output feeds the next."""
    prior_output = ""
    last_agent_id = pipeline[-1]
    all_names = [agent_team.TEAM[a]["name"] for a in pipeline]

    _log_event("jarvis", "pipeline_start", query=user_text, pipeline=pipeline)
    with _pipeline_lock:
        _current_pipeline.clear()
        _current_pipeline.extend(pipeline)

    for stage, agent_id in enumerate(pipeline, 1):
        _set_active(agent_id)
        _log_event(agent_id, "start", query=user_text, pipeline=pipeline)
        if stage == 1:
            prompt = agent_team.build_prompt(user_text, convo, agent_id)
        else:
            prompt = agent_team.build_pipeline_prompt(user_text, prior_output, agent_id, stage)

        kind, payload = _attempt(prompt)
        if kind == "auth" and _refresh_token():
            kind, payload = _attempt(prompt)

        if kind != "ok":
            _set_active("jarvis")
            _log_event(agent_id, "error", query=user_text, reply=str(payload)[:120], pipeline=pipeline)
            with _pipeline_lock:
                _current_pipeline.clear()
            snippet = payload.strip().splitlines()[-1] if payload.strip() else "no output"
            return {"ok": False,
                    "reply": f"Pipeline failed at stage {stage} ({agent_team.TEAM[agent_id]['name']}): {snippet[:200]}"}
        _log_event(agent_id, "pipeline_stage", query=user_text, reply=payload, pipeline=pipeline)
        prior_output = payload

    _set_active("jarvis")
    with _pipeline_lock:
        _current_pipeline.clear()

    final_agent = agent_team.TEAM[last_agent_id]
    _log_event(last_agent_id, "pipeline_done", query=user_text, reply=prior_output, pipeline=pipeline)
    with _history_lock:
        _history.append(("Sir", user_text))
        _history.append((final_agent["name"], prior_output))
        del _history[:-24]

    return {
        "ok": True,
        "reply": prior_output,
        "agent": last_agent_id,
        "agent_name": final_agent["name"],
        "agent_title": final_agent["title"],
        "agent_color": final_agent["color"],
        "pipeline": True,
        "pipeline_agents": all_names,
    }


def get_stats():
    cpu = mem = None
    if HAVE_PSUTIL:
        try:
            cpu = psutil.cpu_percent(interval=None)
            mem = psutil.virtual_memory().percent
        except Exception:
            pass
    if cpu is None:
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
    def log_message(self, *a):
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
            self._send(200, json.dumps({"ok": True, "model": MODEL, "psutil": HAVE_PSUTIL}))
        elif self.path == "/stats":
            self._send(200, json.dumps(get_stats()))
        elif self.path == "/agents":
            with _active_lock:
                active = dict(_active_agent)
            self._send(200, json.dumps({
                "team": agent_team.team_summary(),
                "active": active,
            }))
        elif self.path == "/agent-log":
            with _activity_lock:
                log = list(_activity_log)[:60]
            with _stats_lock:
                stats = {k: dict(v) for k, v in _agent_stats.items()}
            with _active_lock:
                active = dict(_active_agent)
            with _pipeline_lock:
                cur_pipeline = list(_current_pipeline)
            self._send(200, json.dumps({
                "log": log,
                "stats": stats,
                "active": active,
                "current_pipeline": cur_pipeline,
                "team": agent_team.team_summary(),
            }))
        elif self.path in ("/dashboard", "/dashboard.html"):
            f = HERE / "dashboard.html"
            if f.exists():
                self._send(200, f.read_bytes(), "text/html; charset=utf-8")
            else:
                self._send(404, b"dashboard.html not found", "text/plain")
        elif self.path in ("/business", "/business.html"):
            f = HERE / "business.html"
            if f.exists():
                self._send(200, f.read_bytes(), "text/html; charset=utf-8")
            else:
                self._send(404, b"business.html not found", "text/plain")
        elif self.path == "/pepper/status":
            self._send(200, json.dumps(pepper_coordinator.status()))
        elif self.path == "/shopify/status":
            result = shopify_agent.get_client().ping()
            self._send(200, json.dumps(result))
        elif self.path == "/shopify/stats":
            if not shopify_agent.is_configured():
                self._send(200, json.dumps({"ok": False, "error": "Shopify not configured"}))
                return
            try:
                summary = shopify_agent.get_client().sales_summary(since_days=7)
                summary["ok"] = True
                self._send(200, json.dumps(summary))
            except Exception as e:
                self._send(200, json.dumps({"ok": False, "error": str(e)}))
        elif self.path == "/shopify/orders":
            if not shopify_agent.is_configured():
                self._send(200, json.dumps({"ok": False, "error": "Shopify not configured"}))
                return
            try:
                orders = shopify_agent.get_client().list_orders(limit=10)
                self._send(200, json.dumps({"ok": True, "orders": orders}))
            except Exception as e:
                self._send(200, json.dumps({"ok": False, "error": str(e)}))
        elif self.path == "/shopify/products":
            if not shopify_agent.is_configured():
                self._send(200, json.dumps({"ok": False, "error": "Shopify not configured"}))
                return
            try:
                products = shopify_agent.get_client().list_products(limit=20)
                self._send(200, json.dumps({"ok": True, "products": products}))
            except Exception as e:
                self._send(200, json.dumps({"ok": False, "error": str(e)}))
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

        elif self.path == "/pepper/trigger":
            try:
                p = self._read_json()
                task_id = (p.get("task_id") or "").strip()
            except Exception:
                self._send(400, json.dumps({"ok": False, "error": "bad request"}))
                return
            if not task_id:
                self._send(400, json.dumps({"ok": False, "error": "task_id required"}))
                return
            result = pepper_coordinator.trigger_task(task_id)
            self._send(200, json.dumps(result))

        elif self.path == "/shopify/create-product":
            if not shopify_agent.is_configured():
                self._send(200, json.dumps({"ok": False, "error": "Shopify not configured"}))
                return
            try:
                p = self._read_json()
                product = shopify_agent.get_client().create_product(
                    title=p.get("title", ""),
                    body_html=p.get("body_html", ""),
                    price=p.get("price", 27),
                    tags=p.get("tags", ""),
                )
                self._send(200, json.dumps({"ok": True, "product": product}))
            except Exception as e:
                self._send(200, json.dumps({"ok": False, "error": str(e)}))

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
                data = prospector.find_unoptimized(niche, location, limit)
                data["ok"] = True
                self._send(200, json.dumps(data))
            except Exception as e:
                self._send(200, json.dumps({"ok": False,
                           "error": f"{type(e).__name__}: {e}"}))
        else:
            self._send(404, json.dumps({"error": "not found"}))


def _pepper_llm(prompt: str, agent_override: str = None) -> str:
    """LLM call adapter for PEPPER — routes through the specialist team."""
    result = ask_claude(prompt)
    return result.get("reply", "")


def main():
    print(f"\n  J.A.R.V.I.S. backend online")
    print(f"  Model    : {MODEL}  (Claude subscription — no API key)")
    print(f"  Telemetry: {'psutil (real)' if HAVE_PSUTIL else 'estimated (install psutil for real)'}")
    print(f"  OpenClaw : {' '.join(OPENCLAW_CMD)}")
    print(f"  Team     : JARVIS + {len(agent_team.TEAM)} specialists "
          f"({', '.join(a['name'] for a in agent_team.TEAM.values())})")
    shopify_status = "configured" if shopify_agent.is_configured() else "not configured (set SHOPIFY_SHOP + SHOPIFY_TOKEN)"
    print(f"  Shopify  : {shopify_status}")
    print(f"  PEPPER   : autonomous scheduler starting…")
    print(f"  Serving  : http://{HOST}:{PORT}\n")

    # Start PEPPER autonomous coordinator
    shopify_fn = shopify_agent.get_client().ping if shopify_agent.is_configured() else None
    pepper_coordinator.start(_pepper_llm, shopify_fn)

    srv = ThreadingHTTPServer((HOST, PORT), Handler)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\n  Shutting down. Goodbye, Sir.")
        pepper_coordinator.stop()
        srv.shutdown()


if __name__ == "__main__":
    main()
