#!/usr/bin/env python3
"""
Tapedeck — the part that tries to talk you out of it.

`backtest.py` answers "what would these rules have done?". This module answers
the only question that actually matters before risking money:

    IS THAT RESULT REAL, OR IS IT NOISE THAT LOOKS LIKE A RESULT?

Almost every retail strategy dies at this step, and almost none of them are
tested for it. A search over a few hundred rule combinations will always produce
something with a beautiful equity curve. That is not a discovery — it is the
guaranteed arithmetic consequence of looking at a few hundred things. This module
exists to take that beautiful curve away from you when it deserves to be taken.

Four tests, each of which kills a different kind of self-deception:

  1. RANDOM-ENTRY BASELINE  (kills "my signal is doing something")
     Run the same trade count, the same stop, the same target, the same holding
     period — but enter on RANDOMLY CHOSEN BARS. Do it a thousand times. If your
     signal cannot beat the 95th percentile of dice rolls, your signal is a dice
     roll. This is the single most useful test in the file and the one people
     skip, because it usually says no.

  2. WALK-FORWARD  (kills "it works on the data I tuned it on")
     Pick the best parameters using ONLY data up to a point, then score them on
     data that came after. Repeat, rolling forward. In-sample performance is a
     measure of how well you fitted; only out-of-sample performance is evidence.
     The gap between the two is your overfitting, quantified.

  3. MULTIPLE-TESTING CORRECTION  (kills "the best of my 500 tests looks great")
     The maximum of N random draws grows with N. Testing 500 rules and reporting
     the winner's t-statistic is meaningless without adjusting for the fact that
     you took a maximum. `expected_max_t` says how good the best of N pure-noise
     strategies would look, so you can check whether yours beat that bar.

  4. BUY-AND-HOLD AND EXPOSURE  (kills "I made money" when you just held)
     A long-only strategy in a rising market makes money by existing. Every
     result here is reported next to buy-and-hold over the same window, and next
     to the fraction of time the strategy was actually exposed. A return that
     tracks exposure is beta wearing a costume.

Nothing in this module can tell you a strategy WILL work. It can only tell you
that one has failed to prove it doesn't — which is the strongest statement
honest backtesting is capable of making.
"""
import math
import random
import time

import backtest
import indicators as ind

CONF = 0.95


# ---------------------------------------------------------------- spec building
def ref(kind, length=None):
    return {"kind": kind, "length": length}


def cond(left, op, right, text):
    return {"left": left, "op": op, "right": right, "text": text}


def make_spec(filters, timeframe="1h", direction="long", stop_pct=2.0, atr_stop=None,
              target_pct=4.0, max_hold=48, exit_filters=None, label=""):
    """
    A spec the existing backtester understands, built directly rather than parsed.

    The English parser is for humans; a search needs to enumerate thousands of
    combinations, so it constructs the same structure by hand.
    """
    return {
        "raw": label or " and ".join(f["text"] for f in filters),
        "timeframe": timeframe,
        "symbols": [], "whole_market": False,
        "filters": filters,
        "strategy": {
            "direction": direction, "entry": filters, "exit": exit_filters or [],
            "stop_pct": stop_pct, "atr_stop": atr_stop,
            "target_pct": target_pct, "max_hold": max_hold,
        },
        "actions": ["backtest"], "replay_bars": 0, "universe_size": 1, "notes": [],
    }


