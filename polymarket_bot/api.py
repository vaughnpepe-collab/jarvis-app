"""Thin stdlib-only client for Polymarket's public data APIs.

Two services are used, neither needs an API key:
  - Gamma  (gamma-api.polymarket.com): market metadata, prices, resolution.
  - CLOB   (clob.polymarket.com): live order books for exact fill prices.
"""

import json
import time
from datetime import datetime, timezone
import urllib.error
import urllib.parse
import urllib.request

GAMMA = "https://gamma-api.polymarket.com"
CLOB = "https://clob.polymarket.com"

_UA = "jarvis-polymarket-bot/1.0 (paper trading; educational)"


def _get(url, params=None, retries=3, timeout=20):
    if params:
        url = url + "?" + urllib.parse.urlencode(params)
    last_err = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": _UA})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as err:
            last_err = err
            time.sleep(2 ** attempt)
    raise RuntimeError(f"GET {url} failed after {retries} attempts: {last_err}")


def _floats(raw):
    """Gamma encodes list fields as JSON strings, e.g. '["0.97", "0.03"]'."""
    if not raw:
        return []
    values = json.loads(raw) if isinstance(raw, str) else raw
    return [float(v) for v in values]


def _strings(raw):
    if not raw:
        return []
    return json.loads(raw) if isinstance(raw, str) else raw


class Market:
    """Normalised view of a Gamma market row."""

    def __init__(self, row):
        self.id = str(row.get("id"))
        self.question = row.get("question", "")
        self.slug = row.get("slug", "")
        self.end_date = row.get("endDate")
        self.closed = bool(row.get("closed"))
        self.active = bool(row.get("active"))
        self.liquidity = float(row.get("liquidity") or 0)
        self.volume_24h = float(row.get("volume24hr") or 0)
        self.outcomes = _strings(row.get("outcomes"))
        self.prices = _floats(row.get("outcomePrices"))
        self.token_ids = _strings(row.get("clobTokenIds"))
        self.neg_risk = bool(row.get("negRisk"))

    def url(self):
        return f"https://polymarket.com/event/{self.slug}" if self.slug else ""


def open_markets(min_liquidity=0, min_volume=0, max_end_date=None,
                 max_pages=10, page_size=100):
    """Yield active, unresolved binary markets, soonest-resolving first.

    Liquidity/volume/end-date filtering happens server-side.
    max_end_date is an ISO date string (e.g. "2026-07-23").
    """
    today = datetime.now(timezone.utc).date().isoformat()
    for page in range(max_pages):
        params = {
            "closed": "false",
            "active": "true",
            "limit": page_size,
            "offset": page * page_size,
            "order": "endDate",
            "ascending": "true",
            "liquidity_num_min": min_liquidity,
            "volume_num_min": min_volume,
            "end_date_min": today,
        }
        if max_end_date:
            params["end_date_max"] = max_end_date
        rows = _get(f"{GAMMA}/markets", params)
        if not rows:
            return
        for row in rows:
            market = Market(row)
            if len(market.outcomes) == 2 and len(market.prices) == 2:
                yield market
        if len(rows) < page_size:
            return


def market_by_id(market_id):
    """Fetch one market (works for closed markets too, for settlement)."""
    row = _get(f"{GAMMA}/markets/{market_id}")
    return Market(row)


def best_ask(token_id):
    """Lowest ask on the CLOB for a token, as (price, size). None if no asks."""
    book = _get(f"{CLOB}/book", {"token_id": token_id})
    asks = book.get("asks") or []
    if not asks:
        return None
    price, size = min((float(a["price"]), float(a["size"])) for a in asks)
    return price, size
