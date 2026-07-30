#!/usr/bin/env python3
"""
Tapedeck — self-test.

    python selftest.py

Runs offline on synthetic candles: no network, no cache, no API. Covers the parts
where a silent bug would produce a plausible-looking wrong number — indicator
alignment, the no-look-ahead rule, the stop-before-target rule, and what the
brief parser understood.
"""
import sys

import backtest
import brief
import indicators as ind
import scan
from feed import Candle

FAILED = []


def check(label, condition, detail=""):
    mark = "ok  " if condition else "FAIL"
    print("  %s %s%s" % (mark, label, ("  — " + detail) if detail and not condition else ""))
    if not condition:
        FAILED.append(label)


def synth(n=300, start=100.0, wave=8.0):
    """Deterministic candles with a rising trend and a wobble — no randomness."""
    import math
    bars = []
    for i in range(n):
        mid = start + i * 0.15 + math.sin(i / 7.0) * wave
        opn = mid - 0.2
        close = mid + 0.2
        high = max(opn, close) + 0.6
        low = min(opn, close) - 0.6
        vol = 100.0 + (60.0 if i % 25 == 0 else 0.0) + math.sin(i / 3.0) * 8
        bars.append(Candle(1_700_000_000 + i * 3600, opn, high, low, close, vol))
    return bars


def ramp(n, step):
    return [100.0 + i * step for i in range(n)]


# ---------------------------------------------------------------- indicators
def test_indicators():
    print("indicators")
    bars = synth()
    bundle = ind.compute(bars)
    check("every series is input length",
          all(len(v) == len(bars) for v in bundle.values()),
          str({k: len(v) for k, v in bundle.items() if len(v) != len(bars)}))

    check("SMA(10) warms up at index 9",
          ind.sma(ramp(50, 1.0), 10)[8] is None and ind.sma(ramp(50, 1.0), 10)[9] == 104.5)
    check("EMA(10) warms up at index 9",
          ind.ema(ramp(50, 1.0), 10)[8] is None and ind.ema(ramp(50, 1.0), 10)[9] is not None)

    only_up = ind.rsi(ramp(60, 1.0))
    only_down = ind.rsi(ramp(60, -1.0))
    flat = ind.rsi([100.0] * 60)
    check("RSI of a pure uptrend is 100", abs(only_up[-1] - 100.0) < 1e-9, str(only_up[-1]))
    check("RSI of a pure downtrend is 0", abs(only_down[-1]) < 1e-9, str(only_down[-1]))
    check("RSI of a flat series is neutral 50", abs(flat[-1] - 50.0) < 1e-9, str(flat[-1]))
    check("RSI stays inside 0..100",
          all(0 <= v <= 100 for v in ind.rsi([b.close for b in bars]) if v is not None))

    vr = ind.volume_ratio(bars, 20)
    check("volume ratio is ~1.0 on an average bar",
          any(v is not None and 0.5 < v < 1.6 for v in vr))
    check("volume ratio spikes on the seeded bar", max(v for v in vr if v is not None) > 1.4)

    atr = ind.atr(bars)
    check("ATR is positive once warmed", all(v > 0 for v in atr if v is not None))

    whale = ind.whale_momentum(bars)
    check("whale-momentum is bounded to -100..100",
          all(-100 <= v <= 100 for v in whale if v is not None))

    lv = ind.levels(bars, top=4)
    check("levels come back sorted by touches",
          lv == sorted(lv, key=lambda x: (-x["touches"], -x["last_index"])))
    span = max((x["price"] for x in lv), default=0) - min((x["price"] for x in lv), default=0)
    check("no runaway cluster (a level is a band, not the whole range)",
          all(x["touches"] < len(bars) * 0.5 for x in lv), "span=%.2f" % span)


