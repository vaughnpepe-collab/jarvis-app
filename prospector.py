#!/usr/bin/env python3
"""
J.A.R.V.I.S. Prospector — find local businesses with "unoptimized" websites.

Pipeline:
  1. SOURCE   businesses in a niche + location (OpenStreetMap/Overpass, keyless;
              optional Google Places if GOOGLE_PLACES_KEY is set).
  2. AUDIT    each site with fast keyless checks (HTTPS, load time, mobile
              viewport, meta title/description, call-to-action, GBP hint).
  3. RANK     worst site first — that gap is the selling point.

Stdlib only. CLI:  python prospector.py "dentist" "Austin, TX" [limit]
"""

import json
import os
import re
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

BROWSER_HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

UA = "JARVIS-Prospector/1.0 (local research tool)"
PLACES_KEY = os.environ.get("GOOGLE_PLACES_KEY", "").strip()
_CTX = ssl.create_default_context()

# niche keyword -> OpenStreetMap tag filters (Overpass)
NICHE_TAGS = {
    "dentist":   ['["amenity"="dentist"]', '["healthcare"="dentist"]'],
    "plumber":   ['["craft"="plumber"]', '["shop"="trade"]["trade"="plumber"]'],
    "lawyer":    ['["office"="lawyer"]'],
    "law firm":  ['["office"="lawyer"]'],
    "doctor":    ['["amenity"="doctors"]', '["healthcare"="doctor"]'],
    "restaurant":['["amenity"="restaurant"]'],
    "electrician":['["craft"="electrician"]'],
    "roofer":    ['["craft"="roofer"]'],
    "accountant":['["office"="accountant"]'],
    "vet":       ['["amenity"="veterinary"]'],
    "veterinarian":['["amenity"="veterinary"]'],
    "salon":     ['["shop"="hairdresser"]', '["shop"="beauty"]'],
    "gym":       ['["leisure"="fitness_centre"]', '["leisure"="sports_centre"]'],
}


def _get(url, headers=None, timeout=12):
    req = urllib.request.Request(url, headers={"User-Agent": UA, **(headers or {})})
    with urllib.request.urlopen(req, timeout=timeout, context=_CTX) as r:
        return r.read().decode("utf-8", "replace"), dict(r.headers), r.geturl()


def _post(url, data, headers=None, timeout=60):
    body = data.encode() if isinstance(data, str) else data
    req = urllib.request.Request(url, data=body,
                                 headers={"User-Agent": UA, **(headers or {})})
    with urllib.request.urlopen(req, timeout=timeout, context=_CTX) as r:
        return r.read().decode("utf-8", "replace")


# ----------------------------------------------------------------- sourcing
def geocode(location):
    """Location string -> (south, west, north, east) bounding box via Nominatim."""
    q = urllib.parse.urlencode({"q": location, "format": "json", "limit": 1})
    txt, _, _ = _get("https://nominatim.openstreetmap.org/search?" + q)
    arr = json.loads(txt)
    if not arr:
        raise ValueError(f"Could not locate '{location}'")
    bb = arr[0]["boundingbox"]  # [south, north, west, east] as strings
    s, n, w, e = float(bb[0]), float(bb[1]), float(bb[2]), float(bb[3])
    return s, w, n, e


def source_osm(niche, location, limit=30):
    s, w, n, e = geocode(location)
    filters = NICHE_TAGS.get(niche.lower().strip(),
                             [f'["name"~"{re.escape(niche)}",i]'])
    bbox = f"{s},{w},{n},{e}"
    parts = []
    for f in filters:
        parts.append(f'node{f}({bbox});')
        parts.append(f'way{f}({bbox});')
    query = f"[out:json][timeout:25];({''.join(parts)});out center tags 200;"
    txt = _post("https://overpass-api.de/api/interpreter", "data=" + urllib.parse.quote(query))
    data = json.loads(txt)
    out = []
    seen = set()
    for el in data.get("elements", []):
        t = el.get("tags", {})
        name = t.get("name")
        if not name or name in seen:
            continue
        site = t.get("website") or t.get("contact:website") or t.get("url")
        phone = t.get("phone") or t.get("contact:phone")
        addr = " ".join(filter(None, [t.get("addr:housenumber"), t.get("addr:street"),
                                       t.get("addr:city")]))
        seen.add(name)
        out.append({"name": name, "website": site, "phone": phone, "address": addr})
    # businesses with a website first (we can only audit those)
    out.sort(key=lambda b: (b["website"] is None, b["name"]))
    return out[:limit]


def source_places(niche, location, limit=30):
    """Google Places (text search) — only if GOOGLE_PLACES_KEY is set."""
    q = urllib.parse.urlencode({"query": f"{niche} in {location}", "key": PLACES_KEY})
    txt, _, _ = _get("https://maps.googleapis.com/maps/api/place/textsearch/json?" + q)
    data = json.loads(txt)
    out = []
    for r in data.get("results", [])[:limit]:
        pid = r.get("place_id")
        site = phone = None
        if pid:
            dq = urllib.parse.urlencode({"place_id": pid, "key": PLACES_KEY,
                                         "fields": "website,formatted_phone_number"})
            try:
                dt, _, _ = _get("https://maps.googleapis.com/maps/api/place/details/json?" + dq)
                det = json.loads(dt).get("result", {})
                site = det.get("website")
                phone = det.get("formatted_phone_number")
            except Exception:
                pass
        out.append({"name": r.get("name"), "website": site, "phone": phone,
                    "address": r.get("formatted_address", "")})
    out.sort(key=lambda b: (b["website"] is None, b["name"]))
    return out


