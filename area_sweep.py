#!/usr/bin/env python3
"""
HW Web Design — Area Lead Sweep.

One command that turns the prospector into a ready-to-work sales pipeline:

  1. SOURCE  every business across your niches x towns (OpenStreetMap, keyless;
             Google Places if GOOGLE_PLACES_KEY is set — far better coverage).
  2. AUDIT   each site for real, on-page flaws (HTTPS, mobile, speed, SEO, CTA).
             Businesses with NO website are kept too — they're the easiest sale.
  3. BUCKET  by how actionable each lead is (callable + verifiable first).
  4. WRITE   leads/leads_<area>.csv      — every business, full flaw detail
             leads/leads_<area>.md       — the call sheet, worst sites first
             leads/outreach_pack_<area>.md — personalised opener + email per lead

Usage:
    python area_sweep.py                 # default: local towns + niches
    python area_sweep.py --towns "Reading, UK;Slough, UK" --niches "dentist;gym"

Tip: set GOOGLE_PLACES_KEY for 5-10x more businesses with phone numbers.
"""
import argparse
import csv
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import prospector as p

DEFAULT_TOWNS = ["High Wycombe, UK", "Marlow, UK", "Beaconsfield, UK", "Amersham, UK"]
DEFAULT_NICHES = ["restaurant", "salon", "dentist", "plumber", "electrician",
                  "gym", "roofer", "vet", "accountant"]
PER = 30
SLEEP = 1.3  # be polite to the free OSM endpoints (~1 req/sec policy)

SHAKY = ("unreachable", "returns http", "blocked automated", "audit error")
SIGNATURE = "Vaughn\nHW Web Design · 07XXX XXX XXX · hwwebdesign.co.uk"

# flaw fragment -> (short phrase for a call, customer-impact line for an email)
IMPACT = {
    "no HTTPS": ("isn't showing as secure",
                 "it isn't showing as secure (no padlock), which makes browsers warn "
                 "people off and pushes you down Google's rankings"),
    "not mobile-responsive": ("doesn't work well on phones",
                 "it doesn't display properly on phones, where most of your customers "
                 "are searching"),
    "missing/empty title tag": ("is missing its Google title",
                 "the page is missing a proper title, one of the first things Google "
                 "uses to decide where you rank"),
    "missing meta description": ("looks bare in Google results",
                 "there's no description for Google to show under your listing, so you "
                 "look less appealing than competitors in the search results"),
    "slow load": ("loads slowly",
                 "it's slow to load, and a lot of visitors give up if a site takes more "
                 "than about three seconds"),
    "no clear call-to-action": ("has no obvious 'call' or 'book' button",
                 "there's no clear 'call now' or 'book' button, so interested visitors "
                 "don't have an easy next step"),
    "no Google Business linkage": ("isn't tied into Google Business",
                 "it isn't linked to your Google Business listing, which is how most "
                 "locals will actually find you"),
}


def key_for(b):
    site = (b.get("website") or "").lower().strip("/")
    site = site.replace("https://", "").replace("http://", "").replace("www.", "")
    return site or ("name:" + (b.get("name") or "").lower().strip())


def is_verified(flaws):
    fl = " ".join(flaws).lower()
    return not any(s in fl for s in SHAKY)


def sweep(towns, niches):
    leads = {}
    for town in towns:
        for niche in niches:
            try:
                businesses, src = p.source(niche, town, PER)
            except Exception as ex:
                print(f"  ! {niche}/{town}: {ex}")
                time.sleep(SLEEP)
                continue
            with_site = [b for b in businesses if b.get("website")]
            with ThreadPoolExecutor(max_workers=8) as pool:
                fut = {pool.submit(p.audit_site, b["website"]): b for b in with_site}
                for f in as_completed(fut):
                    b = fut[f]
                    try:
                        b["audit"] = f.result()
                    except Exception as ex:
                        b["audit"] = {"score": 80, "flaws": [f"audit error: {ex}"]}
            for b in businesses:
                if not b.get("website"):
                    b["audit"] = {"score": 99, "flaws": ["no website at all"], "url": None}
                k = key_for(b)
                if k in leads and leads[k]["audit"]["score"] >= b["audit"]["score"]:
                    continue
                b["_niche"], b["_town"] = niche, town.split(",")[0]
                leads[k] = b
            nosite = sum(1 for b in businesses if not b.get("website"))
            print(f"  · {niche:11} / {town:22} -> {len(businesses):2} found, "
                  f"{nosite:2} no-site  [{src}]")
            time.sleep(SLEEP)
    return list(leads.values())


