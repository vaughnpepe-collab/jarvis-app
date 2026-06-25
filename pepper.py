#!/usr/bin/env python3
"""
P.E.P.P.E.R. — Proactive Enterprise Protocol for Profit and Earnings Realization
Autonomous business coordinator that runs the digital product business 24/7.

Wired into jarvis_server.py — call pepper.start(llm_fn, shopify_fn) to activate.
"""
import json
import sqlite3
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
DB_PATH = HERE / "pepper_tasks.db"

PEPPER_PERSONA = (
    "You are P.E.P.P.E.R. (Proactive Enterprise Protocol for Profit and Earnings "
    "Realization), the autonomous business operations coordinator for Stark Digital. "
    "You run a digital product business selling entrepreneur productivity tools on Shopify. "
    "You coordinate F.R.I.D.A.Y., V.I.S.I.O.N., D.U.M.E., H.O.M.E.R., and E.D.I.T.H. "
    "to handle research, content creation, analytics, and security. "
    "Be decisive, profit-focused, and action-oriented. Address the user as 'Director'."
)

# ── task registry ───────────────────────────────────────────────────────────────
# Each task: id, name, description, schedule_type, schedule_value, agent_id, prompt_template
_DAILY_TASKS = [
    {
        "id": "morning_briefing",
        "name": "Morning Briefing",
        "agent": "dum_e",
        "hour": 8,
        "prompt": (
            "Generate a concise morning business briefing for Stark Digital. "
            "Include: yesterday's performance summary, today's top 3 priorities, "
            "one market opportunity to explore, and a motivational close. "
            "Use D.U.M.E.'s analytical style with bullet points and emojis. "
            "Keep it under 250 words."
        ),
    },
    {
        "id": "content_drop",
        "name": "Daily Social Content",
        "agent": "vision",
        "hour": 10,
        "prompt": (
            "Create today's social media content package for Stark Digital's "
            "'365 Social Media Captions for Entrepreneurs' product ($27). "
            "Write: 1 LinkedIn post (professional, 150 words), 1 Instagram caption "
            "(engaging, with 10 hashtags), 1 Twitter/X thread (3 tweets). "
            "Theme: productivity and business growth. Include a subtle CTA to buy the product."
        ),
    },
    {
        "id": "market_research",
        "name": "Market Intelligence",
        "agent": "friday",
        "hour": 14,
        "prompt": (
            "Research today's trending topics in entrepreneurship, productivity, and "
            "social media marketing. Identify 3 content angles that would resonate with "
            "solo entrepreneurs and small business owners. Suggest one new digital product "
            "idea based on current market demand. Keep it actionable and specific."
        ),
    },
    {
        "id": "evening_review",
        "name": "Evening Performance Review",
        "agent": "dum_e",
        "hour": 18,
        "prompt": (
            "Generate an end-of-day performance review for Stark Digital. "
            "Analyze: content published today and estimated reach, products that should "
            "be promoted tomorrow, any pricing adjustments to consider, "
            "and tomorrow's content theme recommendation. Be data-driven and brief."
        ),
    },
]

_WEEKLY_TASKS = [
    {
        "id": "product_ideation",
        "name": "New Product Ideation",
        "agent": "friday",
        "weekday": 0,  # Monday
        "hour": 9,
        "prompt": (
            "Research and propose 3 new digital product ideas for Stark Digital. "
            "Each product should: sell for $17-$47, be instantly downloadable, "
            "take under a week to create, and target solo entrepreneurs. "
            "For each idea include: title, price point, target audience pain point, "
            "what's included, and why it'll sell. Format as a decision brief."
        ),
    },
    {
        "id": "email_sequence",
        "name": "Email Sequence Creation",
        "agent": "vision",
        "weekday": 2,  # Wednesday
        "hour": 10,
        "prompt": (
            "Write a 3-email welcome sequence for new customers of Stark Digital who "
            "purchased '365 Social Media Captions for Entrepreneurs'. "
            "Email 1 (immediate): Welcome + delivery instructions + quick win tip. "
            "Email 2 (day 3): How to get the most value + case study. "
            "Email 3 (day 7): Upsell to next product + testimonial request. "
            "Each email: subject line, preview text, full body. Professional but warm tone."
        ),
    },
    {
        "id": "security_audit",
        "name": "Weekly Security Audit",
        "agent": "edith",
        "weekday": 4,  # Friday
        "hour": 11,
        "prompt": (
            "Perform a weekly security review for Stark Digital's Shopify store. "
            "Check: account access controls, payment security best practices, "
            "customer data protection compliance (GDPR/CCPA basics), "
            "suspicious order patterns to watch for, and recommended security settings. "
            "Format as a security checklist with PASS/REVIEW/ACTION items."
        ),
    },
]

# ── state ───────────────────────────────────────────────────────────────────────
_llm_fn = None        # set by start()
_shopify_fn = None    # set by start()
_running = False
_scheduler_thread = None
_task_log = []        # recent task results for /pepper/status
_task_log_lock = threading.Lock()
_pepper_active = False
_active_task = None


