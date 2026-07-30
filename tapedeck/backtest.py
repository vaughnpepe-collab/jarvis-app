#!/usr/bin/env python3
"""
Tapedeck — backtester.

Runs a parsed brief's conditions over historical bars and reports what the rules
would have done. Two commitments that separate this from a screenshot of a
number someone liked:

  1. NO LOOK-AHEAD. A condition is evaluated on a *closed* bar; the position
     opens at the **next bar's open**. You cannot buy the candle that told you
     to buy.
  2. COSTS ARE ON BY DEFAULT. `FEE_PCT` per side and `SLIPPAGE_PCT` per side are
     applied to every fill. Set them to zero if you want the fantasy number, but
     you have to do it on purpose.

When stop and target both sit inside the same bar, the stop is taken — the bar
doesn't say which came first, so the result takes the worse branch rather than
the flattering one.

A backtest is a description of the past under assumptions. It is not a
prediction, and this module does not place orders — there is no order path in
this project. Read `caveats()` alongside any result.
"""
import time

import brief
import indicators as ind
import scan

FEE_PCT = 0.10          # per side, taker-ish
SLIPPAGE_PCT = 0.05     # per side
STAKE = 1000.0          # notional per trade, fixed (no compounding)


def run(bars, spec, stake=STAKE, fee_pct=FEE_PCT, slippage_pct=SLIPPAGE_PCT):
    """
    Returns dict(trades=[...], stats={...}, assumptions={...}).

    One position at a time — a fresh signal while a trade is open is ignored,
    which is what "my system" almost always means in practice.
    """
    st = spec["strategy"]
    filters = st["entry"]
    if not filters:
        return dict(trades=[], stats=_stats([], stake), assumptions=_assumptions(
            st, stake, fee_pct, slippage_pct), signals=[])

    cache = scan.build_series(bars, filters)
    atr_series = ind.atr(bars) if st.get("atr_stop") else [None] * len(bars)
    long = st["direction"] == "long"
    cost = (fee_pct + slippage_pct) / 100.0

    n = len(bars)
    # Every bar the conditions fired, whether or not it became a trade — the walk
    # below skips signals that land inside an open position, and the chart should
    # still show them rather than quietly dropping them.
    signals = [i for i in range(n) if scan.holds(filters, cache, bars, i)]

    trades = []
    i = 0
    while i < n - 1:
        if not scan.holds(filters, cache, bars, i):
            i += 1
            continue

        entry_index = i + 1                       # next bar's open — no look-ahead
        entry_price = bars[entry_index].open
        if st.get("atr_stop") and atr_series[i]:
            risk = st["atr_stop"] * atr_series[i]
            stop = entry_price - risk if long else entry_price + risk
        else:
            risk = entry_price * st["stop_pct"] / 100.0
            stop = entry_price - risk if long else entry_price + risk
        gain = entry_price * st["target_pct"] / 100.0
        target = entry_price + gain if long else entry_price - gain

        exit_index, exit_price, reason = None, None, None
        limit = min(entry_index + st["max_hold"], n - 1)
        for j in range(entry_index, limit + 1):
            bar = bars[j]
            hit_stop = bar.low <= stop if long else bar.high >= stop
            hit_target = bar.high >= target if long else bar.low <= target
            if hit_stop:                          # worse branch first, on purpose
                exit_index, exit_price, reason = j, stop, "stop"
                break
            if hit_target:
                exit_index, exit_price, reason = j, target, "target"
                break
        if exit_index is None:
            exit_index, exit_price, reason = limit, bars[limit].close, "time"

        move = (exit_price - entry_price) if long else (entry_price - exit_price)
        gross_pct = move / entry_price * 100.0
        net_pct = gross_pct - cost * 200.0        # entry + exit
        trades.append({
            "entry_index": entry_index, "exit_index": exit_index,
            "entry_ts": bars[entry_index].ts, "exit_ts": bars[exit_index].ts,
            "signal_index": i, "signal_ts": bars[i].ts,
            "entry": entry_price, "exit": exit_price,
            "stop": stop, "target": target, "reason": reason,
            "bars_held": exit_index - entry_index,
            "gross_pct": gross_pct, "net_pct": net_pct,
            "pnl": stake * net_pct / 100.0,
            "direction": st["direction"],
        })
        i = exit_index + 1                        # flat again before re-arming

    return dict(trades=trades, signals=signals, stats=_stats(trades, stake),
                assumptions=_assumptions(st, stake, fee_pct, slippage_pct))