# ---------------------------------------------------------------- the candidate space
def entry_conditions():
    """
    Single conditions the search can combine, as (key, family, filter) triples.

    `family` names the underlying indicator so `candidates()` can refuse to stack
    two conditions on the same one. Carrying it explicitly beats inferring it from
    the key string: "rsi14<30" and "rsi14>70" are the same indicator, and any
    scheme that splits the key on an operator gets that wrong for half the pairs.

    Deliberately ordinary: these are the rules retail systems are actually built
    from. If an edge exists in this vocabulary the search will find it, and if it
    doesn't, that is worth knowing too.
    """
    out = []
    for length in (7, 14, 21):
        for level in (20, 25, 30, 35, 40):
            out.append(("rsi%d<%d" % (length, level), "rsi%d" % length,
                        cond(ref("rsi", length), "<", float(level),
                             "RSI(%d) below %d" % (length, level))))
        for level in (60, 65, 70, 75, 80):
            out.append(("rsi%d>%d" % (length, level), "rsi%d" % length,
                        cond(ref("rsi", length), ">", float(level),
                             "RSI(%d) above %d" % (length, level))))
        out.append(("rsi%dx30" % length, "rsi%d" % length,
                    cond(ref("rsi", length), "crosses_above", 30.0,
                         "RSI(%d) crosses above 30" % length)))
        out.append(("rsi%dx70" % length, "rsi%d" % length,
                    cond(ref("rsi", length), "crosses_below", 70.0,
                         "RSI(%d) crosses below 70" % length)))
    for ratio in (1.5, 2.0, 3.0, 5.0):
        out.append(("vol>%.1f" % ratio, "volume",
                    cond(ref("vol_ratio", 20), ">", ratio,
                         "volume above %.1fx its 20-bar average" % ratio)))
    for length in (20, 50, 200):
        out.append(("px>ema%d" % length, "ema%d" % length,
                    cond(ref("close"), ">", ref("ema", length),
                         "close above the %d EMA" % length)))
        out.append(("px<ema%d" % length, "ema%d" % length,
                    cond(ref("close"), "<", ref("ema", length),
                         "close below the %d EMA" % length)))
        out.append(("pxXema%d" % length, "ema%d" % length,
                    cond(ref("close"), "crosses_above", ref("ema", length),
                         "close crosses above the %d EMA" % length)))
    out.append(("macd>0", "macd", cond(ref("macd_hist"), ">", 0.0, "MACD histogram positive")))
    out.append(("macd<0", "macd", cond(ref("macd_hist"), "<", 0.0, "MACD histogram negative")))
    out.append(("macdXsig", "macd", cond(ref("macd"), "crosses_above", ref("macd_signal"),
                                 "MACD crosses above its signal")))
    out.append(("px<bbl", "bollinger", cond(ref("close"), "<", ref("bb_lower", 20),
                               "close below the lower Bollinger band")))
    out.append(("px>bbu", "bollinger", cond(ref("close"), ">", ref("bb_upper", 20),
                               "close above the upper Bollinger band")))
    out.append(("whale>20", "whale", cond(ref("whale"), ">", 20.0, "whale-momentum above 20")))
    out.append(("whale<-20", "whale", cond(ref("whale"), "<", -20.0, "whale-momentum below -20")))
    return out


EXITS = [
    dict(atr_stop=1.5, target_pct=3.0, max_hold=24),
    dict(atr_stop=2.0, target_pct=4.0, max_hold=24),
    dict(atr_stop=2.0, target_pct=6.0, max_hold=48),
    dict(stop_pct=2.0, target_pct=4.0, max_hold=24),
    dict(stop_pct=3.0, target_pct=6.0, max_hold=48),
]


def candidates(max_conditions=2, limit=None, seed=7):
    """Every rule combination the search will try."""
    singles = entry_conditions()
    out = []
    for key, _family, filt in singles:
        for exit_spec in EXITS:
            out.append((key, [filt], exit_spec))
    if max_conditions >= 2:
        for i, (key_a, family_a, filt_a) in enumerate(singles):
            for key_b, family_b, filt_b in singles[i + 1:]:
                if family_a == family_b:
                    continue                    # same indicator, don't stack it
                for exit_spec in EXITS:
                    out.append(("%s + %s" % (key_a, key_b), [filt_a, filt_b], exit_spec))
    if limit and len(out) > limit:
        random.Random(seed).shuffle(out)
        out = out[:limit]
    return out


# ---------------------------------------------------------------- statistics
def mean(values):
    return sum(values) / len(values) if values else 0.0


