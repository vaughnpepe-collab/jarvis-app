#!/usr/bin/env python3
"""
Tapedeck — market data feed.

Keyless OHLCV candles from public exchange endpoints, cached to disk so a scan
across dozens of markets doesn't hammer the API (and so the rest of the toolkit
still works with no network).

    from feed import candles, products
    bars = candles("BTC-USD", "1h", 500)     # oldest first
    print(bars[-1].close)

Sources, in order:
  1. Coinbase Exchange  api.exchange.coinbase.com   (spot, ~800 products)
  2. Kraken             api.kraken.com              (fallback)

Both are public, read-only and need no key. This is spot market data — not
futures. Nothing here places an order; there is no trading path in this project
at all, by design.
"""
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import namedtuple

ROOT = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(ROOT, "cache")

Candle = namedtuple("Candle", "ts open high low close volume")

# seconds per bar
TIMEFRAMES = {"1m": 60, "5m": 300, "15m": 900, "1h": 3600, "6h": 21600, "1d": 86400}
# Kraken speaks minutes, and has no 6h bar — 4h is the nearest it offers.
KRAKEN_INTERVAL = {"1m": 1, "5m": 5, "15m": 15, "1h": 60, "6h": 240, "1d": 1440}

UA = "tapedeck/1.0 (+public market data, read-only)"
PAGE = 300          # candles per request, Coinbase's cap
POLITE = 0.28       # seconds between requests


class FeedError(RuntimeError):
    pass


# ---------------------------------------------------------------- http
def _get(url, params=None, timeout=20, tries=3):
    if params:
        url = url + "?" + urllib.parse.urlencode(params)
    last = None
    for attempt in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.load(resp)
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, ValueError) as exc:
            last = exc
            code = getattr(exc, "code", None)
            if code in (400, 404, 451):      # bad symbol / blocked — retrying won't help
                break
            time.sleep(0.6 * (2 ** attempt))
    raise FeedError("%s -> %s" % (url.split("?")[0], last))


# ---------------------------------------------------------------- cache
def _cache_path(name):
    os.makedirs(CACHE, exist_ok=True)
    safe = name.replace("/", "_").replace(":", "_")
    return os.path.join(CACHE, safe + ".json")


def _cache_read(name, max_age):
    path = _cache_path(name)
    if not os.path.isfile(path):
        return None
    if max_age is not None and time.time() - os.path.getmtime(path) > max_age:
        return None
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (ValueError, OSError):
        return None


def _cache_write(name, payload):
    try:
        with open(_cache_path(name), "w", encoding="utf-8") as fh:
            json.dump(payload, fh, separators=(",", ":"))
    except OSError:
        pass          # a cache that can't be written is not a reason to fail


# ---------------------------------------------------------------- coinbase
def _coinbase_candles(product, timeframe, limit):
    """Coinbase rows are [ts, low, high, open, close, volume], newest first."""
    gran = TIMEFRAMES[timeframe]
    url = "https://api.exchange.coinbase.com/products/%s/candles" % product
    out, end = {}, None
    while len(out) < limit:
        params = {"granularity": gran}
        if end is not None:
            # a lone `end` is ignored — Coinbase only pages with an explicit window
            params["start"], params["end"] = end - gran * PAGE, end
        rows = _get(url, params)
        if not rows:
            break
        before = len(out)
        for ts, low, high, opn, close, vol in rows:
            out[int(ts)] = Candle(int(ts), float(opn), float(high), float(low),
                                  float(close), float(vol))
        if len(out) == before:
            break                                  # page added nothing new
        end = min(int(r[0]) for r in rows) - gran
        time.sleep(POLITE)
    return [out[k] for k in sorted(out)][-limit:]


def _coinbase_products(quotes):
    rows = _get("https://api.exchange.coinbase.com/products")
    keep = []
    for p in rows:
        if p.get("trading_disabled") or p.get("status") != "online":
            continue
        if p.get("quote_currency") not in quotes:
            continue
        keep.append(p["id"])
    return sorted(keep)


# ---------------------------------------------------------------- kraken
def _kraken_pair(product):
    base, _, quote = product.partition("-")
    base = {"BTC": "XBT"}.get(base, base)
    return base + quote


