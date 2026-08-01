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


CROSS_OPS = ("crosses_above", "crosses_below")


def _resolve_value(right, series_cache, bars, i):
    """Either side of a condition at bar i: a constant, or a series reading."""
    if isinstance(right, dict):
        series = series_cache[_key(right)]
        return series[i] if 0 <= i < len(series) else None
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


def _one_holds(f, cache, bars, i):
    left = _resolve_value(f["left"], cache, bars, i)
    right = _resolve_value(f["right"], cache, bars, i)
    if left is None or right is None:
        return False

    if f["op"] == "<":
        return left < right
    if f["op"] == ">":
        return left > right

    if f["op"] in CROSS_OPS:
        # A cross needs the bar before it: same side then the other side. Without
        # the previous reading there is no cross to speak of, so warm-up is a no.
        if i == 0:
            return False
        prev_left = _resolve_value(f["left"], cache, bars, i - 1)
        prev_right = _resolve_value(f["right"], cache, bars, i - 1)
        if prev_left is None or prev_right is None:
            return False
        if f["op"] == "crosses_above":
            return prev_left <= prev_right and left > right
        return prev_left >= prev_right and left < right
    return False


def holds(filters, series_cache, bars, i):
    """Do all conditions hold on bar i? Unknown (warm-up) counts as no."""
    return all(_one_holds(f, series_cache, bars, i) for f in filters)


def hits(bars, filters):
    """Indices of every bar where the whole condition set is true."""
    cache = build_series(bars, filters)
    return [i for i in range(len(bars)) if holds(filters, cache, bars, i)], cache


OP_TEXT = {"<": "<", ">": ">", "crosses_above": "x↑", "crosses_below": "x↓"}


def readings(filters, cache, bars, i):
    """What the indicators actually said at bar i — the receipt for a hit."""
    out = []
    for f in filters:
        left = _resolve_value(f["left"], cache, bars, i)
        right = _resolve_value(f["right"], cache, bars, i)
        row = {
            "label": brief.ref_label(f["left"]),
            "value": left,
            "op": f["op"],
            "against": right,
            "against_label": (brief.ref_label(f["right"])
                              if isinstance(f["right"], dict) else None),
        }
        if f["op"] in CROSS_OPS:
            # a cross is only legible next to where it came from
            row["from"] = _resolve_value(f["left"], cache, bars, i - 1)
            row["from_against"] = _resolve_value(f["right"], cache, bars, i - 1)
        out.append(row)
    return out


def resolve_universe(spec):
    """
    Returns (products, unlisted) for the brief's universe.

    `unlisted` is every symbol that isn't on these venues. It matters: this reads
    crypto spot, so "AAPL" has no market here, and quietly charting BTC-USD
    instead would answer a question nobody asked.
    """
    if spec["whole_market"]:
        return feed.liquid_products(limit=spec["universe_size"]), []
    found, unlisted = [], []
    for symbol in spec["symbols"]:
        hits = feed.resolve(symbol)
        if hits:
            found.extend(hits)
        else:
            unlisted.append(symbol)
    return list(dict.fromkeys(found)), unlisted


def universe_for(spec):
    """Just the tradable products — see resolve_universe for what got dropped."""
    return resolve_universe(spec)[0]


def run(spec, history=None, progress=True, fresh=False):
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
            bars = feed.candles(product, spec["timeframe"], history, fresh=fresh)
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


def reading_lines(readings, indent="       "):
    """The per-condition receipt lines, shared by the report and watch mode."""
    lines = []
    for reading in readings:
        value = _num(reading["value"])
        if "from" in reading:
            value = "%s→%s" % (_num(reading["from"]), value)
        against = reading["against_label"] or ""
        lines.append("%s%-26s %12s  %s %s%s"
                     % (indent, reading["label"], value,
                        OP_TEXT.get(reading["op"], reading["op"]),
                        _num(reading["against"]),
                        " (%s)" % against if against else ""))
    return lines


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
                     % (r["product"], flag, when, money(r["close"]),
                        r["count"], "" if r["count"] == 1 else "s"))
        lines.extend(reading_lines(r["readings"]))
    if skipped:
        lines.append("")
        lines.append("  %d market%s skipped (no data or too little history)"
                     % (len(skipped), "" if len(skipped) == 1 else "s"))
    return "\n".join(lines)


def _num(value):
    """
    Two decimals is fine for RSI and useless for a MACD line on a $0.002 token —
    "-0.02 crosses above -0.02" tells you nothing. Small magnitudes get
    significant digits instead so the crossing is actually visible.
    """
    if value is None:
        return "—"
    size = abs(value)
    if size >= 1000:
        return format(value, ",.0f")
    if size >= 1 or size == 0:
        return "%.2f" % value
    return "%.4g" % value


def money(value):
    """Price formatting that survives both BTC and sub-cent tokens."""
    if value >= 1000:
        return format(value, ",.0f")
    return format(value, ",.2f") if value >= 1 else "%.6g" % value


if __name__ == "__main__":
    text = " ".join(sys.argv[1:]) or \
        "Find me all BTC markets with RSI below 30 and volume +200%"
    spec = brief.parse(text)
    print(brief.describe(spec))
    print()
    found, missed = run(spec)
    print(render(found, missed, spec))