# ---------------------------------------------------------------- parser
def test_brief():
    print("brief parser")
    spec = brief.parse("Find me all BTC futures with RSI below 30 and volume +200% "
                       "at the same time")
    kinds = [(f["left"]["kind"], f["op"], f["right"]) for f in spec["filters"]]
    check("reads 'RSI below 30'", ("rsi", "<", 30.0) in kinds, str(kinds))
    check("reads 'volume +200%' as 3.0x", ("vol_ratio", ">", 3.0) in kinds, str(kinds))
    check("spots the named market", spec["symbols"] == ["BTC"], str(spec["symbols"]))
    check("says spot, not futures",
          any("spot" in n for n in spec["notes"]), str(spec["notes"]))
    check("scan is in the plan", "scan" in spec["actions"], str(spec["actions"]))

    tf = brief.parse("scan the market on the 4 hour for RSI above 70")
    check("rounds 4h to a bar the feed has", tf["timeframe"] == "6h", tf["timeframe"])
    check("'scan the market' means whole market", tf["whole_market"])
    check("reads 'RSI above 70'",
          tf["filters"][0]["op"] == ">" and tf["filters"][0]["right"] == 70.0)

    ma = brief.parse("show me BTC where price above the 200 EMA")
    check("compares price to another series",
          isinstance(ma["filters"][0]["right"], dict)
          and ma["filters"][0]["right"]["kind"] == "ema"
          and ma["filters"][0]["right"]["length"] == 200, str(ma["filters"]))

    first = brief.parse("find BTC with RSI below 30")
    follow = brief.parse("now replay last week and show where my system entered",
                         previous=first)
    check("a follow-up inherits the conditions",
          len(follow["filters"]) == 1 and follow["symbols"] == ["BTC"])
    check("a follow-up plans the replay", "replay" in follow["actions"], str(follow["actions"]))

    bare = brief.parse("replay last week")
    check("nothing to backtest without conditions",
          "backtest" not in bare["actions"], str(bare["actions"]))

    stops = brief.parse("backtest BTC with RSI below 30, 1.5 ATR stop, 3% target, hold 10 bars")
    st = stops["strategy"]
    check("reads an ATR stop", st["atr_stop"] == 1.5, str(st))
    check("reads a % target", st["target_pct"] == 3.0, str(st))
    check("reads a max hold", st["max_hold"] == 10, str(st))


# ---------------------------------------------------------------- scan
def test_scan():
    print("scanner")
    bars = synth()
    filters = [{"left": {"kind": "rsi", "length": 14}, "op": "<", "right": 45.0,
                "text": "RSI(14) below 45"}]
    hits, cache = scan.hits(bars, filters)
    check("finds hits on synthetic data", len(hits) > 0, str(len(hits)))
    rsi = ind.rsi([b.close for b in bars])
    check("every hit really satisfies the condition",
          all(rsi[i] is not None and rsi[i] < 45.0 for i in hits))
    check("no hit during warm-up", all(rsi[i] is not None for i in hits))

    impossible = [{"left": {"kind": "rsi", "length": 14}, "op": "<", "right": -5.0,
                   "text": "RSI below -5"}]
    check("an impossible condition finds nothing", scan.hits(bars, impossible)[0] == [])