def _kraken_candles(product, timeframe, limit):
    """Kraken rows are [ts, open, high, low, close, vwap, volume, trades]."""
    data = _get("https://api.kraken.com/0/public/OHLC",
                {"pair": _kraken_pair(product), "interval": KRAKEN_INTERVAL[timeframe]})
    if data.get("error"):
        raise FeedError("kraken: %s" % data["error"])
    series = [v for k, v in (data.get("result") or {}).items() if k != "last"]
    if not series:
        raise FeedError("kraken returned no series for %s" % product)
    bars = [Candle(int(r[0]), float(r[1]), float(r[2]), float(r[3]), float(r[4]), float(r[6]))
            for r in series[0]]
    return sorted(bars, key=lambda b: b.ts)[-limit:]


# ---------------------------------------------------------------- public api
def candles(product, timeframe="1h", limit=400, fresh=False):
    """OHLCV for one market, oldest first. Cached for roughly half a bar."""
    if timeframe not in TIMEFRAMES:
        raise FeedError("unknown timeframe %r (have %s)"
                        % (timeframe, ", ".join(TIMEFRAMES)))
    key = "candles_%s_%s" % (product, timeframe)
    if not fresh:
        cached = _cache_read(key, max_age=TIMEFRAMES[timeframe] / 2)
        if cached and len(cached["bars"]) >= min(limit, cached.get("asked", 0)):
            return [Candle(*b) for b in cached["bars"]][-limit:]

    bars, errors = [], []
    for name, fetch in (("coinbase", _coinbase_candles), ("kraken", _kraken_candles)):
        try:
            bars = fetch(product, timeframe, limit)
            if bars:
                break
        except FeedError as exc:
            errors.append("%s: %s" % (name, exc))
    if not bars:
        stale = _cache_read(key, max_age=None)          # better stale than nothing
        if stale:
            return [Candle(*b) for b in stale["bars"]][-limit:]
        raise FeedError("no data for %s %s (%s)" % (product, timeframe, "; ".join(errors)))

    _cache_write(key, {"asked": limit, "fetched": int(time.time()),
                       "bars": [list(b) for b in bars]})
    return bars


def products(quotes=("USD",), fresh=False):
    """Tradable product ids, e.g. ['BTC-USD', 'ETH-USD', ...]."""
    key = "products_" + "-".join(quotes)
    if not fresh:
        cached = _cache_read(key, max_age=86400)
        if cached:
            return cached["products"]
    found = _coinbase_products(set(quotes))
    _cache_write(key, {"products": found, "fetched": int(time.time())})
    return found


def liquid_products(quotes=("USD",), limit=60, fresh=False):
    """
    The `limit` busiest markets, ranked by 24h volume in quote currency.

    One request covers every product, so "scan the market" costs a single call
    to rank and only then pulls candles for the shortlist.
    """
    key = "liquidity_" + "-".join(quotes)
    ranked = None if fresh else (_cache_read(key, max_age=3600) or {}).get("ranked")
    if ranked is None:
        stats = _get("https://api.exchange.coinbase.com/products/stats")
        tradable = set(products(quotes, fresh=fresh))
        scored = []
        for pid, row in stats.items():
            if pid not in tradable:
                continue
            day = (row or {}).get("stats_24hour") or {}
            try:
                turnover = float(day.get("volume") or 0) * float(day.get("last") or 0)
            except (TypeError, ValueError):
                continue
            if turnover > 0:
                scored.append((turnover, pid))
        scored.sort(reverse=True)
        ranked = [pid for _, pid in scored]
        _cache_write(key, {"ranked": ranked, "fetched": int(time.time())})
    return ranked[:limit]


def resolve(query, quotes=("USD",)):
    """'BTC' -> every BTC market; 'BTC-USD' -> itself. Case-insensitive."""
    want = query.strip().upper()
    universe = products(quotes)
    if want in universe:
        return [want]
    hits = [p for p in universe if p.split("-")[0] == want]
    return hits or [p for p in universe if want in p]


if __name__ == "__main__":
    import sys
    sym = sys.argv[1] if len(sys.argv) > 1 else "BTC-USD"
    tf = sys.argv[2] if len(sys.argv) > 2 else "1h"
    bars = candles(sym, tf, 300)
    print("%s %s — %d bars" % (sym, tf, len(bars)))
    for b in bars[-3:]:
        print("  %s  o=%s h=%s l=%s c=%s v=%.2f"
              % (time.strftime("%Y-%m-%d %H:%M", time.gmtime(b.ts)),
                 b.open, b.high, b.low, b.close, b.volume))
