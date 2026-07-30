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
    --watch        keep re-scanning on every bar close, report new firings
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


GRACE = 20          # seconds after a bar closes before the venue is asked for it


def next_bar_close(timeframe, now=None):
    """Epoch second at which the current bar closes."""
    step = feed.TIMEFRAMES[timeframe]
    now = time.time() if now is None else now
    return (int(now) // step + 1) * step


def _sleep_until(when, label):
    """Interruptible wait, so Ctrl-C lands immediately instead of at the end."""
    while True:
        left = when - time.time()
        if left <= 0:
            return
        sys.stderr.write("\r  %s in %s   " % (label, _countdown(left)))
        sys.stderr.flush()
        time.sleep(min(left, 20))


def _countdown(seconds):
    seconds = int(seconds)
    if seconds >= 3600:
        return "%dh%02dm" % (seconds // 3600, seconds % 3600 // 60)
    if seconds >= 60:
        return "%dm%02ds" % (seconds // 60, seconds % 60)
    return "%ds" % seconds


def watch(spec, history):
    """
    Re-scan on every bar close and report setups the moment they go live.

    Only *newly* fired setups print — a market that stays in condition across
    several bars is announced once per bar it fires on, never on a loop.
    """
    universe = scan.universe_for(spec)
    print("Watching %d market%s on %s bars. Ctrl-C to stop."
          % (len(universe), "" if len(universe) == 1 else "s", spec["timeframe"]))
    print("Reports a setup only on the bar it fires. Nothing is ordered.\n")

    step = feed.TIMEFRAMES[spec["timeframe"]]
    seen = set()
    while True:
        try:
            closes_at = next_bar_close(spec["timeframe"])
            _sleep_until(closes_at + GRACE, "next bar close")
            sys.stderr.write("\r" + " " * 46 + "\r")
            sys.stderr.flush()
            # venues stamp a bar with its open time, so the bar that just closed
            # is the one that opened a step ago
            just_closed = closes_at - step
            results, _ = scan.run(spec, history=history, progress=False, fresh=True)
        except KeyboardInterrupt:
            print("\nStopped watching.")
            return 0
        except feed.FeedError as exc:
            print("  ! feed problem, will retry next bar: %s" % exc)
            continue

        fresh_hits = []
        for r in results:
            if not r["live"] or (r["product"], r["last_ts"]) in seen:
                continue
            seen.add((r["product"], r["last_ts"]))
            fresh_hits.append(r)

        if not fresh_hits:
            print("  %s UTC bar — nothing live"
                  % time.strftime("%Y-%m-%d %H:%M", time.gmtime(just_closed)))
            continue
        for r in fresh_hits:
            # the bar's own close time, not the wall clock — that's what fired
            print("  %s UTC bar — %s FIRED   close %s"
                  % (time.strftime("%Y-%m-%d %H:%M", time.gmtime(r["last_ts"])),
                     r["product"], scan.money(r["close"])))
            for line in scan.reading_lines(r["readings"]):
                print(line)
            try:
                bars = feed.candles(r["product"], spec["timeframe"], history)
                path, _, _ = chart_market(r["product"], spec, bars,
                                          "backtest" in spec["actions"])
                print("       chart: %s" % os.path.relpath(path))
            except feed.FeedError as exc:
                print("       (no chart: %s)" % exc)


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
    ap.add_argument("--watch", action="store_true",
                    help="after the first pass, re-scan on every bar close")
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

    if args.watch:
        if not spec["filters"]:
            print("\nNothing to watch for — the brief has no conditions.")
            return 1
        print()
        try:
            return watch(spec, min(history, brief.DEFAULTS["scan_history"]))
        except KeyboardInterrupt:
            print("\nStopped watching.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
