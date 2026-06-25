#!/usr/bin/env python3
"""
Outreach pipeline — ties together prospector → email queue → send → log.

Usage:
    python pipeline.py prospect  "dentist" "High Wycombe, UK"
    python pipeline.py review                        # show queued leads
    python pipeline.py send                          # send next batch (default 10)
    python pipeline.py followup                      # send follow-ups (5+ days old)
    python pipeline.py stats                         # show campaign stats
"""

import json
import os
import re
import sys
import time
import datetime
from pathlib import Path

# ── paths ────────────────────────────────────────────────────────────────────
ROOT = Path(__file__).parent.parent
DATA = ROOT / "outreach" / "data"
DATA.mkdir(exist_ok=True)
LEADS_FILE   = DATA / "leads.json"
LOG_FILE     = DATA / "sent_log.json"
QUEUE_FILE   = DATA / "queue.json"

YOUR_NAME    = os.environ.get("OUTREACH_NAME",  "Vaughn")
YOUR_PHONE   = os.environ.get("OUTREACH_PHONE", "07XXX XXX XXX")
YOUR_EMAIL   = os.environ.get("OUTREACH_EMAIL", "vaughnpepe@gmail.com")
PORTFOLIO    = os.environ.get("PORTFOLIO_URL",  "https://hwwebdesign.co.uk")

# ── data helpers ─────────────────────────────────────────────────────────────
def _load(path, default):
    if path.exists():
        return json.loads(path.read_text())
    return default

def _save(path, data):
    path.write_text(json.dumps(data, indent=2))


def load_leads():   return _load(LEADS_FILE, [])
def load_log():     return _load(LOG_FILE,   [])
def load_queue():   return _load(QUEUE_FILE, [])

def save_leads(d):  _save(LEADS_FILE, d)
def save_log(d):    _save(LOG_FILE,   d)
def save_queue(d):  _save(QUEUE_FILE, d)


# ── email builders ────────────────────────────────────────────────────────────
def _subject_no_site(name):
    return f"Quick question about {name}"

def _subject_bad_site(name):
    return f"Your website — a quick thought ({name})"

def _body_no_site(name, niche):
    return f"""Hi there,

I was looking for a {niche} in High Wycombe and noticed {name} doesn't have a website yet.

I build websites for local businesses in the area — clean, professional, and fast to get live. A basic site starts from £399 and is usually live within a week.

Here's a look at my recent work: {PORTFOLIO}

Happy to have a no-pressure chat if you're interested — or I can send over a free mockup tailored to {name}.

Best,
{YOUR_NAME}
{YOUR_PHONE}
{YOUR_EMAIL}
"""

def _body_bad_site(name, niche, flaws):
    flaw_text = flaws[0] if flaws else "could use some improvements"
    return f"""Hi there,

I came across {name} online — great business, but I noticed your website {flaw_text}.

I build modern, mobile-friendly websites for local businesses in High Wycombe starting from £399. Most clients see more enquiries within the first month.

Here's a demo of the kind of thing I'd build for you: {PORTFOLIO}

Worth a quick call? No obligation at all.

Best,
{YOUR_NAME}
{YOUR_PHONE}
{YOUR_EMAIL}
"""

def _body_followup(name):
    return f"""Hi again,

Just following up on my message from a few days ago in case it got lost.

I build websites for local businesses in High Wycombe — simple process, fair prices, most sites live within a week.

If you'd like a free mockup for {name}, just reply here or call {YOUR_PHONE}.

Best,
{YOUR_NAME}
"""

def _subject_followup(name):
    return f"Re: {name} website"


def build_email(lead):
    """Return (to, subject, body) for a lead dict."""
    name    = lead.get("name", "your business")
    niche   = lead.get("niche", "business")
    email   = lead.get("email", "")
    flaws   = lead.get("audit", {}).get("flaws", [])
    has_site = bool(lead.get("website"))

    if has_site:
        subj = _subject_bad_site(name)
        body = _body_bad_site(name, niche, flaws)
    else:
        subj = _subject_no_site(name)
        body = _body_no_site(name, niche)

    return email, subj, body


def build_followup(lead):
    name  = lead.get("name", "your business")
    email = lead.get("email", "")
    return email, _subject_followup(name), _body_followup(name)


