#!/usr/bin/env python3
"""
Tapedeck — plain English into a spec the rest of the toolkit can execute.

    parse("find me all BTC markets with RSI below 30 and volume +200%")

gives back a dict describing the universe, timeframe, filters, strategy and what
to do with them. `describe()` renders it back as prose, so before anything runs
you can see exactly what was understood — including where a vague phrase was
pinned to a number.

This is a deterministic parser: regex rules, no model call, no API key, no
network. That matters for a tool whose output you're meant to check — the same
sentence always produces the same spec, and every assumption it makes is listed
in `notes` rather than hidden. `LLM_HANDOFF` in the README covers wiring a model
in front of it for looser phrasing.
"""
import re

import indicators as ind

TIMEFRAME_WORDS = [
    (r"\b(?:1|one)\s*(?:m|min|minute)s?\b", "1m"),
    (r"\b(?:5|five)\s*(?:m|min|minute)s?\b", "5m"),
    (r"\b(?:15|fifteen)\s*(?:m|min|minute)s?\b", "15m"),
    (r"\b(?:1|one|an)\s*(?:h|hr|hour)s?\b", "1h"),
    (r"\bhourly\b", "1h"),
    (r"\b(?:6|six)\s*(?:h|hr|hour)s?\b", "6h"),
    (r"\b(?:daily|1d|one day|day)\b", "1d"),
]
# phrasings we round to the nearest bar the feeds actually publish
TIMEFRAME_NEAREST = [
    (r"\b(?:3|three)\s*(?:m|min|minute)s?\b", "5m", "3-minute"),
    (r"\b(?:30|thirty)\s*(?:m|min|minute)s?\b", "15m", "30-minute"),
    (r"\b(?:2|two)\s*(?:h|hr|hour)s?\b", "1h", "2-hour"),
    (r"\b(?:4|four)\s*(?:h|hr|hour)s?\b", "6h", "4-hour"),
    (r"\b(?:12|twelve)\s*(?:h|hr|hour)s?\b", "6h", "12-hour"),
    (r"\bweekly\b", "1d", "weekly"),
]

NAMED_COINS = {
    "bitcoin": "BTC", "btc": "BTC", "ether": "ETH", "ethereum": "ETH", "eth": "ETH",
    "solana": "SOL", "sol": "SOL", "ripple": "XRP", "xrp": "XRP",
    "dogecoin": "DOGE", "doge": "DOGE", "cardano": "ADA", "ada": "ADA",
    "chainlink": "LINK", "link": "LINK", "litecoin": "LTC", "ltc": "LTC",
    "avalanche": "AVAX", "avax": "AVAX", "polkadot": "DOT", "dot": "DOT",
}
WHOLE_MARKET = r"\b(?:all|any|every|everything|the market|markets|scan the market|screener?)\b"

BELOW = r"(?:below|under|less than|lower than|beneath|<=?)"
ABOVE = r"(?:above|over|greater than|higher than|more than|>=?)"

# words that never mean "ticker", however they're capitalised
STOP_TOKENS = {
    "RSI", "MACD", "EMA", "SMA", "MA", "ATR", "USD", "USDT", "BB", "PNL", "TP", "SL",
    "AND", "OR", "THE", "ALL", "ANY", "WITH", "FOR", "ME", "MY", "AT", "IN", "ON",
    "BUY", "SELL", "LONG", "SHORT", "STOP", "TARGET", "VOLUME", "PRICE", "CLOSE",
    "OPEN", "HIGH", "LOW", "FIND", "SHOW", "SCAN", "CHART", "REPLAY", "BACKTEST",
    "SUPPORT", "RESISTANCE", "LEVELS", "TREND", "ENTRY", "EXIT", "WEEK", "MONTH",
    "DAY", "BARS", "CANDLES", "OF", "TO", "A", "AN", "IS", "ARE", "WAS", "WHERE",
}

DEFAULTS = dict(stop_pct=2.0, target_pct=4.0, max_hold=48, universe_size=40,
                history=700, scan_history=260)


# ---------------------------------------------------------------- helpers
def _ref(kind, length=None):
    return {"kind": kind, "length": length}


def _op(word):
    word = word.strip().lower()
    if re.fullmatch(BELOW, word):
        return "<"
    if re.fullmatch(ABOVE, word):
        return ">"
    return {"<": "<", "<=": "<", ">": ">", ">=": ">"}.get(word, "<")


def _filter(left, op, right, text):
    return {"left": left, "op": op, "right": right, "text": text}


