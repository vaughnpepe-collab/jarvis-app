#!/usr/bin/env python3
"""
Tapedeck — autonomous execution.

    python live.py "BTC with RSI below 30 and volume +200%, 1.5 ATR stop, 3% target"

Takes the same plain-English brief the rest of Tapedeck takes, waits for each bar
to close, and acts on it. Three modes:

    --mode paper    (default) simulated money, real prices, no keys needed
    --mode shadow   real account read for real, orders printed but NOT sent
    --mode live     orders are sent and cost real money

`tapedeck.py` cannot trade. It has no order path and no credential handling — the
read-only tool stays read-only, and everything that can spend money is in this
file and the four modules it imports. That separation is deliberate: it means you
can read the trading surface in one sitting.

ARMING LIVE MODE takes two independent actions, because one is too easy to do by
accident:

    --mode live                    on the command line, and
    TAPEDECK_LIVE_CONFIRM=yes      in the environment

Miss either and it refuses, tells you which one is missing, and exits without
sending anything.

HOW A BAR IS TRADED — and why it matches the backtester

The backtest evaluates conditions on a closed bar and enters at the NEXT bar's
open. Live, the moment a bar closes is the next bar's open, so a market order
placed immediately after the close is the faithful equivalent. That is the whole
reason this loop is bar-aligned rather than polling every few seconds: it makes
the live rule and the tested rule the same rule.

Order of business on every bar close:

    1. refresh candles for each market
    2. let resting stops resolve (paper simulates, live asks the venue)
    3. manage an open position: stop gone? target hit? exit signal? held too long?
    4. otherwise test the entry conditions, and if they hold, ask the risk gate
    5. on a permitted entry: send the order, then IMMEDIATELY park a protective
       stop at the venue

If step 5's stop cannot be placed, the position is closed again at once. A
position without a stop is the one state this loop will not sit in, so it would
rather take a small round-trip loss than hold something unprotected.

Ctrl-C is honoured between bars and stops the loop without touching open
positions. To actually get flat, run `--flatten`. To stop new entries without
killing the process, `touch HALT` — the file is the kill switch and open
positions keep being managed to their exit.

None of this is advice, and none of it makes the strategy work. Read
`risk.caveats()`, which every run prints.
"""
import argparse
import os
import sys
import time

import backtest
import brief
import broker as bk
import feed
import indicators as ind
import ledger as ledger_mod
import risk
import scan
import tapedeck
import venues

STATE_DIR = os.path.join(feed.ROOT, "state")
GRACE = tapedeck.GRACE          # seconds after a bar closes before asking the venue


# ---------------------------------------------------------------- wiring
def build_broker(mode, venue, prices, cash, paper_state=None):
    """
    The one place a real, order-capable broker can come into existence.

    paper  -> simulated, no credentials touched at all
    shadow -> real venue for reads, wrapped so writes only print
    live   -> the real thing
    """
    if mode == "paper":
        return bk.PaperBroker(cash=cash, price_source=lambda p: prices.get(p),
                              fee_pct=backtest.FEE_PCT,
                              slippage_pct=backtest.SLIPPAGE_PCT,
                              state_path=paper_state)
    inner = venues.connect(venue)
    if mode == "shadow":
        return bk.ShadowBroker(inner)
    return inner


def arm_live(mode):
    """Both gates, or nothing."""
    if mode != "live":
        return True, ""
    if os.environ.get("TAPEDECK_LIVE_CONFIRM", "").strip().lower() != "yes":
        return False, ("--mode live also needs TAPEDECK_LIVE_CONFIRM=yes in the "
                       "environment. Two gates, on purpose: a stale shell alias or "
                       "a typo should not be able to arm real orders.")
    return True, ""


def state_path(mode, venue):
    return os.path.join(STATE_DIR, "%s-%s.json" % (mode, venue))