# ── prospect command ──────────────────────────────────────────────────────────
def cmd_prospect(niche, location, limit=30):
    sys.path.insert(0, str(ROOT))
    from prospector import find_unoptimized

    print(f"\n  Prospecting {niche}s in {location} ...")
    data = find_unoptimized(niche, location, int(limit))

    leads = load_leads()
    existing_names = {l["name"] for l in leads}
    added = 0

    for b in data["results"]:
        if b["name"] in existing_names:
            continue
        lead = {
            "id":       f"{niche[:3].lower()}_{re.sub(r'[^a-z0-9]','',b['name'].lower())[:20]}",
            "name":     b["name"],
            "niche":    niche,
            "location": location,
            "website":  b.get("website"),
            "phone":    b.get("phone"),
            "address":  b.get("address"),
            "email":    b.get("email", ""),
            "audit":    b.get("audit", {}),
            "score":    b.get("audit", {}).get("score", 0),
            "status":   "new",
            "added":    datetime.date.today().isoformat(),
            "notes":    "",
        }
        leads.append(lead)
        existing_names.add(b["name"])
        added += 1

    save_leads(leads)
    print(f"  Added {added} new leads  (total: {len(leads)})")
    print(f"  Data: {LEADS_FILE}")

    # auto-queue new leads that have email addresses OR phone numbers
    queueable = [l for l in leads if l["status"] == "new" and (l.get("email") or l.get("phone"))]
    print(f"\n  {len(queueable)} lead(s) ready to contact (email or phone known)")
    print(f"  Top 5 targets:")
    for l in sorted(queueable, key=lambda x: -x["score"])[:5]:
        print(f"    [{l['score']:3}] {l['name']}  |  {l.get('phone','')}  |  flaws: {', '.join(l['audit'].get('flaws',[]))[:80]}")


# ── review command ────────────────────────────────────────────────────────────
def cmd_review():
    leads = load_leads()
    by_status = {}
    for l in leads:
        by_status.setdefault(l["status"], []).append(l)

    print(f"\n  {'='*60}")
    print(f"  LEAD SUMMARY  —  {len(leads)} total")
    print(f"  {'='*60}")
    for status, grp in sorted(by_status.items()):
        print(f"\n  {status.upper()} ({len(grp)})")
        for l in sorted(grp, key=lambda x: -x["score"])[:8]:
            print(f"    [{l['score']:3}] {l['name']:<35} {l.get('phone',''):<18} {l.get('email','')}")
    print()


# ── queue management ──────────────────────────────────────────────────────────
def cmd_queue_emails(limit=10):
    """Stage next N new leads with known emails into the send queue."""
    leads = load_leads()
    queue = load_queue()
    queued_ids = {q["lead_id"] for q in queue}

    staged = 0
    for l in sorted(leads, key=lambda x: -x["score"]):
        if staged >= int(limit):
            break
        if l["status"] != "new":
            continue
        if l["id"] in queued_ids:
            continue
        if not l.get("email"):
            continue
        to, subj, body = build_email(l)
        queue.append({
            "lead_id": l["id"],
            "to":      to,
            "subject": subj,
            "body":    body,
            "type":    "initial",
            "queued":  datetime.datetime.now().isoformat(),
            "sent":    None,
        })
        queued_ids.add(l["id"])
        staged += 1

    save_queue(queue)
    pending = [q for q in queue if not q["sent"]]
    print(f"  Staged {staged} new email(s).  Queue: {len(pending)} pending.")