def source(niche, location, limit=30):
    if PLACES_KEY:
        try:
            res = source_places(niche, location, limit)
            if res:
                return res, "google_places"
        except Exception:
            pass
    return source_osm(niche, location, limit), "openstreetmap"


# ----------------------------------------------------------------- auditing
def audit_site(url):
    """Fast keyless audit. Returns a scorecard with a list of flaws."""
    flaws = []
    sc = {"url": url, "https": False, "load_ms": None, "mobile": False,
          "meta_title": False, "meta_desc": False, "cta": False, "gbp": False,
          "reachable": False, "flaws": flaws}
    if not url:
        flaws.append("no website at all")
        sc["score"] = 99
        return sc

    # Build attempt list, preferring https, with a scheme fallback.
    if url.startswith("https://"):
        attempts = [url, "http://" + url[8:]]
    elif url.startswith("http://"):
        attempts = [url, "https://" + url[7:]]
    else:
        attempts = ["https://" + url, "http://" + url]

    html = final = None
    last_http = None
    t0 = time.time()
    for target in attempts:
        try:
            html, _, final = _get(target, headers=BROWSER_HEADERS, timeout=12)
            break
        except urllib.error.HTTPError as he:
            last_http = he.code
            if he.code in (401, 403, 406, 429):  # blocked, not broken
                continue
            # other HTTP errors: server responded but with an error page
            continue
        except Exception:
            continue

    if html is None:
        if last_http in (401, 403, 406, 429):
            flaws.append("blocked automated audit — verify manually")
            sc["score"] = 15  # not a confirmed prospect; needs a human look
        elif last_http is not None:
            flaws.append(f"site returns HTTP {last_http}")
            sc["score"] = 85
        else:
            flaws.append("site unreachable (down or DNS failure)")
            sc["score"] = 88
        return sc

    sc["reachable"] = True
    sc["load_ms"] = int((time.time() - t0) * 1000)
    sc["https"] = final.lower().startswith("https")
    low = html.lower()
    sc["mobile"] = ('name="viewport"' in low) or ("name='viewport'" in low)
    m = re.search(r"<title[^>]*>(.*?)</title>", html, re.I | re.S)
    sc["meta_title"] = bool(m and m.group(1).strip())
    sc["meta_desc"] = bool(re.search(r'<meta[^>]+name=["\']description["\'][^>]+content=["\'][^"\']{10,}', html, re.I))
    sc["cta"] = bool(re.search(r'(href=["\']tel:|book\s+(now|online|appointment)|'
                               r'request\s+(a\s+)?(quote|appointment)|call\s+now|'
                               r'schedule\s+(an?\s+)?appointment|get\s+a\s+quote|'
                               r'contact\s+us)', low))
    sc["gbp"] = bool(re.search(r'(google\.com/maps|g\.page|maps\.app\.goo|'
                               r'"@type"\s*:\s*"localbusiness")', low))

    if not sc["https"]:                 flaws.append("no HTTPS")
    if sc["load_ms"] and sc["load_ms"] > 3000: flaws.append(f"slow load ({sc['load_ms']}ms)")
    if not sc["mobile"]:                flaws.append("not mobile-responsive (no viewport)")
    if not sc["meta_title"]:            flaws.append("missing/empty title tag")
    if not sc["meta_desc"]:             flaws.append("missing meta description")
    if not sc["cta"]:                   flaws.append("no clear call-to-action")
    if not sc["gbp"]:                   flaws.append("no Google Business linkage")
    sc["score"] = len(flaws) * 10 + (10 if not sc["https"] else 0)  # higher = worse
    return sc


def find_unoptimized(niche, location, limit=30):
    businesses, src = source(niche, location, limit)
    auditable = [b for b in businesses if b["website"]]
    results = []
    with ThreadPoolExecutor(max_workers=8) as pool:
        fut = {pool.submit(audit_site, b["website"]): b for b in auditable}
        for f in as_completed(fut):
            b = fut[f]
            try:
                b["audit"] = f.result()
            except Exception as ex:
                b["audit"] = {"score": 80, "flaws": [f"audit error: {ex}"], "url": b["website"]}
            results.append(b)
    results.sort(key=lambda b: b["audit"]["score"], reverse=True)  # worst first
    return {"source": src, "niche": niche, "location": location,
            "total_found": len(businesses),
            "without_website": sum(1 for b in businesses if not b["website"]),
            "audited": len(results), "results": results}


# ----------------------------------------------------------------- CLI
def main():
    if len(sys.argv) < 3:
        print('Usage: python prospector.py "<niche>" "<location>" [limit]')
        return
    niche, location = sys.argv[1], sys.argv[2]
    limit = int(sys.argv[3]) if len(sys.argv) > 3 else 30
    print(f"\n  Sourcing {niche}s in {location} ...")
    data = find_unoptimized(niche, location, limit)
    print(f"  Source: {data['source']} | found {data['total_found']} "
          f"({data['without_website']} had no website) | audited {data['audited']}\n")
    for i, b in enumerate(data["results"][:15], 1):
        a = b["audit"]
        print(f"  {i:2}. [{a['score']:3}] {b['name']}")
        print(f"       {b.get('website')}")
        if b.get("phone"):
            print(f"       ph: {b['phone']}")
        print(f"       flaws: {', '.join(a['flaws']) or 'none - well optimized'}")
    print()


if __name__ == "__main__":
    main()
