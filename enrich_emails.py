#!/usr/bin/env python3
"""
HW Web Design — Email Enrichment.

For leads that have a reachable website, fetch the homepage (and likely contact
page) and extract a contact email address, so you can work email alongside the
phone. Pairs with the mockups: a found email + a ready mockup link = a complete
draft.

Usage:
    python enrich_emails.py                      # default area CSV, warm leads
    python enrich_emails.py leads/leads_x.csv

Writes leads/lead_emails.csv (name, niche, town, phone, website, email, mockup).
"""
import csv
import re
import sys
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed

import prospector as p
from area_sweep import lead_slug, BASE_URL, WARM_LIMIT

ENRICH_LIMIT = 45  # how many reachable leads to attempt
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
# noise that shows up in page source but isn't a real contact address
JUNK = ("sentry", "wixpress", "example.", "@2x", "@3x", "godaddy", "yourname",
        "your@email", "email@", "@sentry", "domain.com", "squarespace", "cloudflare",
        ".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", "u003e", "core@", "@adobe")
# placeholder / role addresses that aren't a real owner contact
BAD_LOCAL = ("test", "noreply", "no-reply", "donotreply", "do-not-reply", "postmaster",
             "abuse", "privacy", "webmaster", "mailer-daemon", "root", "user", "name")
BAD_DOMAIN = ("mail.com", "email.com", "test.com", "domain.com", "example.com",
              "yourdomain.com", "company.com")
PREFERRED = ("info@", "hello@", "contact@", "enquiries@", "enquiry@", "bookings@",
             "reception@", "admin@", "sales@", "office@", "mail@")


VALID_TLD = ("com", "uk", "org", "net", "io", "me", "eu", "biz", "info", "co",
             "shop", "store", "online", "life", "club", "pub", "cafe", "agency",
             "studio", "salon", "dental", "clinic", "fitness", "design")


def reject(email):
    el = email.lower()
    local, _, dom = el.partition("@")
    if local in BAD_LOCAL or dom in BAD_DOMAIN:
        return True
    tld = dom.rsplit(".", 1)[-1]
    return tld not in VALID_TLD


def domain_of(url):
    try:
        net = urllib.parse.urlparse(url if "//" in url else "//" + url).netloc.lower()
        return net.replace("www.", "")
    except Exception:
        return ""


def emails_from_html(html):
    found = set()
    # mailto links first (most reliable)
    for m in re.finditer(r'mailto:([^"\'?>\s]+)', html, re.I):
        found.add(m.group(1).strip())
    for m in EMAIL_RE.finditer(html):
        found.add(m.group(0).strip())
    out = []
    for e in found:
        el = e.lower()
        if any(j in el for j in JUNK):
            continue
        if len(el) > 60 or el.count("@") != 1:
            continue
        if reject(e):
            continue
        out.append(e)
    return out


def best_email(candidates, site_domain):
    if not candidates:
        return ""
    def rank(e):
        el = e.lower()
        same = site_domain and site_domain.split(".")[0] in el  # matches the brand
        pref = next((i for i, pre in enumerate(PREFERRED) if el.startswith(pre)), 99)
        free = any(d in el for d in ("gmail.", "hotmail.", "outlook.", "yahoo.", "icloud."))
        return (0 if same else 1, pref, 1 if free else 0, len(el))
    return sorted(candidates, key=rank)[0]


def find_email(website):
    if not website:
        return ""
    site_domain = domain_of(website)
    pages, html0 = [], None
    for attempt in ([website, "https://" + website] if "//" not in website else [website]):
        try:
            html0, _, final = p._get(attempt, headers=p.BROWSER_HEADERS, timeout=12)
            pages.append(html0)
            # discover a contact page on the same site
            for m in re.finditer(r'href=["\']([^"\']*contact[^"\']*)["\']', html0, re.I):
                link = m.group(1)
                if link.startswith("#") or "mailto" in link:
                    continue
                full = urllib.parse.urljoin(final, link)
                if domain_of(full) == site_domain:
                    pages.append(full)
            break
        except Exception:
            continue
    if html0 is None:
        return ""
    # fetch up to 2 discovered contact pages
    extra = [x for x in pages[1:3] if isinstance(x, str) and x.startswith("http")]
    for url in extra:
        try:
            h, _, _ = p._get(url, headers=p.BROWSER_HEADERS, timeout=10)
            pages.append(h)
        except Exception:
            pass
    cands = []
    for h in pages:
        if isinstance(h, str) and ("@" in h):
            cands += emails_from_html(h)
    return best_email(list(dict.fromkeys(cands)), site_domain)


def load_warm(csv_path):
    rows = []
    with open(csv_path) as f:
        for r in csv.DictReader(f):
            r["phone"] = (r.get("phone") or "").strip()
            r["nosite"] = "no website at all" in r.get("flaws", "")
            r["verified"] = r.get("verified_flaw") == "yes"
            rows.append(r)
    warm = [r for r in rows if r["verified"] and not r["nosite"] and r.get("website")]
    warm.sort(key=lambda r: -int(r.get("score") or 0))
    return warm[:ENRICH_LIMIT]


def main():
    csv_path = sys.argv[1] if len(sys.argv) > 1 else "leads/leads_high_wycombe_area.csv"
    warm = load_warm(csv_path)
    print(f"Enriching {len(warm)} reachable leads for contact emails...\n")
    results = []
    with ThreadPoolExecutor(max_workers=8) as pool:
        fut = {pool.submit(find_email, r["website"]): r for r in warm}
        for f in as_completed(fut):
            r = fut[f]
            try:
                r["email"] = f.result()
            except Exception:
                r["email"] = ""
            results.append(r)
    results.sort(key=lambda r: (r["email"] == "", -int(r.get("score") or 0)))

    out = "leads/lead_emails.csv"
    with open(out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["name", "niche", "town", "phone", "email", "website", "mockup_url"])
        for r in results:
            w.writerow([r["name"], r["niche"], r["town"], r["phone"], r.get("email", ""),
                        r["website"], f"{BASE_URL}/mockups/{lead_slug(r['name'], r['town'])}/"])

    got = [r for r in results if r.get("email")]
    print(f"Found emails for {len(got)}/{len(results)} leads -> {out}\n")
    for r in got:
        print(f"  ✓ {r['email']:38} {r['name']} ({r['town']})")
    miss = [r for r in results if not r.get("email")]
    if miss:
        print(f"\n  (no email found for {len(miss)}: " +
              ", ".join(r["name"] for r in miss[:10]) + ")")


if __name__ == "__main__":
    main()