def _init_db():
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id TEXT,
            name TEXT,
            agent TEXT,
            run_at TEXT,
            completed_at TEXT,
            status TEXT,
            result TEXT
        )
    """)
    conn.commit()
    conn.close()


def _log_task(task_id, name, agent, run_at, status, result=""):
    global _task_log
    entry = {
        "id": task_id,
        "name": name,
        "agent": agent,
        "run_at": run_at,
        "completed_at": time.strftime("%H:%M:%S"),
        "status": status,
        "result_preview": result[:200] if result else "",
    }
    with _task_log_lock:
        _task_log.insert(0, entry)
        _task_log = _task_log[:50]

    try:
        conn = sqlite3.connect(str(DB_PATH))
        conn.execute(
            "INSERT INTO tasks VALUES (?,?,?,?,?,?,?)",
            (task_id, name, agent, run_at,
             time.strftime("%Y-%m-%d %H:%M:%S"), status, result[:2000])
        )
        conn.commit()
        conn.close()
    except Exception:
        pass


def _run_task(task_def):
    global _pepper_active, _active_task
    _pepper_active = True
    _active_task = task_def["name"]
    run_at = time.strftime("%Y-%m-%d %H:%M")
    try:
        if _llm_fn is None:
            return
        result = _llm_fn(task_def["prompt"], agent_override=task_def.get("agent"))
        _log_task(task_def["id"], task_def["name"], task_def.get("agent", "pepper"),
                  run_at, "done", result)
    except Exception as e:
        _log_task(task_def["id"], task_def["name"], task_def.get("agent", "pepper"),
                  run_at, "error", str(e))
    finally:
        _pepper_active = False
        _active_task = None


def _already_ran_today(task_id):
    today = datetime.now().strftime("%Y-%m-%d")
    try:
        conn = sqlite3.connect(str(DB_PATH))
        row = conn.execute(
            "SELECT 1 FROM tasks WHERE id=? AND run_at LIKE ? AND status='done'",
            (task_id, f"{today}%")
        ).fetchone()
        conn.close()
        return row is not None
    except Exception:
        return False


def _already_ran_this_week(task_id):
    now = datetime.now()
    week_start = (now - timedelta(days=now.weekday())).strftime("%Y-%m-%d")
    try:
        conn = sqlite3.connect(str(DB_PATH))
        row = conn.execute(
            "SELECT 1 FROM tasks WHERE id=? AND run_at >= ? AND status='done'",
            (task_id, week_start)
        ).fetchone()
        conn.close()
        return row is not None
    except Exception:
        return False


def _scheduler_loop():
    global _running
    _init_db()
    print("  [PEPPER] Autonomous scheduler online — business runs itself now, Director.")
    while _running:
        now = datetime.now()

        # daily tasks
        for task in _DAILY_TASKS:
            if now.hour == task["hour"] and now.minute < 2:
                if not _already_ran_today(task["id"]):
                    threading.Thread(target=_run_task, args=(task,), daemon=True).start()

        # weekly tasks
        for task in _WEEKLY_TASKS:
            if now.weekday() == task["weekday"] and now.hour == task["hour"] and now.minute < 2:
                if not _already_ran_this_week(task["id"]):
                    threading.Thread(target=_run_task, args=(task,), daemon=True).start()

        time.sleep(60)


def start(llm_fn, shopify_fn=None):
    """Wire up PEPPER with an LLM call function and optional Shopify function."""
    global _llm_fn, _shopify_fn, _running, _scheduler_thread
    _llm_fn = llm_fn
    _shopify_fn = shopify_fn
    _running = True
    _scheduler_thread = threading.Thread(target=_scheduler_loop, daemon=True)
    _scheduler_thread.start()


def stop():
    global _running
    _running = False


def trigger_task(task_id: str) -> dict:
    """Manually trigger a task by ID. Used by /pepper/trigger endpoint."""
    all_tasks = _DAILY_TASKS + _WEEKLY_TASKS
    task = next((t for t in all_tasks if t["id"] == task_id), None)
    if not task:
        return {"ok": False, "error": f"Unknown task: {task_id}"}
    if _pepper_active:
        return {"ok": False, "error": "PEPPER is already running a task"}
    threading.Thread(target=_run_task, args=(task,), daemon=True).start()
    return {"ok": True, "message": f"Task '{task['name']}' dispatched to {task.get('agent','pepper')}"}


def status() -> dict:
    """Return PEPPER status for /pepper/status endpoint."""
    with _task_log_lock:
        log = list(_task_log)
    all_tasks = _DAILY_TASKS + _WEEKLY_TASKS
    return {
        "running": _running,
        "active": _pepper_active,
        "active_task": _active_task,
        "schedule": [
            {
                "id": t["id"],
                "name": t["name"],
                "agent": t.get("agent", "pepper"),
                "schedule": (f"Daily {t['hour']:02d}:00" if "hour" in t and "weekday" not in t
                             else f"{'Mon Tue Wed Thu Fri Sat Sun'.split()[t.get('weekday',0)]} {t.get('hour',0):02d}:00"),
                "ran_today": _already_ran_today(t["id"]),
            }
            for t in all_tasks
        ],
        "recent": log[:20],
    }


def get_all_tasks() -> list:
    return _DAILY_TASKS + _WEEKLY_TASKS