# ---------------------------------------------------------------- sections
def _timeframe(text, notes, default):
    for pattern, tf in TIMEFRAME_WORDS:
        if re.search(pattern, text):
            return tf
    for pattern, tf, said in TIMEFRAME_NEAREST:
        if re.search(pattern, text):
            notes.append("no %s bars on these feeds — using %s" % (said, tf))
            return tf
    return default


def _universe(text, notes):
    """
    Returns (symbols, explicit, defaulted).

    explicit False  -> no market named, rank the whole market
    defaulted True  -> nothing named and nothing implied; caller picks a default
    """
    symbols = []
    for token in re.findall(r"\b[A-Za-z][A-Za-z0-9]{1,5}\b", text):
        upper = token.upper()
        if upper in STOP_TOKENS:
            continue
        named = NAMED_COINS.get(token.lower())
        if named:
            symbols.append(named)
        elif token.isupper() and len(token) >= 3:
            symbols.append(upper)                 # looks like a ticker: SOL, HYPE

    if "future" in text or "perp" in text:
        notes.append("these feeds are spot markets — reading spot, not futures/perps")

    seen, ordered = set(), []
    for sym in symbols:
        if sym not in seen:
            seen.add(sym)
            ordered.append(sym)
    if ordered:
        return ordered, True, False
    if re.search(WHOLE_MARKET, text):
        return [], False, False
    return ["BTC"], True, True


def _filters(text, notes):
    out = []

    # --- RSI, with optional length: "RSI below 30", "rsi(21) > 70"
    for m in re.finditer(r"\brsi\s*(?:\(\s*(\d+)\s*\))?\s*(?:is\s*)?(%s|%s)\s*(\d+(?:\.\d+)?)"
                         % (BELOW, ABOVE), text):
        length = int(m.group(1)) if m.group(1) else 14
        op, value = _op(m.group(2)), float(m.group(3))
        out.append(_filter(_ref("rsi", length), op, value,
                           "RSI(%d) %s %g" % (length, "below" if op == "<" else "above", value)))

    # --- volume as a percentage jump: "volume +200%", "volume up 150%"
    for m in re.finditer(r"\bvolume\s*(?:is\s*)?(?:up\s*|\+\s*)?\+?\s*(\d+(?:\.\d+)?)\s*%", text):
        pct = float(m.group(1))
        ratio = 1.0 + pct / 100.0
        out.append(_filter(_ref("vol_ratio", 20), ">", ratio,
                           "volume at least %g%% above its 20-bar average (%.2fx)" % (pct, ratio)))
        notes.append("read 'volume +%g%%' as %.2fx the 20-bar average volume"
                     % (pct, ratio))

    # --- volume as a multiple: "volume above 3x average"
    for m in re.finditer(r"\bvolume\s*(?:%s|%s)?\s*(\d+(?:\.\d+)?)\s*x\b" % (ABOVE, BELOW), text):
        ratio = float(m.group(1))
        out.append(_filter(_ref("vol_ratio", 20), ">", ratio,
                           "volume above %.2fx its 20-bar average" % ratio))

    # --- bare "volume spike"
    if not any(f["left"]["kind"] == "vol_ratio" for f in out) and \
            re.search(r"\bvolume\s*(?:spike|surge|blow[- ]?off|climax)\b", text):
        out.append(_filter(_ref("vol_ratio", 20), ">", 2.0,
                           "volume above 2.00x its 20-bar average"))
        notes.append("'volume spike' pinned to 2.00x the 20-bar average")

    # --- price against a moving average: "price above the 200 EMA"
    for m in re.finditer(r"\b(?:price|close|it)\s*(?:is\s*)?(%s|%s)\s*(?:the\s*)?(\d+)\s*[- ]?"
                         r"(ema|sma|ma)\b" % (BELOW, ABOVE), text):
        op, length, kind = _op(m.group(1)), int(m.group(2)), m.group(3)
        kind = "ema" if kind == "ema" else "sma"
        out.append(_filter(_ref("close"), op, _ref(kind, length),
                           "close %s the %d %s" % ("below" if op == "<" else "above",
                                                    length, kind.upper())))

    # --- MACD sign
    if re.search(r"\bmacd\s*(?:is\s*)?(?:positive|bullish|above zero)\b", text):
        out.append(_filter(_ref("macd_hist"), ">", 0.0, "MACD histogram positive"))
    if re.search(r"\bmacd\s*(?:is\s*)?(?:negative|bearish|below zero)\b", text):
        out.append(_filter(_ref("macd_hist"), "<", 0.0, "MACD histogram negative"))

    # --- Bollinger touches
    if re.search(r"\b(?:below|under|outside)\s*(?:the\s*)?lower\s*(?:bollinger|band|bb)", text):
        out.append(_filter(_ref("close"), "<", _ref("bb_lower", 20), "close below the lower Bollinger band"))
    if re.search(r"\b(?:above|over|outside)\s*(?:the\s*)?upper\s*(?:bollinger|band|bb)", text):
        out.append(_filter(_ref("close"), ">", _ref("bb_upper", 20), "close above the upper Bollinger band"))

    # --- the project's own composite
    for m in re.finditer(r"\bwhale[- ]?(?:momentum|activity)?\s*(?:is\s*)?(%s|%s)\s*(-?\d+(?:\.\d+)?)"
                         % (BELOW, ABOVE), text):
        op, value = _op(m.group(1)), float(m.group(2))
        out.append(_filter(_ref("whale"), op, value,
                           "whale-momentum %s %g" % ("below" if op == "<" else "above", value)))

    # --- generic "% change" moves: "up more than 5% today"
    for m in re.finditer(r"\b(up|down)\s*(?:more than\s*|over\s*|by\s*)?(\d+(?:\.\d+)?)\s*%", text):
        if re.search(r"volume\s*(?:is\s*)?(?:up\s*|\+\s*)?%s\s*%%" % re.escape(m.group(2)), text):
            continue                                  # that was the volume rule's match
        direction, pct = m.group(1), float(m.group(2))
        op = ">" if direction == "up" else "<"
        value = pct if direction == "up" else -pct
        out.append(_filter(_ref("change", 24), op, value,
                           "%s %g%% or more over 24 bars" % (direction, pct)))
    return out