def _stats(trades, stake):
    if not trades:
        return dict(trades=0, wins=0, losses=0, hit_rate=None, pnl=0.0,
                    total_pct=0.0, avg_pct=None, best_pct=None, worst_pct=None,
                    profit_factor=None, max_drawdown=0.0, avg_bars=None,
                    exits={})
    wins = [t for t in trades if t["net_pct"] > 0]
    losses = [t for t in trades if t["net_pct"] <= 0]
    won = sum(t["pnl"] for t in wins)
    lost = -sum(t["pnl"] for t in losses)

    equity, peak, drawdown = 0.0, 0.0, 0.0
    for t in trades:
        equity += t["pnl"]
        peak = max(peak, equity)
        drawdown = max(drawdown, peak - equity)

    exits = {}
    for t in trades:
        exits[t["reason"]] = exits.get(t["reason"], 0) + 1

    return dict(
        trades=len(trades), wins=len(wins), losses=len(losses),
        hit_rate=len(wins) / len(trades) * 100.0,
        pnl=sum(t["pnl"] for t in trades),
        total_pct=sum(t["net_pct"] for t in trades),
        avg_pct=sum(t["net_pct"] for t in trades) / len(trades),
        best_pct=max(t["net_pct"] for t in trades),
        worst_pct=min(t["net_pct"] for t in trades),
        profit_factor=(won / lost) if lost > 0 else None,
        max_drawdown=drawdown,
        avg_bars=sum(t["bars_held"] for t in trades) / len(trades),
        exits=exits,
    )


def _assumptions(st, stake, fee_pct, slippage_pct):
    stop = ("%.2f x ATR(14)" % st["atr_stop"]) if st.get("atr_stop") else "%g%%" % st["stop_pct"]
    return {
        "direction": st["direction"],
        "stop": stop,
        "target": "%g%%" % st["target_pct"],
        "max_hold": "%d bars" % st["max_hold"],
        "entry_fill": "next bar's open after the signal bar closes",
        "costs": "%.2f%% fee + %.2f%% slippage per side (%.2f%% round trip)"
                 % (fee_pct, slippage_pct, (fee_pct + slippage_pct) * 2),
        "stake": "%s notional per trade, no compounding" % format(stake, ",.0f"),
        "same_bar": "stop taken when stop and target both fall inside one bar",
        "positions": "one at a time; signals during an open trade are ignored",
    }


def caveats():
    return [
        "Past bars only. A backtest cannot tell you what happens next.",
        "Spot data from one venue — no funding, borrow, or futures basis.",
        "Fills assume your size doesn't move the market.",
        "No account for missed bars, outages, or a venue halting the pair.",
        "One instrument at a time; nothing here sizes a portfolio or manages risk.",
    ]


def render(result, product, spec):
    """The terminal report for a single market's backtest."""
    stats, trades = result["stats"], result["trades"]
    lines = ["Backtest — %s %s bars" % (product, spec["timeframe"])]
    if not trades:
        lines.append("  No trades: the conditions never fired in this window.")
        return "\n".join(lines)

    span = "%s → %s UTC" % (
        time.strftime("%Y-%m-%d %H:%M", time.gmtime(trades[0]["entry_ts"])),
        time.strftime("%Y-%m-%d %H:%M", time.gmtime(trades[-1]["exit_ts"])))
    lines += [
        "  %s" % span,
        "",
        "  Trades        %d   (%d won, %d lost)" % (stats["trades"], stats["wins"], stats["losses"]),
        "  Hit rate      %.1f%%" % stats["hit_rate"],
        "  Net result    %+.2f%% summed   %s%s on %s per trade (theoretical)"
        % (stats["total_pct"], "+" if stats["pnl"] >= 0 else "-",
           format(abs(stats["pnl"]), ",.2f"), format(STAKE, ",.0f")),
        "  Average       %+.2f%% per trade over %.1f bars" % (stats["avg_pct"], stats["avg_bars"]),
        "  Best / worst  %+.2f%% / %+.2f%%" % (stats["best_pct"], stats["worst_pct"]),
    ]
    if stats["profit_factor"] is not None:
        lines.append("  Profit factor %.2f" % stats["profit_factor"])
    lines.append("  Max drawdown  %s (peak-to-trough on closed trades)"
                 % format(stats["max_drawdown"], ",.2f"))
    lines.append("  Exits         %s" % ", ".join("%s x%d" % (k, v)
                                                  for k, v in sorted(stats["exits"].items())))
    lines += ["", "  Assumptions"]
    for key, value in result["assumptions"].items():
        lines.append("    %-11s %s" % (key.replace("_", " "), value))
    lines += ["", "  Read with these in mind"]
    for c in caveats():
        lines.append("    - %s" % c)
    return "\n".join(lines)


if __name__ == "__main__":
    import sys

    import feed
    text = " ".join(sys.argv[1:]) or \
        "Backtest BTC with RSI below 35 and volume +100%, 2% stop, 4% target"
    spec = brief.parse(text)
    print(brief.describe(spec))
    print()
    product = scan.universe_for(spec)[0]
    bars = feed.candles(product, spec["timeframe"], brief.DEFAULTS["history"])
    print(render(run(bars, spec), product, spec))