def classify(rows):
    for r in rows:
        a = r["audit"]
        r["_phone"] = bool(r.get("phone"))
        r["_nosite"] = "no website at all" in a["flaws"]
        r["_verified"] = is_verified(a["flaws"])
    hot = [r for r in rows if r["_nosite"] and r["_phone"]]
    warm = [r for r in rows if r["_verified"] and not r["_nosite"] and r["_phone"]]
    verify = [r for r in rows if not r["_verified"] and r["_phone"]]
    nophone = [r for r in rows if r["_nosite"] and not r["_phone"]]
    hot.sort(key=lambda r: (r["_town"], r["name"]))
    warm.sort(key=lambda r: -r["audit"]["score"])
    verify.sort(key=lambda r: -r["audit"]["score"])
    return hot, warm, verify, nophone


def write_csv(path, rows):
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["score", "name", "niche", "town", "phone", "website",
                    "verified_flaw", "flaws"])
        for r in sorted(rows, key=lambda r: -r["audit"]["score"]):
            a = r["audit"]
            w.writerow([a["score"], r["name"], r["_niche"], r["_town"],
                        r.get("phone") or "", r.get("website") or "",
                        "yes" if r["_verified"] else "verify", "; ".join(a["flaws"])])


def _table(items, n=80):
    out = ["| # | Business | Niche | Town | Phone | What's wrong (your angle) |",
           "|---|----------|-------|------|-------|---------------------------|"]
    for i, r in enumerate(items[:n], 1):
        out.append(f"| {i} | **{r['name']}** | {r['_niche']} | {r['_town']} "
                   f"| {r.get('phone') or '—'} | {', '.join(r['audit']['flaws'])} |")
    return "\n".join(out)


def write_callsheet(path, area, hot, warm, verify, nophone, total):
    md = f"""# HW Web Design — Lead List ({area})

_Generated {time.strftime('%Y-%m-%d')} from live OpenStreetMap + on-page website audits._

| Bucket | Count | What it means |
|--------|------:|---------------|
| 🟢 No website + phone | {len(hot)} | Easiest sale. They have nothing — you offer everything. |
| 🟡 Has a site, real flaws + phone | {len(warm)} | Flaws read from the live page — quote them with confidence. |
| 🔵 Verify first + phone | {len(verify)} | Checker couldn't load the site (maybe down, maybe blocking us). |
| ⚪ No website, no phone listed | {len(nophone)} | Strong prospects — look up their number on Google/Facebook. |

**Pitch:** free mockup, no obligation · £399 start · live within a week ·
portfolio at hwwebdesign.co.uk. Work each list top-down.

---

## 🟢 NO WEBSITE + phone — call these first ({len(hot)})
{_table(hot)}

---

## 🟡 Has a website with real, verifiable flaws + phone ({len(warm)})
_Every flaw below was read from the actual page, so you can mention it on the call._

{_table(warm)}

---

## 🔵 Verify first, then call ({len(verify)})
_Open each on your phone before ringing — if it genuinely won't load, that's your pitch._

{_table(verify)}

---

## ⚪ No website, no phone in our data ({len(nophone)})
{_table(nophone)}

---

_Full data with every flaw: the matching `leads_*.csv`. Re-run: `python area_sweep.py`._
"""
    with open(path, "w") as f:
        f.write(md)


def _impacts(flaws):
    return [v for k, v in IMPACT.items() if k in flaws]