def _strategy(text, filters, notes):
    short = bool(re.search(r"\bshort(?:ing|s)?\b|\bsell\s*signal\b|\bfade\b", text))
    stop_pct = target_pct = atr_stop = None
    max_hold = DEFAULTS["max_hold"]

    m = re.search(r"(\d+(?:\.\d+)?)\s*%\s*stop|stop\s*(?:loss\s*)?(?:at\s*|of\s*)?(\d+(?:\.\d+)?)\s*%", text)
    if m:
        stop_pct = float(m.group(1) or m.group(2))
    m = re.search(r"(\d+(?:\.\d+)?)\s*(?:x\s*)?atr\s*stop|stop\s*(?:at\s*|of\s*)?(\d+(?:\.\d+)?)\s*(?:x\s*)?atr", text)
    if m:
        atr_stop = float(m.group(1) or m.group(2))
    m = re.search(r"(?:target|take\s*profit|tp)\s*(?:at\s*|of\s*)?(\d+(?:\.\d+)?)\s*%"
                  r"|(\d+(?:\.\d+)?)\s*%\s*(?:target|take\s*profit)", text)
    if m:
        target_pct = float(m.group(1) or m.group(2))
    m = re.search(r"(?:hold|exit after|for)\s*(\d+)\s*(bar|candle|hour|day)s?", text)
    if m:
        count, unit = int(m.group(1)), m.group(2)
        max_hold = count if unit in ("bar", "candle") else count
        if unit in ("hour", "day"):
            notes.append("read 'hold %d %ss' as %d bars" % (count, unit, count))

    if stop_pct is None and atr_stop is None:
        stop_pct = DEFAULTS["stop_pct"]
        notes.append("no stop given — using %g%%" % stop_pct)
    if target_pct is None:
        target_pct = DEFAULTS["target_pct"]
        notes.append("no target given — using %g%%" % target_pct)

    return dict(direction="short" if short else "long", entry=filters,
                stop_pct=stop_pct, atr_stop=atr_stop, target_pct=target_pct,
                max_hold=max_hold)


def _replay_bars(text, timeframe, notes):
    per_day = {"1m": 1440, "5m": 288, "15m": 96, "1h": 24, "6h": 4, "1d": 1}[timeframe]
    windows = [(r"\blast week\b|\bpast week\b|\b7 days?\b", 7, "last week"),
               (r"\blast month\b|\bpast month\b|\b30 days?\b", 30, "last month"),
               (r"\byesterday\b|\blast 24 ?h(?:ours)?\b|\bpast day\b", 1, "the last day"),
               (r"\blast (\d+) days?\b", None, None)]
    for pattern, days, said in windows:
        m = re.search(pattern, text)
        if not m:
            continue
        if days is None:
            days = int(m.group(1))
            said = "the last %d days" % days
        notes.append("replay window: %s (%d bars of %s)" % (said, days * per_day, timeframe))
        return days * per_day
    return 14 * per_day