def stdev(values):
    if len(values) < 2:
        return 0.0
    m = mean(values)
    return math.sqrt(sum((v - m) ** 2 for v in values) / (len(values) - 1))


def t_stat(returns):
    """How many standard errors above zero the average trade is."""
    if len(returns) < 2:
        return 0.0
    sd = stdev(returns)
    if sd == 0:
        return 0.0
    return mean(returns) / (sd / math.sqrt(len(returns)))


def expected_max_t(trials):
    """
    How big the best t-statistic out of `trials` PURE NOISE strategies would be.

    This is the bar a search result has to clear. Testing 500 rules and finding
    one with t = 2.5 sounds impressive until you learn that the best of 500 coin
    flips scores about 3.2 by construction. Uses the standard approximation for
    the expected maximum of n standard normals.
    """
    if trials < 2:
        return 0.0
    return math.sqrt(2 * math.log(trials)) - (
        math.log(math.log(trials)) + math.log(4 * math.pi)) / (
        2 * math.sqrt(2 * math.log(trials)))


def bootstrap_ci(returns, iterations=2000, conf=CONF, seed=11):
    """
    Confidence interval for the mean trade return, by resampling the trades.

    Makes no assumption that returns are normal — which they are not, being a
    pile of small stops and occasional targets. If the interval includes zero,
    the strategy has not demonstrated a positive expectancy.
    """
    if len(returns) < 3:
        return (None, None)
    rng = random.Random(seed)
    n = len(returns)
    means = []
    for _ in range(iterations):
        means.append(mean([returns[rng.randrange(n)] for _ in range(n)]))
    means.sort()
    low = means[int((1 - conf) / 2 * iterations)]
    high = means[min(iterations - 1, int((1 + conf) / 2 * iterations))]
    return (low, high)


# ---------------------------------------------------------------- baselines
def buy_and_hold(bars):
    return (bars[-1].close - bars[0].close) / bars[0].close * 100.0


def exposure(result, bars):
    """Fraction of the window spent holding anything, as a percentage."""
    if not bars:
        return 0.0
    held = sum(t["bars_held"] for t in result["trades"])
    return held / len(bars) * 100.0


def random_entry_baseline(bars, spec, trade_count, iterations=500, seed=13):
    """
    The dice-roll comparison: same exits, same trade count, random entry bars.

    Returns the distribution of total returns. A real signal has to sit in the
    top tail of this. Most do not, and finding that out here costs nothing.
    """
    if trade_count <= 0 or len(bars) < 100:
        return []
    rng = random.Random(seed)
    st = spec["strategy"]
    atr_series = ind.atr(bars) if st.get("atr_stop") else [None] * len(bars)
    long = st["direction"] == "long"
    cost = (backtest.FEE_PCT + backtest.SLIPPAGE_PCT) / 100.0
    n = len(bars)
    out = []

    for _ in range(iterations):
        total = 0.0
        for _ in range(trade_count):
            i = rng.randrange(30, n - 2)            # leave warm-up and room to exit
            entry_index = i + 1
            entry = bars[entry_index].open
            if st.get("atr_stop") and atr_series[i]:
                risk = st["atr_stop"] * atr_series[i]
            else:
                risk = entry * st["stop_pct"] / 100.0
            stop = entry - risk if long else entry + risk
            gain = entry * st["target_pct"] / 100.0
            target = entry + gain if long else entry - gain

            limit = min(entry_index + st["max_hold"], n - 1)
            exit_price = bars[limit].close
            for j in range(entry_index, limit + 1):
                b = bars[j]
                if (b.low <= stop) if long else (b.high >= stop):
                    exit_price = stop
                    break
                if (b.high >= target) if long else (b.low <= target):
                    exit_price = target
                    break
            move = (exit_price - entry) if long else (entry - exit_price)
            total += move / entry * 100.0 - cost * 200.0
        out.append(total)
    out.sort()
    return out


