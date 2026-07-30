#!/usr/bin/env python3
"""
Tapedeck — say what you want to see; it operates the chart.

    python tapedeck.py "find me all BTC markets with RSI below 30 and volume +200%"
    python tapedeck.py "replay last week and show me where my system would have entered"
    python tapedeck.py "show me SOL daily with support and resistance drawn"
    python tapedeck.py "write me a momentum oscillator that crosses whale activity with price trend"

One brief goes in. What comes out: the spec it understood (with every assumption
listed), a scan across the universe, the levels it drew, a backtest of the rules
under stated costs, and a self-contained HTML chart with candle-by-candle replay.

Consecutive runs remember the last brief, so a follow-up can say "my system"
and mean the conditions you just gave. `--new` forgets.

    --top N        markets to rank when scanning the whole market (default 40)
    --charts N     how many matching markets to chart (default 6)
    --history N    bars of history to load per market (default 700)
    --fresh        ignore the cache and refetch
    --open         open the chart when it's written
    --new          start a fresh session
    --quiet        skip the spec echo

Read-only market data. No orders, no keys, no account. Backtests describe past
bars under the assumptions printed beside them — not a forecast, not advice.
"""
import argparse
import json
import os
import sys
import time
import webbrowser

import backtest
import brief
import chart
import feed
import indicators as ind
import scan

SESSION = os.path.join(feed.CACHE, "session.json")


# ---------------------------------------------------------------- session
def load_session():
    try:
        with open(SESSION, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None


def save_session(spec):
    os.makedirs(feed.CACHE, exist_ok=True)
    keep = {k: spec[k] for k in ("raw", "symbols", "whole_market", "timeframe",
                                "filters", "strategy")}
    try:
        with open(SESSION, "w", encoding="utf-8") as fh:
            json.dump(keep, fh)
    except OSError:
        pass


# ---------------------------------------------------------------- actions
def do_indicator(bars, product):
    """Answer 'write me an indicator' with a real, readable one."""
    series = ind.whale_momentum(bars)
    live = [(i, v) for i, v in enumerate(series) if v is not None]
    print("Indicator — whale-momentum (Tapedeck composite)")
    print(ind.whale_momentum.__doc__.rstrip())
    if not live:
        print("  Not enough history on %s to print a reading." % product)
        return
    print("  Latest readings on %s:" % product)
    for i, v in live[-5:]:
        when = time.strftime("%Y-%m-%d %H:%M", time.gmtime(bars[i].ts))
        arrow = "with the trend" if v > 20 else "against the trend" if v < -20 else "quiet"
        print("    %s UTC   %+7.2f   %s" % (when, v, arrow))
    print("  It is plotted on every chart this run writes (hover a candle to read it).")
    print("  Change the formula in indicators.py — it is nine lines.")


def chart_market(product, spec, bars, run_backtest):
    levels = ind.levels(bars, top=5)
    result = (backtest.run(bars, spec) if run_backtest
              else {"trades": [], "signals": [], "stats": {}, "assumptions": {}})
    path = chart.write(product, spec, bars, levels, result, backtest.caveats())
    return path, levels, result


def main(argv=None):
    ap = argparse.ArgumentParser(add_help=True, description="Tapedeck — chart operator.")
    ap.add_argument("brief", nargs="*", help="what you want, in plain English")
    ap.add_argument("--top", type=int, default=None)
    ap.add_argument("--charts", type=int, default=6)
    ap.add_argument("--history", type=int, default=None)
    ap.add_argument("--fresh", action="store_true")
    ap.add_argument("--open", action="store_true")
    ap.add_argument("--new", action="store_true")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args(argv)

    text = " ".join(args.brief).strip()
    if not text:
        print(__doc__.strip())
        return 0

    previous = None if args.new else load_session()
    spec = brief.parse(text, previous=previous)
    if args.top:
        spec["universe_size"] = args.top
    history = args.history or brief.DEFAULTS["history"]

    if not args.quiet:
        print(brief.describe(spec))
        print()

    # ---------------------------------------------------------- scan
    charted, results = [], []
    if "scan" in spec["actions"]:
        results, skipped = scan.run(spec, history=min(history, brief.DEFAULTS["scan_history"]))
        print(scan.render(results, skipped, spec))
        print()
        products = [r["product"] for r in results][:args.charts]
        if not products:
            products = scan.universe_for(spec)[:1]      # still show one chart
            print("Charting %s anyway so there's something to look at.\n" % products[0])
    else:
        products = scan.universe_for(spec)[:max(1, args.charts)]

    # ---------------------------------------------------------- per market
    run_bt = "backtest" in spec["actions"]
    for product in products:
        try:
            bars = feed.candles(product, spec["timeframe"], history, fresh=args.fresh)
        except feed.FeedError as exc:
            print("  ! %s: %s" % (product, exc))
            continue
        if len(bars) < 60:
            print("  ! %s: only %d bars of history" % (product, len(bars)))
            continue

        path, levels, result = chart_market(product, spec, bars, run_bt)
        charted.append({"product": product, "timeframe": spec["timeframe"],
                        "path": path, "brief": spec["raw"],
                        "stats": result.get("stats"),
                        "hits": next((r["count"] for r in results
                                      if r["product"] == product), None),
                        "when": next((time.strftime("%Y-%m-%d %H:%M",
                                                    time.gmtime(r["last_ts"]))
                                      for r in results if r["product"] == product), "")})

        if "levels" in spec["actions"] and levels:
            print("Levels — %s (%s)" % (product, spec["timeframe"]))
            for lv in levels:
                print("  %-10s %12s   touches %d"
                      % (lv["kind"], format(lv["price"], ",.4f").rstrip("0").rstrip("."),
                         lv["touches"]))
            print()
        if run_bt:
            print(backtest.render(result, product, spec))
            print()
        if "indicator" in spec["actions"] and product == products[0]:
            do_indicator(bars, product)
            print()

    # ---------------------------------------------------------- output
    if not charted:
        print("Nothing charted — no market in the brief returned usable data.")
        return 1

    if len(charted) > 1:
        index = chart.write_index(charted)
        print("Charts written:")
        for entry in charted:
            print("  %s" % os.path.relpath(entry["path"]))
        print("  %s   <- open this one" % os.path.relpath(index))
        target = index
    else:
        target = charted[0]["path"]
        print("Chart written: %s" % os.path.relpath(target))

    if "replay" in spec["actions"]:
        print("\nReplay is in the page: press Replay (or space) to walk it bar by bar.")
    save_session(spec)

    if args.open:
        webbrowser.open("file://" + os.path.abspath(target))
    return 0


if __name__ == "__main__":
    sys.exit(main())