# ---------------------------------------------------------------- levels
def stop_and_target(spec, price, atr_value):
    """
    Where the stop and target sit for an entry at `price`.

    Computed from the ACTUAL fill price, not the signal bar's close. A stop placed
    a fixed percentage below a price you didn't get is protecting a position you
    don't have.
    """
    st = spec["strategy"]
    long = st["direction"] != "short"
    if st.get("atr_stop") and atr_value:
        risk_distance = st["atr_stop"] * atr_value
    else:
        risk_distance = price * st["stop_pct"] / 100.0
    gain = price * st["target_pct"] / 100.0
    if long:
        return price - risk_distance, price + gain
    return price + risk_distance, price - gain


def bars_held(position, bar_ts, step):
    if not position.get("signal_bar_ts") or not step:
        return 0
    return max(0, int((bar_ts - position["signal_bar_ts"]) // step))


# ---------------------------------------------------------------- position management
def manage(product, position, bars, spec, cache, broker, book, log):
    """
    Resolve an open position against the bar that just closed.

    Precedence matters and mirrors the backtester: the stop is checked first, so a
    bar that contains both the stop and the target is recorded as a stop. The bar
    does not say which came first and the pessimistic branch is the honest one.
    """
    last = bars[-1]
    step = feed.TIMEFRAMES[spec["timeframe"]]
    long = position["direction"] != "short"
    st = spec["strategy"]

    # 1. did the protective stop fill? The venue is the authority, not our maths.
    stop_id = position.get("stop_venue_id")
    if stop_id:
        try:
            still_resting = any(o.venue_id == stop_id
                                for o in broker.open_orders(product))
        except bk.BrokerError as exc:
            log("  ! could not check the stop at %s (%s) — leaving the position "
                "alone this bar" % (broker.name, exc))
            return
        if not still_resting:
            # A missing stop is NOT proof that it filled. It may have been
            # cancelled by hand, dropped by the venue, or hidden by a paginated
            # order list. Booking a loss on that inference alone would report a
            # trade that never happened and leave real coins unmanaged, so ask
            # what we actually hold before deciding which of the two it was.
            base = product.partition("-")[0]
            try:
                held = float(broker.balances().get(base, 0.0))
            except bk.BrokerError as exc:
                log("  ! the stop is gone and balances are unreadable (%s) — not "
                    "guessing which; leaving the position alone this bar" % exc)
                return
            if held >= position["qty"] * 0.95:
                log("  ! %s: the protective stop is gone but the coins are still "
                    "here — it was cancelled, not filled. Replacing it." % product)
                _replace_stop(product, position, broker, book, last, log)
            else:
                price = position.get("stop") or last.close
                record = book.close_position(position, price, "stop", bar_ts=last.ts)
                log("  STOP filled — out of %s at %s   %+.2f"
                    % (product, scan.money(price), record["pnl"]))
                return

    # 2. target — managed here rather than resting at the venue, so a filled stop
    #    can never leave a live order behind that would re-open the position.
    hit_target = (last.high >= position["target"] if long
                  else last.low <= position["target"])
    reason = None
    if position.get("target") and hit_target:
        reason, exit_price = "target", position["target"]
    else:
        exit_filters = st.get("exit") or []
        if exit_filters and scan.holds(exit_filters, cache, bars, len(bars) - 1):
            reason, exit_price = "signal", last.close
        elif st.get("max_hold") and bars_held(position, last.ts, step) >= st["max_hold"]:
            reason, exit_price = "time", last.close
    if not reason:
        return

    # cancel the protective stop BEFORE selling: selling first would briefly leave a
    # resting sell against a position that no longer exists.
    if stop_id:
        try:
            broker.cancel(stop_id, product)
        except bk.BrokerError as exc:
            log("  ! could not cancel the protective stop (%s) — not selling into an "
                "uncancelled stop, will retry next bar" % exc)
            return

    cid = bk.client_id(product, "sell" if long else "buy", last.ts, "x")
    if book.was_submitted(cid):
        return
    book.record_submitted(cid, "exit", product)
    try:
        fill = broker.market_order(product, bk.SELL if long else bk.BUY,
                                  position["qty"], cid)
    except bk.BrokerError as exc:
        log("  !! EXIT FAILED on %s: %s" % (product, exc))
        log("     The position is still open and its stop was cancelled. Replacing "
            "the stop now.")
        _replace_stop(product, position, broker, book, last, log)
        return
    record = book.close_position(position, fill.price, reason, fees=fill.fee,
                                bar_ts=last.ts)
    log("  %-6s exit %s at %s   %+.2f  (%.2f%%)"
        % (reason.upper(), product, scan.money(fill.price), record["pnl"], record["pct"]))


def _replace_stop(product, position, broker, book, bar, log):
    """Re-park a protective stop. Used after a failed exit or a vanished stop."""
    long = position["direction"] != "short"
    cid = bk.client_id(product, "sell" if long else "buy", bar.ts, "s2")
    try:
        order = broker.stop_order(product, bk.SELL if long else bk.BUY,
                                 position["qty"], position["stop"], cid)
        book.attach_stop(position, order.venue_id, cid, position["stop"])
        log("     protective stop re-placed at %s" % scan.money(position["stop"]))
        return True
    except bk.BrokerError as exc:
        log("     !! COULD NOT PLACE A STOP: %s" % exc)
        log("     !! %s is open and UNPROTECTED. Close it at the venue by hand."
            % product)
        return False


# ---------------------------------------------------------------- entry
def try_entry(product, bars, spec, cache, broker, book, engine, notional, log):
    last = bars[-1]
    index = len(bars) - 1
    if not scan.holds(spec["filters"], cache, bars, index):
        return False

    long = spec["strategy"]["direction"] != "short"
    side = bk.BUY if long else bk.SELL
    cid = bk.client_id(product, side, last.ts, "e")
    if book.was_submitted(cid):
        return False                    # this bar has already been acted on

    for line in scan.reading_lines(scan.readings(spec["filters"], cache, bars, index)):
        log(line)

    try:
        price = broker.ticker(product)
        market = broker.market(product)
    except bk.BrokerError as exc:
        log("  ! no tradable quote for %s (%s)" % (product, exc))
        return False

    atr_series = ind.atr(bars)
    stop_price, target_price = stop_and_target(spec, price, atr_series[index]
                                               if atr_series else None)

    balances = {}
    try:
        balances = broker.balances()
    except bk.BrokerError as exc:
        log("  ! could not read balances (%s)" % exc)
        return False
    quote_free = float(balances.get(market.quote, 0.0))

    decision = engine.check_entry(
        product, spec["strategy"]["direction"], price, stop_price, notional,
        book.snapshot(feed.TIMEFRAMES[spec["timeframe"]]), broker,
        reference_price=last.close, quote_balance=quote_free)
    for note in decision.notes:
        log("       %s" % note)
    if not decision.ok:
        log("  BLOCKED — %s" % decision.reason)
        return False

    try:
        qty = bk.size_for(decision.notional, price, market)
    except bk.Rejected as exc:
        log("  BLOCKED — %s" % exc)
        return False

    # Recorded BEFORE the send. If the process dies between these two lines the
    # worst case is a signal we skip; recording afterwards would risk sending the
    # same order twice, which is the failure that actually costs money.
    book.record_submitted(cid, "entry", product)
    try:
        fill = broker.market_order(product, side, qty, cid)
    except bk.Rejected as exc:
        log("  REFUSED by %s — %s" % (broker.name, exc))
        return False
    except bk.BrokerError as exc:
        log("  !! ENTRY UNCERTAIN on %s: %s" % (product, exc))
        log("     Check the venue before running again — an order may exist.")
        return False

    # the stop belongs to the price we actually got
    stop_price, target_price = stop_and_target(spec, fill.price,
                                               atr_series[index] if atr_series else None)
    position = book.open_position(
        product=product, direction=spec["strategy"]["direction"], qty=fill.qty,
        entry=fill.price, stop=stop_price, target=target_price,
        signal_bar_ts=last.ts, entry_cid=cid, fees=fill.fee,
        max_hold=spec["strategy"].get("max_hold"))
    log("  ENTERED %s %s %s at %s   stop %s   target %s"
        % (spec["strategy"]["direction"], bk._trim(fill.qty), product,
           scan.money(fill.price), scan.money(stop_price), scan.money(target_price)))

    scid = bk.client_id(product, bk.SELL if long else bk.BUY, last.ts, "s")
    try:
        order = broker.stop_order(product, bk.SELL if long else bk.BUY,
                                 fill.qty, stop_price, scid)
        book.attach_stop(position, order.venue_id, scid, stop_price)
        log("       protective stop resting at the venue (%s)" % order.venue_id)
    except bk.BrokerError as exc:
        # An unprotected position is the one state worth paying to leave.
        log("  !! the entry filled but the protective stop was refused: %s" % exc)
        log("     closing the position again rather than holding it unprotected")
        try:
            out = broker.market_order(product, bk.SELL if long else bk.BUY, fill.qty,
                                     bk.client_id(product, "sell", last.ts, "panic"))
            record = book.close_position(position, out.price, "no-stop", fees=out.fee,
                                        bar_ts=last.ts)
            log("     flattened at %s   %+.2f" % (scan.money(out.price), record["pnl"]))
        except bk.BrokerError as inner:
            log("     !! COULD NOT FLATTEN EITHER: %s" % inner)
            log("     !! %s IS OPEN AND UNPROTECTED — go to the venue now." % product)
    return True


# ---------------------------------------------------------------- flatten
def flatten(products, spec, broker, book, log):
    """Cancel every protective stop and close every open position, now."""
    positions = list(book.state["positions"])
    if not positions:
        log("Nothing open.")
        return 0
    for position in positions:
        product = position["product"]
        long = position["direction"] != "short"
        if position.get("stop_venue_id"):
            try:
                broker.cancel(position["stop_venue_id"], product)
            except bk.BrokerError as exc:
                log("  ! could not cancel the stop on %s: %s" % (product, exc))
        cid = bk.client_id(product, "sell" if long else "buy", time.time(), "flat")
        try:
            fill = broker.market_order(product, bk.SELL if long else bk.BUY,
                                      position["qty"], cid)
            record = book.close_position(position, fill.price, "flatten", fees=fill.fee)
            log("  closed %s at %s   %+.2f"
                % (product, scan.money(fill.price), record["pnl"]))
        except bk.BrokerError as exc:
            log("  !! could not close %s: %s — do it at the venue" % (product, exc))
            return 1
    return 0


# ---------------------------------------------------------------- header
def header(spec, mode, broker, engine, products, notional, book):
    lines = ["Tapedeck — execution", ""]
    lines.append("  Mode       %s" % {
        "paper": "PAPER — simulated money, real prices",
        "shadow": "SHADOW — real account read, orders printed and NOT sent",
        "live": "LIVE — orders are sent and cost real money",
    }[mode])
    lines.append("  Venue      %s" % broker.describe())
    lines.append("  Markets    %s" % ", ".join(products))
    lines.append("  Timeframe  %s bars" % spec["timeframe"])
    if spec["filters"]:
        lines.append("  Entry when (all on the same closed bar)")
        for f in spec["filters"]:
            lines.append("    · %s" % f["text"])
    st = spec["strategy"]
    stop = ("%.2f x ATR(14)" % st["atr_stop"]) if st.get("atr_stop") else "%g%%" % st["stop_pct"]
    lines.append("  Exit       stop %s · target %g%% · max hold %d bars"
                 % (stop, st["target_pct"], st["max_hold"]))
    for f in st.get("exit") or []:
        lines.append("             or when %s" % f["text"])
    lines.append("  Size       %s notional per trade (before limits)"
                 % format(notional, ",.2f"))
    lines.append("  Ledger     %s" % os.path.relpath(book.path))
    lines.append("")
    lines.append("  Risk limits")
    for line in engine.limits.describe():
        lines.append("    - %s" % line)
    lines.append("")
    lines.append("  What these limits cannot do for you")
    for line in risk.caveats():
        lines.append("    - %s" % line)
    return "\n".join(lines)


# ---------------------------------------------------------------- the loop
def run(spec, args):
    prices = {}
    mode = args.mode
    ok, why = arm_live(mode)
    if not ok:
        print("Refusing to arm live trading.\n\n  %s" % why)
        return 2

    products, unlisted = scan.resolve_universe(spec)
    if unlisted:
        print("Not listed on these venues: %s" % ", ".join(unlisted))
    if not products:
        print("No tradable market in the brief.")
        return 1
    products = products[:max(1, args.markets)]

    if not spec["filters"]:
        print("The brief has no entry condition — there is nothing to trade on.")
        return 1

    step = feed.TIMEFRAMES[spec["timeframe"]]
    # seed prices before the broker needs them
    history = args.history or brief.DEFAULTS["scan_history"]
    for product in products:
        try:
            prices[product] = feed.candles(product, spec["timeframe"], 2)[-1].close
        except feed.FeedError:
            pass

    try:
        trader = build_broker(mode, args.venue, prices, args.cash,
                              paper_state=state_path(mode, "paper-book"))
    except bk.BrokerError as exc:
        print("Cannot connect to %s:\n\n  %s" % (args.venue, exc))
        return 2

    if spec["strategy"]["direction"] == "short" and not trader.can_short:
        print("The brief is a SHORT and %s is a spot account.\n\n"
              "  Selling what you do not hold needs margin or a futures contract, "
              "and this project has no path to either — deliberately. Nothing was "
              "sent." % trader.name)
        return 1

    limits = risk.Limits(
        max_notional=args.max_notional, max_exposure=args.max_exposure,
        max_positions=args.max_positions, daily_loss_stop=args.daily_loss,
        cooldown_bars=args.cooldown, kill_file=args.kill_file)
    engine = risk.RiskEngine(limits)
    book = ledger_mod.Ledger(state_path(mode, trader.name), mode, trader.name)
    notional = args.notional or limits.max_notional

    print(header(spec, mode, trader, engine, products, notional, book))
    print()

    if args.flatten:
        return flatten(products, spec, trader, book, print)

    print("Reconciling the ledger against %s..." % trader.name)
    report = book.reconcile(trader)
    print(ledger_mod.render_reconcile(report))
    if report["blocking"] and not args.adopt:
        print("\nRefusing to trade while the ledger and the venue disagree.\n"
              "  Look at the account, then re-run with --adopt to accept the "
              "venue's version and carry on.")
        return 3
    if report["blocking"] and args.adopt:
        print("\n--adopt given: continuing despite the conflicts above.")
    print()

    if engine.halted():
        print("Kill switch is on (%s) — no new entries will be opened.\n"
              % engine.limits.kill_file)

    stats = book.stats()
    if stats["trades"]:
        print("Ledger so far: %d closed trade%s, %+.2f realised (%.1f%% hit rate)\n"
              % (stats["trades"], "" if stats["trades"] == 1 else "s",
                 stats["pnl"], stats["hit_rate"]))

    print("Watching %d market%s on %s bars. Ctrl-C to stop (positions are left "
          "open — use --flatten to get out).\n"
          % (len(products), "" if len(products) == 1 else "s", spec["timeframe"]))

    passes = 0
    while True:
        if not args.now or passes:
            closes_at = tapedeck.next_bar_close(spec["timeframe"])
            try:
                tapedeck._sleep_until(closes_at + GRACE, "next bar close")
            except KeyboardInterrupt:
                print("\nStopped. Open positions were left as they are.")
                return 0
            sys.stderr.write("\r" + " " * 46 + "\r")
            sys.stderr.flush()

        passes += 1
        stamp = time.strftime("%Y-%m-%d %H:%M", time.gmtime())
        print("%s UTC" % stamp)

        for product in products:
            try:
                bars = feed.candles(product, spec["timeframe"], history, fresh=True)
            except feed.FeedError as exc:
                print("  ! %s: feed problem, skipping this bar (%s)" % (product, exc))
                continue
            if len(bars) < 60:
                print("  ! %s: only %d bars of history" % (product, len(bars)))
                continue
            prices[product] = bars[-1].close

            filters = spec["filters"] + (spec["strategy"].get("exit") or [])
            cache = scan.build_series(bars, filters)

            # resting stops resolve first, before anything reads position state
            if isinstance(trader, bk.PaperBroker):
                for fill in trader.poll(bars[-1], product):
                    position = book.position_for(product)
                    if position:
                        record = book.close_position(position, fill.price, "stop",
                                                    fees=fill.fee, bar_ts=bars[-1].ts)
                        print("  STOP filled — out of %s at %s   %+.2f"
                              % (product, scan.money(fill.price), record["pnl"]))

            position = book.position_for(product)
            if position:
                if not position.get("stop_venue_id"):
                    _replace_stop(product, position, trader, book, bars[-1], print)
                manage(product, position, bars, spec, cache, trader, book, print)
                position = book.position_for(product)
                if position:
                    held = bars_held(position, bars[-1].ts, step)
                    mark = ((bars[-1].close - position["entry"]) * position["qty"]
                            if position["direction"] != "short"
                            else (position["entry"] - bars[-1].close) * position["qty"])
                    print("  holding %s from %s — %d bar%s, open %+.2f"
                          % (product, scan.money(position["entry"]), held,
                             "" if held == 1 else "s", mark))
            else:
                if not try_entry(product, bars, spec, cache, trader, book, engine,
                                 notional, print):
                    print("  %s %s — no entry" % (product, scan.money(bars[-1].close)))

        if isinstance(trader, bk.PaperBroker):
            print("  paper equity %s" % format(trader.equity(prices), ",.2f"))
        if mode == "shadow" and trader.intents:
            print("  %d order(s) would have been sent this run" % len(trader.intents))

        if args.once:
            break
        print()
    return 0


# ---------------------------------------------------------------- cli
def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Tapedeck — trade a plain-English brief automatically.")
    ap.add_argument("brief", nargs="*", help="the strategy, in plain English")
    ap.add_argument("--mode", choices=("paper", "shadow", "live"), default="paper")
    ap.add_argument("--venue", choices=sorted(venues.VENUES), default="kraken",
                    help="only used by shadow and live")
    ap.add_argument("--markets", type=int, default=1,
                    help="how many markets from the brief to trade (default 1)")
    ap.add_argument("--notional", type=float, default=None,
                    help="quote currency per trade, before risk clamping")
    ap.add_argument("--max-notional", type=float, default=None, dest="max_notional")
    ap.add_argument("--max-exposure", type=float, default=None, dest="max_exposure")
    ap.add_argument("--max-positions", type=int, default=None, dest="max_positions")
    ap.add_argument("--daily-loss", type=float, default=None, dest="daily_loss")
    ap.add_argument("--cooldown", type=int, default=None,
                    help="bars of silence after a losing trade")
    ap.add_argument("--kill-file", default=None, dest="kill_file")
    ap.add_argument("--cash", type=float, default=10000.0,
                    help="starting balance for paper mode")
    ap.add_argument("--history", type=int, default=None)
    ap.add_argument("--once", action="store_true", help="one pass, then exit")
    ap.add_argument("--now", action="store_true",
                    help="act on the newest closed bar immediately, don't wait")
    ap.add_argument("--flatten", action="store_true",
                    help="close every open position and exit")
    ap.add_argument("--adopt", action="store_true",
                    help="proceed even if the ledger and venue disagree")
    ap.add_argument("--new", action="store_true", help="ignore the remembered brief")
    args = ap.parse_args(argv)

    text = " ".join(args.brief).strip()
    if not text and not args.flatten:
        print(__doc__.strip())
        return 0

    previous = None if args.new else tapedeck.load_session()
    spec = brief.parse(text or "hold", previous=previous)
    try:
        return run(spec, args)
    except KeyboardInterrupt:
        print("\nStopped. Open positions were left as they are.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
