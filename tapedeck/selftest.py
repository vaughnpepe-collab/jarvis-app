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


# ---------------------------------------------------------------- backtest
def _spec_for(filters, **strategy):
    base = dict(direction="long", entry=filters, stop_pct=2.0, atr_stop=None,
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
