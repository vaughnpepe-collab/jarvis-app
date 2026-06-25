#!/usr/bin/env python3
"""Seed the leads database with all prospected businesses."""
import json, re, datetime
from pathlib import Path

DATA = Path(__file__).parent / "data"
DATA.mkdir(exist_ok=True)
LEADS_FILE = DATA / "leads.json"

raw = [
    # ── Restaurants ──────────────────────────────────────────────────────────
    {"name": "Historia Meze & Grill",    "niche": "restaurant", "website": "https://historiamezegrill.co.uk/",    "phone": "+44 1494 533176", "score": 40, "flaws": ["slow load", "not mobile-responsive", "missing meta description", "no clear call-to-action"]},
    {"name": "Mezza House",              "niche": "restaurant", "website": None,                                   "phone": "+44 1494 445592", "score": 85, "flaws": ["Facebook only — no real website"]},
    {"name": "Caipirao",                 "niche": "restaurant", "website": "https://sitelift.site/caipiraosouthamericansteakhouse/", "phone": "+44 1494 441999", "score": 30, "flaws": ["missing meta description", "no clear call-to-action", "no Google Business linkage"]},
    {"name": "La Luna Ceylon",           "niche": "restaurant", "website": "https://www.instagram.com/laluna.ceylon/", "phone": "+44 1494 504278", "score": 30, "flaws": ["Instagram only — no real website"]},
    {"name": "DLuna Pao de Queijaria",   "niche": "restaurant", "website": "https://www.instagram.com/dlunapaodequeijaria/", "phone": None, "score": 30, "flaws": ["Instagram only — no real website"]},
    # ── Dentists ──────────────────────────────────────────────────────────────
    {"name": "Valley Dental Care",       "niche": "dentist",    "website": "http://valleydentalcare.co.uk/",      "phone": None,              "score": 40, "flaws": ["no HTTPS", "missing meta description", "no Google Business linkage"]},
    {"name": "Cressex Dental Practice",  "niche": "dentist",    "website": "https://www.cressexdental.com/",      "phone": None,              "score": 30, "flaws": ["slow load (6897ms)", "missing meta description", "no Google Business linkage"]},
    {"name": "Scandic Dental Care",      "niche": "dentist",    "website": "https://www.scandicdentalcare.co.uk/", "phone": "+44 1494 526566", "score": 20, "flaws": ["missing meta description", "no Google Business linkage"]},
    {"name": "The Willows Dental Surgery","niche": "dentist",   "website": "https://willowsdentalsurgery.com/",   "phone": "+44 1494 522368", "score": 20, "flaws": ["slow load", "no Google Business linkage"]},
    {"name": "JD Dental Care",           "niche": "dentist",    "website": "https://jddentalcare.co.uk/",         "phone": "+44 1494 528700", "score": 10, "flaws": ["no Google Business linkage"]},
    {"name": "Octagon Orthodontics",     "niche": "dentist",    "website": "https://octagonorthodontics.com/",    "phone": "+44 1494 513797", "score": 10, "flaws": ["missing meta description"]},
    {"name": "Enhance Dental",           "niche": "dentist",    "website": "https://enhancedental.co.uk/",        "phone": "+44 1494 524455", "score": 10, "flaws": ["no Google Business linkage"]},
    {"name": "Wycombe Dental Clinic",    "niche": "dentist",    "website": "https://wycombedentist.co.uk/",       "phone": "+44 1494 465241", "score": 10, "flaws": ["missing meta description"]},
    # ── Salons / Barbers / Nails ───────────────────────────────────────────────
    {"name": "Hair & Beauty Boutique",   "niche": "salon",      "website": None,                                   "phone": None,              "score": 88, "flaws": ["site down — needs new website"]},
    {"name": "Adils Cutting Edge",       "niche": "salon",      "website": None,                                   "phone": "+44 7765 950330", "score": 85, "flaws": ["Facebook only — no real website"]},
    {"name": "Brooklyn Nails",           "niche": "salon",      "website": None,                                   "phone": "+44 1494 458000", "score": 85, "flaws": ["Facebook only — no real website"]},
    {"name": "Kings Barbers",            "niche": "salon",      "website": None,                                   "phone": "+44 7552 184571", "score": 85, "flaws": ["Facebook only — no real website"]},
    {"name": "Moon's Nails",             "niche": "salon",      "website": None,                                   "phone": "+44 1494 436700", "score": 85, "flaws": ["Facebook only — no real website"]},
    {"name": "Love Nails",               "niche": "salon",      "website": "http://lovenailseden.co.uk/",          "phone": "+44 7476 182888", "score": 50, "flaws": ["no HTTPS", "missing meta description", "no CTA", "no Google Business"]},
    {"name": "Luxe Spa Land",            "niche": "salon",      "website": "https://myluxland.com/",               "phone": "+44 7732 359999", "score": 20, "flaws": ["missing meta description", "no Google Business linkage"]},
    {"name": "Adorn Beauty",             "niche": "salon",      "website": "https://highwycombe.adorn-beauty.com/", "phone": "+44 1494 535089", "score": 15, "flaws": ["verify manually"]},
    {"name": "Cutlers",                  "niche": "salon",      "website": "https://cutlers.edan.io/",             "phone": "+44 1494 452888", "score": 15, "flaws": ["verify manually"]},
]

leads = []
for b in raw:
    lid = b["niche"][:3].lower() + "_" + re.sub(r"[^a-z0-9]", "", b["name"].lower())[:20]
    leads.append({
        "id":       lid,
        "name":     b["name"],
        "niche":    b["niche"],
        "location": "High Wycombe, UK",
        "website":  b["website"],
        "phone":    b.get("phone"),
        "email":    "",
        "audit":    {"score": b["score"], "flaws": b["flaws"]},
        "score":    b["score"],
        "status":   "new",
        "added":    "2026-06-25",
        "notes":    "",
    })

LEADS_FILE.write_text(json.dumps(leads, indent=2))
print(f"Saved {len(leads)} leads to {LEADS_FILE}")

callables = sorted([l for l in leads if l.get("phone")], key=lambda x: -x["score"])
print(f"\nCALLABLE LEADS ({len(callables)}):")
for l in callables:
    print(f"  [{l['score']:3}] {l['name']:<35} {l['phone']:<22} {', '.join(l['audit']['flaws'])[:60]}")