# ── stats command ─────────────────────────────────────────────────────────────
def cmd_stats():
    leads = load_leads()
    log   = load_log()
    queue = load_queue()

    total     = len(leads)
    emailed   = len([l for l in leads if l["status"] in ("emailed","called","meeting","closed","lost")])
    called    = len([l for l in leads if l["status"] in ("called","meeting","closed")])
    meetings  = len([l for l in leads if l["status"] in ("meeting","closed")])
    closed    = len([l for l in leads if l["status"] == "closed"])
    revenue   = sum(l.get("deal_value", 0) for l in leads if l["status"] == "closed")
    pending_q = len([q for q in queue if not q["sent"]])

    print(f"""
  ╔══════════════════════════════════════╗
  ║       7-DAY £500 CHALLENGE           ║
  ╠══════════════════════════════════════╣
  ║  Leads found      : {total:<17}║
  ║  Emailed          : {emailed:<17}║
  ║  Called           : {called:<17}║
  ║  Meetings booked  : {meetings:<17}║
  ║  CLOSED           : {closed:<17}║
  ║  REVENUE          : £{revenue:<16}║
  ╠══════════════════════════════════════╣
  ║  Emails in queue  : {pending_q:<17}║
  ╚══════════════════════════════════════╝
    """)
    if revenue >= 500:
        print("  🎯 GOAL REACHED!")
    else:
        gap = 500 - revenue
        closes_needed = -(-gap // 399)  # ceiling div
        print(f"  £{gap} to go — {closes_needed} more close(s) needed")
    print()


# ── update lead status ────────────────────────────────────────────────────────
def cmd_update(lead_name, new_status, deal_value=0):
    """Mark a lead's status. Statuses: emailed called meeting closed lost"""
    leads = load_leads()
    for l in leads:
        if lead_name.lower() in l["name"].lower():
            l["status"] = new_status
            if deal_value:
                l["deal_value"] = int(deal_value)
            l["updated"] = datetime.date.today().isoformat()
            save_leads(leads)
            print(f"  Updated '{l['name']}' → {new_status}" +
                  (f" (£{deal_value})" if deal_value else ""))
            return
    print(f"  Lead matching '{lead_name}' not found.")


# ── print send-ready emails (for copy/paste or gmail integration) ─────────────
def cmd_send(limit=10):
    """Print next N queued emails ready to send (paste or hook into Gmail)."""
    queue = load_queue()
    pending = [q for q in queue if not q["sent"]][:int(limit)]

    if not pending:
        print("  No emails queued. Run:  python pipeline.py queue")
        return

    leads  = {l["id"]: l for l in load_leads()}
    log    = load_log()

    for i, q in enumerate(pending, 1):
        lead = leads.get(q["lead_id"], {})
        print(f"\n{'─'*60}")
        print(f"  Email {i}/{len(pending)}: {lead.get('name','?')}")
        print(f"  To:      {q['to'] or '⚠ NO EMAIL — use phone: ' + lead.get('phone','?')}")
        print(f"  Subject: {q['subject']}")
        print(f"  ─ ─ ─")
        print(q["body"])

        # mark as "ready" so we know it's been reviewed
        q["sent"]    = datetime.datetime.now().isoformat()
        q["method"]  = "printed_for_manual_send"

        # update lead status
        if lead.get("id"):
            for l in load_leads():
                if l["id"] == lead["id"]:
                    l["status"] = "emailed"
                    l["last_contact"] = datetime.date.today().isoformat()
            save_leads(load_leads())

        log.append({"lead_id": q["lead_id"], "type": q["type"],
                    "sent": q["sent"], "to": q["to"]})

    save_queue(queue)
    save_log(log)
    print(f"\n  {len(pending)} email(s) printed. Copy each and send from your email client.")
    print(f"  Log saved: {LOG_FILE}")


# ── followup command ──────────────────────────────────────────────────────────
def cmd_followup():
    leads = load_leads()
    log   = load_log()
    today = datetime.date.today()

    for l in leads:
        if l["status"] != "emailed":
            continue
        last = l.get("last_contact")
        if not last:
            continue
        days_ago = (today - datetime.date.fromisoformat(last)).days
        if days_ago < 5:
            continue
        to, subj, body = build_followup(l)
        print(f"\n{'─'*60}")
        print(f"  FOLLOW-UP ({days_ago}d): {l['name']}")
        print(f"  To:      {to or '⚠ NO EMAIL'}")
        print(f"  Subject: {subj}")
        print(f"  ─ ─ ─")
        print(body)
        l["status"] = "followed_up"
        l["last_contact"] = today.isoformat()

    save_leads(leads)


# ── daily action plan ─────────────────────────────────────────────────────────
def cmd_plan():
    leads = load_leads()
    today = datetime.date.today()
    day   = (today - datetime.date(2026, 6, 25)).days + 1  # challenge day 1 = June 25

    print(f"\n  ═══ DAY {day} ACTION PLAN  ({today}) ═══\n")

    new_leads = [l for l in leads if l["status"] == "new"]
    emailed   = [l for l in leads if l["status"] == "emailed"]
    closed    = [l for l in leads if l["status"] == "closed"]
    revenue   = sum(l.get("deal_value", 0) for l in closed)

    print(f"  PRIORITY ACTIONS:")
    print(f"  1. Phone calls  — target {max(0, 10 - len(closed)*3)} calls today")
    print(f"     Best prospects to call:")
    callable_leads = [l for l in leads if l.get("phone") and l["status"] in ("new","emailed","followed_up")]
    for l in sorted(callable_leads, key=lambda x: -x["score"])[:5]:
        print(f"     • {l['name']:<35} {l.get('phone',''):<20} score={l['score']}")

    print(f"\n  2. Email outreach — {len(new_leads)} new leads with emails to send")
    print(f"  3. Follow-ups — {len(emailed)} emailed leads to chase")

    print(f"\n  REVENUE: £{revenue} / £500 target")
    if revenue >= 1000:
        print("  🏆 £1,000 SMASHED!")
    elif revenue >= 500:
        print("  🎯 £500 GOAL HIT!  Push for £1,000!")
    else:
        closes_needed = -(-( 500 - revenue) // 399)
        print(f"  Need {closes_needed} more close(s) — keep dialling!\n")


# ── main ──────────────────────────────────────────────────────────────────────
COMMANDS = {
    "prospect": lambda *a: cmd_prospect(*a),
    "review":   lambda *a: cmd_review(),
    "queue":    lambda *a: cmd_queue_emails(a[0] if a else 10),
    "send":     lambda *a: cmd_send(a[0] if a else 10),
    "followup": lambda *a: cmd_followup(),
    "stats":    lambda *a: cmd_stats(),
    "update":   lambda *a: cmd_update(*a),
    "plan":     lambda *a: cmd_plan(),
}

if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        print(__doc__)
        print("  Commands:", ", ".join(COMMANDS))
        sys.exit(1)
    cmd  = sys.argv[1]
    args = sys.argv[2:]
    COMMANDS[cmd](*args)
