#!/usr/bin/env python3
"""
HW Web Design — Prepare email drafts.

Takes the enriched emails (leads/lead_emails.csv), drops junk addresses, makes
sure every lead has a mockup, and writes ready-to-create email drafts:
  leads/email_drafts.json  — machine-readable (to / subject / body) for Gmail
  leads/email_drafts.md    — human-readable, review before anything is sent

Nothing is sent. Drafts are created separately and reviewed by you first.
"""
import csv
import json
import os

import mockup_gen
from area_sweep import lead_slug, BASE_URL, IMPACT, _impacts, SIGNATURE
from enrich_emails import reject

EMAILS = "leads/lead_emails.csv"
MAIN = "leads/leads_high_wycombe_area.csv"


def flaws_by_key():
    m = {}
    with open(MAIN) as f:
        for r in csv.DictReader(f):
            m[(r["name"], r["town"])] = r.get("flaws", "").replace("; ", ", ")
    return m


def ensure_mockup(b):
    slug = lead_slug(b["name"], b["town"])
    d = os.path.join("mockups", slug)
    path = os.path.join(d, "index.html")
    if not os.path.exists(path):
        os.makedirs(d, exist_ok=True)
        with open(path, "w") as f:
            f.write(mockup_gen.render(b))
        return slug, True
    return slug, False


def art(noun):
    return "an" if noun[:1].lower() in "aeiou" else "a"


def impact_line(flaws):
    imp = _impacts(flaws)
    if len(imp) >= 2:
        return f"{imp[0][1]}, and {imp[1][1]}"
    if imp:
        return imp[0][1]
    return "a few things that are likely quietly costing you enquiries"


def main():
    flaws = flaws_by_key()
    drafts, made = [], 0
    with open(EMAILS) as f:
        rows = list(csv.DictReader(f))

    for r in rows:
        email = (r.get("email") or "").strip()
        if not email or reject(email):
            continue
        name, niche, town = r["name"], r["niche"], r["town"]
        slug, created = ensure_mockup(r)
        made += created
        url = f"{BASE_URL}/mockups/{slug}/"
        line = impact_line(flaws.get((name, town), ""))
        subject = f"A fresh look for {name}'s website (free mockup)"
        body = (
            f"Hi there,\n\n"
            f"I came across {name} while looking for {art(niche)} {niche} in {town}. I had a "
            f"quick look at your website and noticed a couple of things that might "
            f"quietly be costing you customers — {line}.\n\n"
            f"So I put together a free mockup of how a refreshed version could look:\n"
            f"{url}\n\n"
            f"I build fast, modern, mobile-friendly sites for local businesses around "
            f"High Wycombe from £399, usually live within a week. No cost or obligation "
            f"for the mockup — if you like the direction, we take it from there. Worth a "
            f"quick chat?\n\n"
            f"Best,\n{SIGNATURE}"
        )
        drafts.append({"to": email, "subject": subject, "body": body,
                       "name": name, "niche": niche, "town": town, "mockup": url})

    with open("leads/email_drafts.json", "w") as f:
        json.dump(drafts, f, indent=2)

    md = ["# HW Web Design — Email Drafts (review before sending)",
          "",
          f"{len(drafts)} drafts ready. Each is also being created in your Gmail as a "
          f"**draft** (nothing is sent). Review, swap in your real phone number, then "
          f"send the ones you're happy with.",
          ""]
    for d in drafts:
        md += [f"## {d['name']} — {d['niche']}, {d['town']}",
               f"**To:** {d['to']}  ", f"**Subject:** {d['subject']}  ",
               f"**Mockup:** {d['mockup']}", "", "```", d["body"], "```", ""]
    with open("leads/email_drafts.md", "w") as f:
        f.write("\n".join(md))

    print(f"{len(drafts)} drafts prepared (generated {made} new mockups).")
    print("  -> leads/email_drafts.json\n  -> leads/email_drafts.md")
    for d in drafts:
        print(f"   • {d['to']:38} {d['name']}")


if __name__ == "__main__":
    main()