def write_outreach(path, area, hot, warm):
    out = [f"""# HW Web Design — Outreach Pack ({area})

Personalised opener + email for your top callable leads, built from the live
audit. **Swap in** your real phone number (placeholder `07XXX XXX XXX`) and your
name if it isn't *Vaughn*. Channel is phone-first; for email, grab each
business's address from their Google/Facebook page.

---

## 🟢 No-website leads
"""]
    for r in hot:
        b, niche, town = r["name"], r["_niche"], r["_town"]
        out.append(f"""### {b} — {niche}, {town}  ·  📞 {r['phone']}

**Call opener:**
> "Hi, is that {b}? My name's Vaughn — I'm a web designer based locally in {town}.
> I'll keep this quick: I noticed {b} doesn't have a website yet, and I build
> sites for local businesses in the area. Open to a quick chat about it?"

**Email** *(once you have their address)*
**Subject:** Quick question about {b}

Hi there,

I was looking for a {niche} in {town} and noticed {b} doesn't have a website yet.
A simple, professional site would help people find you on Google, see what you
offer, and get in touch — without every enquiry having to be a phone call.

I build clean, fast websites for local businesses around High Wycombe from £399,
usually live within a week. Some of my work: https://hwwebdesign.co.uk

I'm happy to put together a **free mockup for {b} specifically** — no cost, no
obligation. Worth a quick chat?

Best,
{SIGNATURE}

---
""")
    out.append("## 🟡 Has-a-website leads (real flaws to quote)\n")
    for r in warm[:20]:
        b, niche, town = r["name"], r["_niche"], r["_town"]
        flaws = ", ".join(r["audit"]["flaws"])
        imp = _impacts(flaws)
        short = imp[0][0] if imp else "could do with a refresh"
        if len(imp) >= 2:
            line = f"{imp[0][1]}, and {imp[1][1]}"
        elif imp:
            line = imp[0][1]
        else:
            line = "a few things that are likely costing you enquiries"
        out.append(f"""### {b} — {niche}, {town}  ·  📞 {r['phone']}
_Audit found: {flaws}_

**Call opener:**
> "Hi, is that {b}? My name's Vaughn, I'm a local web designer in High Wycombe —
> I'll be quick. I had a look at your website and noticed it {short}. I build
> modern sites for local {niche}s that sort exactly that out. Open to a quick chat?"

**Email** *(once you have their address)*
**Subject:** A quick thought about {b}'s website

Hi there,

I came across {b} while looking for a {niche} in {town}. I had a quick look at
your website and noticed a couple of things that might quietly be costing you
customers — {line}.

I build fast, modern, mobile-friendly websites for local businesses around High
Wycombe. Prices start at £399 and most sites are live within a week — some of my
work: https://hwwebdesign.co.uk

If it'd help, I'll put together a **free mockup** of what {b}'s new site could
look like — no cost, no obligation. Worth a quick chat?

Best,
{SIGNATURE}

---
""")
    with open(path, "w") as f:
        f.write("\n".join(out))


def main():
    ap = argparse.ArgumentParser(description="HW Web Design area lead sweep")
    ap.add_argument("--towns", help='semicolon-separated, e.g. "Reading, UK;Slough, UK"')
    ap.add_argument("--niches", help='semicolon-separated, e.g. "dentist;gym"')
    args = ap.parse_args()
    towns = [t.strip() for t in args.towns.split(";")] if args.towns else DEFAULT_TOWNS
    niches = [n.strip() for n in args.niches.split(";")] if args.niches else DEFAULT_NICHES

    area = towns[0].split(",")[0] if len(towns) == 1 else "High Wycombe & area"
    slug = area.lower().replace(" & ", "_").replace(" ", "_")
    os.makedirs("leads", exist_ok=True)

    print(f"\nSweeping {len(niches)} niches x {len(towns)} towns "
          f"({'Google Places' if p.PLACES_KEY else 'OpenStreetMap'})...\n")
    rows = sweep(towns, niches)
    hot, warm, verify, nophone = classify(rows)

    csv_path = f"leads/leads_{slug}.csv"
    md_path = f"leads/leads_{slug}.md"
    pack_path = f"leads/outreach_pack_{slug}.md"
    write_csv(csv_path, rows)
    write_callsheet(md_path, area, hot, warm, verify, nophone, len(rows))
    write_outreach(pack_path, area, hot, warm)

    print(f"\n  {len(rows)} businesses  |  🟢 {len(hot)} no-site+phone  "
          f"🟡 {len(warm)} flaws+phone  🔵 {len(verify)} verify  ⚪ {len(nophone)} no-phone")
    print(f"  -> {md_path}\n  -> {pack_path}\n  -> {csv_path}\n")


if __name__ == "__main__":
    main()
