#!/usr/bin/env python3
"""
Tapedeck — the screener.

Takes a parsed brief and checks every market in its universe for bars where all
the conditions hold at once, which is the literal ask in "find me everything
with RSI below 30 and volume +200% **at the same time**".

Reports, per market: whether the setup is live on the newest closed bar, when it
last fired, and how often it fired across the window — plus the actual indicator
readings at that bar, so a hit can be checked rather than trusted.
"""
import sys
import time

import brief
import feed


def _resolve_value(right, series_cache, bars, i):
    """The right-hand side of a condition: a constant, or another series."""
    if isinstance(right, dict):
        return series_cache[_key(right)][i]
    return right


def _key(ref):
    return (ref["kind"], ref.get("length"))


def build_series(bars, filters):
    """One series per distinct reference in the brief, computed once."""
    cache = {}
    for f in filters:
        for ref in (f["left"], f["right"]):
            if isinstance(ref, dict) and _key(ref) not in cache:
                cache[_key(ref)] = brief.series_for(ref, bars)
    return cache


def holds(filters, series_cache, bars, i):
    """Do all conditions hold on bar i? Unknown (warm-up) counts as no."""
    for f in filters:
        left = series_cache[_key(f["left"])][i]
        right = _resolve_value(f["right"], series_cache, bars, i)
        if left is None or right is None:
            return False
        if f["op"] == "<" and not left < right:
            return False
        if f["op"] == ">" and not left > right:
            return False
    return True


def hits(bars, filters):
    """Indices of every bar where the whole condition set is true."""
    cache = build_series(bars, filters)
    return [i for i in range(len(bars)) if holds(filters, cache, bars, i)], cache


def readings(filters, cache, bars, i):
    """What the indicators actually said at bar i — the receipt for a hit."""
    out = []
    for f in filters:
        left = cache[_key(f["left"])][i]
        right = _resolve_value(f["right"], series_cache=cache, bars=bars, i=i)
        out.append({
            "label": brief.ref_label(f["left"]),
            "value": left,
            "op": f["op"],
            "against": right,
            "against_label": (brief.ref_label(f["right"])
                              if isinstance(f["right"], dict) else None),
        })
    return out


def universe_for(spec):
    if spec["whole_market"]:
        return feed.liquid_products(limit=spec["universe_size"])
    found = []
    for symbol in spec["symbols"]:
        found.extend(feed.resolve(symbol))
    return list(dict.fromkeys(found)) or ["BTC-USD"]


def run(spec, history=None, progress=True):
    """
    Scan the brief's universe. Returns (results, skipped).

    Each result: product, live (setup true on the newest closed bar), last_index,
    last_ts, count, close, readings, bars.
    """
    products = universe_for(spec)
    history = history or brief.DEFAULTS["scan_history"]
    results, skipped = [], []

    for n, product in enumerate(products, 1):
        if progress:
            sys.stderr.write("\r  scanning %-14s %d/%d " % (product, n, len(products)))
            sys.stderr.flush()
        try:
            bars = feed.candles(product, spec["timeframe"], history)
        except feed.FeedError as exc:
            skipped.append((product, str(exc)))
            continue
        if len(bars) < 60:
            skipped.append((product, "only %d bars of history" % len(bars)))
            continue

        found, cache = hits(bars, spec["filters"])
        if not found:
            continue
        last = found[-1]
        results.append({
            "product": product,
            "bars": bars,
            "live": last == len(bars) - 1,
            "last_index": last,
            "last_ts": bars[last].ts,
            "count": len(found),
            "all_hits": found,
            "close": bars[last].close,
            "readings": readings(spec["filters"], cache, bars, last),
        })
    if progress:
        sys.stderr.write("\r" + " " * 44 + "\r")
        sys.stderr.flush()

    # live setups first, then most recent
    results.sort(key=lambda r: (not r["live"], -r["last_ts"]))
    return results, skipped


def render(results, skipped, spec):
    """Text report — what a scan prints in the terminal."""
    if not results:
        lines = ["No market in the scanned universe met all conditions."]
        if skipped:
            lines.append("(%d skipped: %s)" % (len(skipped), skipped[0][1]))
        return "\n".join(lines)

    live = [r for r in results if r["live"]]
    lines = ["%d market%s matched — %d live on the newest closed bar."
             % (len(results), "" if len(results) == 1 else "s", len(live)), ""]
    for r in results:
        when = time.strftime("%Y-%m-%d %H:%M", time.gmtime(r["last_ts"]))
        flag = "LIVE NOW" if r["live"] else "last fired"
        lines.append("  %-12s %-9s %s UTC   close %s   %d hit%s in window"
                     % (r["product"], flag, when, _money(r["close"]),
                        r["count"], "" if r["count"] == 1 else "s"))
        for reading in r["readings"]:
            against = (reading["against_label"] or "")
            target = _num(reading["against"])
            lines.append("       %-26s %8s  %s %s%s"
                         % (reading["label"], _num(reading["value"]),
                            reading["op"], target,
                            " (%s)" % against if against else ""))
    if skipped:
        lines.append("")
        lines.append("  %d market%s skipped (no data or too little history)"
                     % (len(skipped), "" if len(skipped) == 1 else "s"))
    return "\n".join(lines)


def _num(value):
    if value is None:
        return "—"
    return format(value, ",.0f") if abs(value) >= 1000 else "%.2f" % value


def _money(value):
    return format(value, ",.0f") if value >= 1000 else format(value, ",.2f")


if __name__ == "__main__":
    text = " ".join(sys.argv[1:]) or \
        "Find me all BTC markets with RSI below 30 and volume +200%"
    spec = brief.parse(text)
    print(brief.describe(spec))
    print()
    found, missed = run(spec)
    print(render(found, missed, spec))