def percentile_of(value, distribution):
    """Where `value` sits in `distribution`, 0-100."""
    if not distribution:
        return None
    below = sum(1 for d in distribution if d < value)
    return below / len(distribution) * 100.0


# ---------------------------------------------------------------- walk-forward
def fold_bounds(total, folds, warmup=200):
    """Chronological, non-overlapping test windows after a warm-up."""
    usable = total - warmup
    if usable <= 0 or folds < 1:
        return []
    size = usable // folds
    if size < 50:
        return []
    return [(warmup + i * size, warmup + (i + 1) * size if i < folds - 1 else total)
            for i in range(folds)]


def walk_forward(bars, pool, folds=4, warmup=200, progress=None):
    """
    The honest procedure.

    For each test window: choose the best candidate using ONLY the bars BEFORE
    that window, then score that choice on the window itself. The selection never
    sees the data it is judged on.

    Returns dict with per-fold out-of-sample results and the aggregate.
    """
    windows = fold_bounds(len(bars), folds, warmup)
    if not windows:
        return {"folds": [], "oos_returns": [], "error": "not enough history"}

    results = []
    for number, (start, end) in enumerate(windows, 1):
        in_sample = bars[:start]
        out_sample = bars[start:end]
        if len(in_sample) < warmup or len(out_sample) < 30:
            continue

        best, best_score = None, None
        for key, filters, exit_spec in pool:
            spec = make_spec(filters, label=key, **exit_spec)
            stats = backtest.run(in_sample, spec)["stats"]
            if stats["trades"] < 5:
                continue
            score = stats["total_pct"]
            if best_score is None or score > best_score:
                best, best_score = (key, filters, exit_spec), score
        if best is None:
            continue

        key, filters, exit_spec = best
        spec = make_spec(filters, label=key, **exit_spec)
        oos = backtest.run(out_sample, spec)
        results.append({
            "fold": number,
            "chosen": key,
            "in_sample_pct": best_score,
            "oos_pct": oos["stats"]["total_pct"],
            "oos_trades": oos["stats"]["trades"],
            "oos_returns": [t["net_pct"] for t in oos["trades"]],
            "buy_hold_pct": buy_and_hold(out_sample),
            "exposure_pct": exposure(oos, out_sample),
        })
        if progress:
            progress(number, len(windows), key)

    every_return = [r for f in results for r in f["oos_returns"]]
    return {
        "folds": results,
        "oos_returns": every_return,
        "oos_total": sum(f["oos_pct"] for f in results),
        "in_sample_total": sum(f["in_sample_pct"] for f in results),
        "buy_hold_total": sum(f["buy_hold_pct"] for f in results),
    }


# ---------------------------------------------------------------- verdict
def verdict(oos_returns, trials, random_percentile, oos_total, buy_hold_total):
    """
    The summary sentence, and it is allowed to be rude.

    Every branch that returns "no" is a branch that saves money.
    """
    reasons = []
    if len(oos_returns) < 20:
        reasons.append("only %d out-of-sample trades — far too few to conclude "
                       "anything either way" % len(oos_returns))
    t = t_stat(oos_returns)
    bar = expected_max_t(trials)
    if t < 2.0:
        reasons.append("out-of-sample t-statistic %.2f is below 2.0 — not "
                       "distinguishable from luck" % t)
    if t < bar:
        reasons.append("t-statistic %.2f does not clear the %.2f a search over %d "
                       "candidates would reach on pure noise" % (t, bar, trials))
    low, high = bootstrap_ci(oos_returns)
    if low is not None and low <= 0:
        reasons.append("the 95%% confidence interval for the average trade "
                       "(%+.3f%% to %+.3f%%) includes zero" % (low, high))
    if random_percentile is not None and random_percentile < 95:
        reasons.append("it beat only %.0f%% of random-entry runs with the same "
                       "exits — a signal should beat 95%%" % random_percentile)
    if oos_total <= buy_hold_total:
        reasons.append("buy-and-hold returned %+.2f%% over the same windows "
                       "against the strategy's %+.2f%%" % (buy_hold_total, oos_total))
    return (not reasons), reasons