def test_crossings():
    print("crossings")
    # closes walk 95 -> 105, crossing 100 exactly once
    up = [Candle(1_700_000_000 + i * 3600, 95.0 + i, 95.5 + i, 94.5 + i, 95.0 + i, 100.0)
          for i in range(11)]
    above = [{"left": {"kind": "close"}, "op": "crosses_above", "right": 100.0,
              "text": "close crosses above 100"}]
    fired, _ = scan.hits(up, above)
    check("a cross fires once, not on every bar above", len(fired) == 1, str(fired))
    check("it fires on the bar that broke through",
          fired and up[fired[0]].close > 100 and up[fired[0] - 1].close <= 100)

    below = [{"left": {"kind": "close"}, "op": "crosses_below", "right": 100.0,
              "text": "close crosses below 100"}]
    check("a rising series never crosses down", scan.hits(up, below)[0] == [])
    down = list(reversed([b._replace(ts=1_700_000_000 + i * 3600)
                          for i, b in enumerate(up)]))
    check("a falling series crosses down once", len(scan.hits(down, below)[0]) == 1)

    # touching the level without breaking it is not a cross
    flat = [Candle(1_700_000_000 + i * 3600, 99.0, 100.0, 98.0, 100.0, 100.0)
            for i in range(10)]
    check("sitting exactly on the level is not a cross", scan.hits(flat, above)[0] == [])

    check("bar 0 can never be a cross (no bar before it)",
          0 not in scan.hits(up, above)[0])

    spec = brief.parse("find BTC where macd crosses above its signal")
    f = spec["filters"][0]
    check("parses 'crosses above its signal'",
          f["op"] == "crosses_above" and f["right"]["kind"] == "macd_signal", str(f))
    spec = brief.parse("find BTC where price crosses back above the 200 EMA")
    f = spec["filters"][0]
    check("parses 'crosses back above the 200 EMA'",
          f["op"] == "crosses_above" and f["right"] == {"kind": "ema", "length": 200},
          str(f))
    spec = brief.parse("find BTC where rsi crosses below 30")
    check("parses 'rsi crosses below 30'",
          spec["filters"][0]["op"] == "crosses_below" and spec["filters"][0]["right"] == 30.0)
    spec = brief.parse("find BTC where rsi crosses above 30")
    check("a crossing is not also read as a plain comparison",
          len(spec["filters"]) == 1, str(spec["filters"]))


def test_exits():
    print("exit rules")
    spec = brief.parse("backtest BTC with rsi below 30, exit when rsi goes above 70, "
                       "2% stop, 5% target")
    st = spec["strategy"]
    check("splits the exit clause off the entry rules",
          len(spec["filters"]) == 1 and spec["filters"][0]["right"] == 30.0,
          str(spec["filters"]))
    check("reads the exit condition",
          len(st["exit"]) == 1 and st["exit"][0]["right"] == 70.0, str(st["exit"]))
    check("the exit clause doesn't swallow the stop", st["stop_pct"] == 2.0, str(st))
    check("the exit clause doesn't swallow the target", st["target_pct"] == 5.0, str(st))

    spec = brief.parse("backtest BTC with rsi below 30, exit when the vibes are bad")
    check("an unreadable exit rule is reported, not invented",
          not spec["strategy"]["exit"]
          and any("couldn't read an exit rule" in n for n in spec["notes"]),
          str(spec["notes"]))
    check("...and it doesn't eat the entry rules either", len(spec["filters"]) == 1)

    # an exit condition that is true from bar 5 onward should close the trade there
    bars = [Candle(1_700_000_000 + i * 3600, 100.0, 100.4, 99.8, 100.0 + (i >= 5) * 0.2,
                   100.0) for i in range(40)]
    always = [{"left": {"kind": "close"}, "op": ">", "right": 0.0, "text": "always"}]
    on_signal = [{"left": {"kind": "close"}, "op": ">", "right": 100.1,
                  "text": "close above 100.1"}]
    result = backtest.run(bars, _spec_for(always, exit=on_signal,
                                          stop_pct=50.0, target_pct=50.0))
    trades = result["trades"]
    check("a signal exit closes the trade", trades and trades[0]["reason"] == "signal",
          str(trades[:1]))
    check("a signal exit fills at that bar's close",
          trades and trades[0]["exit"] == bars[trades[0]["exit_index"]].close)
    check("stop and target still win over a later signal",
          backtest.run(bars, _spec_for(always, exit=on_signal, stop_pct=0.05,
                                       target_pct=50.0))["trades"][0]["reason"] == "stop")
    check("the exit rule is listed in the assumptions",
          "exit_rule" in result["assumptions"], str(result["assumptions"].keys()))