def _actions(text, explicit_universe, filters):
    acts = set()
    if re.search(r"\b(find|scan|screen|search|which|show me all|list)\b", text) or not explicit_universe:
        if filters:
            acts.add("scan")
    if re.search(r"\bbacktest|back-?test|how would|would have (?:entered|worked)|test (?:it|this|my)\b", text):
        acts.add("backtest")
    if re.search(r"\breplay\b|\bcandle by candle\b|\bstep through\b", text):
        acts.update(("replay", "backtest"))
    if re.search(r"\bsupport|resistance|levels?\b", text):
        acts.add("levels")
    if re.search(r"\bchart|plot|draw|show\b", text):
        acts.add("chart")
    if re.search(r"\bindicator|oscillator\b", text):
        acts.add("indicator")
    if not acts:
        acts.update(("scan", "chart") if filters else ("chart", "levels"))
    if "scan" in acts and not filters:
        acts.discard("scan")
    acts.add("chart")                     # there is always something worth looking at
    return sorted(acts)


# ---------------------------------------------------------------- entry point
CARRY_OVER = (r"\bmy (?:system|strategy|setup|rules|conditions|filters)\b"
              r"|\bthe same (?:thing|conditions|setup|rules)\b|\bthose\b|\bthat setup\b")


def parse(text, default_timeframe="1h", previous=None):
    """
    `previous` is the spec from the last brief. A follow-up that says "replay
    where my system would have entered" has no conditions of its own — it means
    the ones you just gave, so they carry over.
    """
    lowered = " " + text.lower().strip() + " "
    notes = []
    timeframe = _timeframe(lowered, notes, default_timeframe)
    symbols, explicit, defaulted = _universe(text, notes)   # case matters for tickers
    if defaulted and previous:
        symbols, explicit = previous["symbols"], not previous["whole_market"]
        notes.append("no market named — staying on %s from the previous brief"
                     % (", ".join(symbols) if symbols else "the whole-market scan"))
    elif defaulted:
        notes.append("no market named — defaulting to BTC-USD")
    filters = _filters(lowered, notes)

    if not filters and previous and previous.get("filters") and re.search(CARRY_OVER, lowered):
        filters = previous["filters"]
        notes.append("carried %d condition(s) over from the previous brief"
                     % len(filters))
    actions = _actions(lowered, explicit, filters)

    # strategy defaults are only worth reporting if a backtest is actually going to use them
    strategy_notes = []
    strategy = _strategy(lowered, filters, strategy_notes)

    if "backtest" in actions and not filters:
        notes.append("nothing to backtest — no entry condition in the brief")
        actions = [a for a in actions if a not in ("backtest", "replay")]
    if "backtest" in actions:
        notes.extend(strategy_notes)

    return dict(raw=text.strip(), timeframe=timeframe, symbols=symbols,
                whole_market=not explicit, filters=filters, strategy=strategy,
                actions=actions, replay_bars=_replay_bars(lowered, timeframe, notes),
                universe_size=DEFAULTS["universe_size"], notes=notes)


def describe(spec):
    """The 'here's what I heard' echo — print this before doing any work."""
    lines = ["Brief: %s" % spec["raw"], ""]
    if spec["whole_market"]:
        lines.append("  Universe   the %d busiest USD markets" % spec["universe_size"])
    else:
        lines.append("  Universe   %s" % ", ".join(spec["symbols"]))
    lines.append("  Timeframe  %s bars" % spec["timeframe"])

    if spec["filters"]:
        lines.append("  Conditions (all must hold on the same bar)")
        for f in spec["filters"]:
            lines.append("    · %s" % f["text"])
    else:
        lines.append("  Conditions none")

    st = spec["strategy"]
    if "backtest" in spec["actions"]:
        stop = ("%.2f x ATR" % st["atr_stop"]) if st["atr_stop"] else "%g%%" % st["stop_pct"]
        lines.append("  Strategy   %s · stop %s · target %g%% · max hold %d bars"
                     % (st["direction"], stop, st["target_pct"], st["max_hold"]))
    lines.append("  Will do    %s" % ", ".join(spec["actions"]))
    if spec["notes"]:
        lines.append("")
        lines.append("  Assumptions made:")
        for note in spec["notes"]:
            lines.append("    - %s" % note)
    return "\n".join(lines)


def series_for(ref, bars):
    return ind.series(bars, ref["kind"], ref.get("length"))


def ref_label(ref):
    return ind.label(ref["kind"], ref.get("length"))


if __name__ == "__main__":
    import sys
    text = " ".join(sys.argv[1:]) or \
        "Find me all BTC futures with RSI below 30 and volume +200% at the same time"
    print(describe(parse(text)))