def render(name, wf, random_dist, trials):
    lines = ["", "=" * 74, "%s" % name, "=" * 74]
    if not wf["folds"]:
        lines.append("  Not enough history to walk forward. No verdict.")
        return "\n".join(lines)

    lines.append("%-6s %-22s %11s %11s %11s %9s"
                 % ("fold", "chosen in-sample", "in-samp%", "OOS%", "buy&hold%", "in-mkt%"))
    for f in wf["folds"]:
        lines.append("%-6d %-22s %+11.2f %+11.2f %+11.2f %8.1f%%"
                     % (f["fold"], f["chosen"][:22], f["in_sample_pct"], f["oos_pct"],
                        f["buy_hold_pct"], f["exposure_pct"]))

    oos = wf["oos_returns"]
    lines += ["", "  in-sample total   %+.2f%%   <- what fitting the data looks like"
              % wf["in_sample_total"],
              "  OUT-OF-SAMPLE     %+.2f%%   <- the only number that is evidence"
              % wf["oos_total"],
              "  buy & hold        %+.2f%%   <- the bar it has to clear"
              % wf["buy_hold_total"]]
    decay = wf["in_sample_total"] - wf["oos_total"]
    lines.append("  overfit gap       %+.2f points lost between fitting and testing"
                 % decay)

    if oos:
        low, high = bootstrap_ci(oos)
        lines += ["", "  OOS trades        %d" % len(oos),
                  "  mean per trade    %+.3f%%" % mean(oos),
                  "  t-statistic       %.2f  (needs > 2.0, and > %.2f to beat a "
                  "%d-candidate search on noise)" % (t_stat(oos),
                                                     expected_max_t(trials), trials)]
        if low is not None:
            lines.append("  95%% CI per trade  %+.3f%% to %+.3f%%%s"
                         % (low, high, "   <- includes zero" if low <= 0 else ""))

    pct = None
    if random_dist:
        pct = percentile_of(wf["oos_total"], random_dist)
        lines += ["", "  random-entry baseline (same exits, %d runs)" % len(random_dist),
                  "    median dice roll  %+.2f%%" % random_dist[len(random_dist) // 2],
                  "    95th percentile   %+.2f%%" % random_dist[int(len(random_dist) * 0.95)],
                  "    this strategy     %+.2f%%  -> beats %.0f%% of random entries"
                  % (wf["oos_total"], pct)]

    good, reasons = verdict(oos, trials, pct, wf["oos_total"], wf["buy_hold_total"])
    lines += ["", "  VERDICT: %s" % ("survives every test in this file — a candidate, "
                                     "not a conclusion" if good else "NOT PROVEN")]
    for reason in reasons:
        lines.append("    - %s" % reason)
    if good:
        lines.append("    Next: paper trade it for months before it sees money.")
    return "\n".join(lines)


if __name__ == "__main__":
    import sys

    import feed

    product = sys.argv[1] if len(sys.argv) > 1 else "BTC-USD"
    timeframe = sys.argv[2] if len(sys.argv) > 2 else "1h"
    depth = int(sys.argv[3]) if len(sys.argv) > 3 else 3000

    print("Loading %s %s ..." % (product, timeframe))
    bars = feed.candles(product, timeframe, depth)
    print("  %d bars, %s -> %s UTC" % (
        len(bars), time.strftime("%Y-%m-%d", time.gmtime(bars[0].ts)),
        time.strftime("%Y-%m-%d", time.gmtime(bars[-1].ts))))

    pool = candidates(max_conditions=1)
    print("  %d candidate rule sets" % len(pool))
    wf = walk_forward(bars, pool, folds=4)
    dist = []
    if wf["folds"]:
        dist = random_entry_baseline(bars, make_spec([], **EXITS[0]),
                                     len(wf["oos_returns"]), iterations=400)
    print(render("%s %s — walk-forward" % (product, timeframe), wf, dist, len(pool)))