def test_universe():
    print("universe resolution")
    import feed
    listed = ["BTC-USD", "ETH-USD", "SOL-USD", "ESP-USD", "USELESS-USD", "BTC-EUR"]
    real = feed.products
    # stand in for the venue, filtering by quote the way the real call does
    feed.products = lambda quotes=("USD",), fresh=False: [
        p for p in listed if p.split("-")[1] in quotes]
    try:
        check("an exact base resolves", feed.resolve("BTC") == ["BTC-USD"],
              str(feed.resolve("BTC")))
        check("a base with several quotes resolves to all of them",
              feed.resolve("BTC", quotes=("USD", "EUR")) == ["BTC-USD", "BTC-EUR"],
              str(feed.resolve("BTC", quotes=("USD", "EUR"))))
        check("a full product id resolves", feed.resolve("SOL-USD") == ["SOL-USD"])
        check("matching is case-insensitive", feed.resolve("eth") == ["ETH-USD"])
        check("no loose substring match — 'ES' is not USELESS",
              feed.resolve("ES") == [], str(feed.resolve("ES")))
        check("an unlisted ticker resolves to nothing", feed.resolve("AAPL") == [])

        mixed = {"whole_market": False, "symbols": ["AAPL", "SOL"], "universe_size": 10}
        products, unlisted = scan.resolve_universe(mixed)
        check("unlisted symbols are reported back", unlisted == ["AAPL"], str(unlisted))
        check("listed symbols still resolve alongside them", products == ["SOL-USD"],
              str(products))

        none = {"whole_market": False, "symbols": ["AAPL"], "universe_size": 10}
        products, unlisted = scan.resolve_universe(none)
        check("nothing listed gives an empty universe, not a silent BTC fallback",
              products == [], str(products))
    finally:
        feed.products = real


def test_watch_clock():
    print("watch clock")
    import tapedeck
    import feed
    # 2026-07-30 00:17:00 UTC — mid-bar on every timeframe
    now = 1785370620
    for tf, expect in (("1m", 60), ("15m", 780), ("1h", 2580), ("1d", 85380)):
        nxt = tapedeck.next_bar_close(tf, now)
        check("%s bar closes in %ds" % (tf, expect), nxt - now == expect,
              "got +%ds" % (nxt - now))
        check("%s close lands on a bar boundary" % tf, nxt % feed.TIMEFRAMES[tf] == 0)
    exactly_on = tapedeck.next_bar_close("1h", 1785369600)
    check("on a boundary it waits for the NEXT bar, not this one",
          exactly_on == 1785369600 + 3600, str(exactly_on))
    check("countdown formats coarsely", tapedeck._countdown(3725) == "1h02m",
          tapedeck._countdown(3725))
    check("countdown formats minutes", tapedeck._countdown(95) == "1m35s",
          tapedeck._countdown(95))


def test_cache_rules():
    print("feed cache")
    import feed
    entry = {"bars": [0] * 260, "asked": 260}
    check("260 cached bars cannot answer a 700-bar request",
          not feed._cache_covers(entry, 700))
    check("260 cached bars answer a 200-bar request",
          feed._cache_covers(entry, 200))
    check("a short venue history answers a larger request",
          feed._cache_covers({"bars": [0] * 350, "asked": 900}, 700))
    check("an exact-size cache answers its own size",
          feed._cache_covers(entry, 260))


# ---------------------------------------------------------------- backtest
def _spec_for(filters, **strategy):
    base = dict(direction="long", entry=filters, exit=[], stop_pct=2.0, atr_stop=None,
                target_pct=4.0, max_hold=48)
    base.update(strategy)
    return {"strategy": base, "timeframe": "1h", "filters": filters,
            "raw": "test", "notes": [], "actions": ["backtest"]}


def test_backtest():
    print("backtester")
    bars = synth()
    filters = [{"left": {"kind": "rsi", "length": 14}, "op": "<", "right": 45.0,
                "text": "RSI(14) below 45"}]
    result = backtest.run(bars, _spec_for(filters))
    trades = result["trades"]
    check("produces trades", len(trades) > 0, str(len(trades)))

    check("entry is always the bar AFTER the signal (no look-ahead)",
          all(t["entry_index"] == t["signal_index"] + 1 for t in trades))
    check("entry fills at that bar's open",
          all(t["entry"] == bars[t["entry_index"]].open for t in trades))
    check("exit never precedes entry", all(t["exit_index"] >= t["entry_index"] for t in trades))
    check("max hold is respected",
          all(t["exit_index"] - t["entry_index"] <= 48 for t in trades))
    check("only one position at a time",
          all(trades[i]["entry_index"] > trades[i - 1]["exit_index"]
              for i in range(1, len(trades))))
    check("signals include bars skipped by an open position",
          len(result["signals"]) >= len(trades), "%d signals, %d trades"
          % (len(result["signals"]), len(trades)))

    for t in trades:
        if t["reason"] == "stop":
            ok = bars[t["exit_index"]].low <= t["stop"]
        elif t["reason"] == "target":
            ok = bars[t["exit_index"]].high >= t["target"]
        else:
            ok = t["exit"] == bars[t["exit_index"]].close
        if not ok:
            check("exit price matches its stated reason (%s)" % t["reason"], False,
                  "trade at %d" % t["entry_index"])
            break
    else:
        check("every exit price matches its stated reason", True)

    check("costs make net worse than gross",
          all(t["net_pct"] < t["gross_pct"] for t in trades))
    free = backtest.run(bars, _spec_for(filters), fee_pct=0, slippage_pct=0)
    check("zero-cost run scores higher than the costed one",
          free["stats"]["total_pct"] > result["stats"]["total_pct"])

    stats = result["stats"]
    wins = sum(1 for t in trades if t["net_pct"] > 0)
    check("hit rate matches the trade list",
          abs(stats["hit_rate"] - wins / len(trades) * 100) < 1e-9)
    check("summed PnL matches the trade list",
          abs(stats["pnl"] - sum(t["pnl"] for t in trades)) < 1e-9)
    check("drawdown is never negative", stats["max_drawdown"] >= 0)

    # stop must win when both stop and target sit inside the same bar
    both = [Candle(1_700_000_000 + i * 3600, 100.0, 100.5, 99.5, 100.0, 100.0)
            for i in range(30)]
    both.append(Candle(1_700_000_000 + 30 * 3600, 100.0, 110.0, 90.0, 100.0, 100.0))
    always = [{"left": {"kind": "close"}, "op": ">", "right": 0.0, "text": "always"}]
    pinned = backtest.run(both, _spec_for(always, stop_pct=2.0, target_pct=2.0))
    check("stop wins when stop and target share a bar",
          pinned["trades"] and pinned["trades"][0]["reason"] == "stop",
          str(pinned["trades"][:1]))

    empty = backtest.run(bars, _spec_for([]))
    check("no conditions means no trades and no crash", empty["trades"] == [])
    check("empty stats are still well formed", empty["stats"]["trades"] == 0)

    short = backtest.run(bars, _spec_for(filters, direction="short"))
    check("a short run produces trades too", len(short["trades"]) > 0)
    check("short PnL is the mirror of the move",
          all((t["gross_pct"] > 0) == (t["exit"] < t["entry"]) for t in short["trades"]))


def main():
    print("Tapedeck self-test — offline, synthetic data\n")
    test_indicators(); print()
    test_brief(); print()
    test_scan(); print()
    test_crossings(); print()
    test_exits(); print()
    test_universe(); print()
    test_watch_clock(); print()
    test_cache_rules(); print()
    test_backtest(); print()
    if FAILED:
        print("%d check(s) FAILED:" % len(FAILED))
        for name in FAILED:
            print("  - %s" % name)
        return 1
    print("all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
