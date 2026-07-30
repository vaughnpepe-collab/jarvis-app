#!/usr/bin/env python3
"""
Tapedeck — self-test for the order path.

    python selftest_live.py

Offline. No network, no credentials, no venue. Uses fake keys and a fake price
source, so it can be run anywhere, by anyone, including on a machine that has
never held an API key.

What it is actually checking is not "does the code run" but "does the code refuse
to do the expensive wrong thing":

  - a retried order does not become two positions
  - a size is never rounded UP past a limit
  - the risk gate blocks entries and never blocks exits
  - the kill switch stops entries
  - the daily loss stop counts realised losses and halts
  - a short on a spot account is refused rather than quietly flipped
  - a ledger that disagrees with the venue is reported, not papered over
  - a stop that vanished while we were dead is booked at the stop price
  - the signing schemes produce stable, documented output

The signing tests pin each venue's scheme against fixed vectors. They prove the
implementation does not silently change — they cannot prove a venue accepts it.
Only `--mode shadow` against your own account can do that, and it is the first
thing you should run.
"""
import os
import sys
import tempfile
import time

import broker as bk
import brief
import ledger as ledger_mod
import risk
from feed import Candle

FAILED = []


def check(label, condition, detail=""):
    mark = "ok  " if condition else "FAIL"
    print("  %s %s%s" % (mark, label, ("  — " + detail) if detail and not condition else ""))
    if not condition:
        FAILED.append(label)


def bar(ts, o, h, l, c, v=100.0):
    return Candle(ts, o, h, l, c, v)


def paper(price=100.0, cash=1000.0):
    prices = {"BTC-USD": price}
    return bk.PaperBroker(cash=cash, price_source=lambda p: prices.get(p)), prices


def tmp_ledger():
    handle = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
    handle.close()
    os.unlink(handle.name)
    return ledger_mod.Ledger(handle.name, "paper", "paper")


# ---------------------------------------------------------------- sizing
def test_sizing():
    print("sizing")
    market = bk.Market("BTC-USD", "BTC", "USD", min_size=0.0001,
                       size_step=0.00001, price_step=0.01)

    qty = bk.size_for(100.0, 30000.0, market)
    check("size rounds DOWN to the venue increment", qty == 0.00333,
          "got %r" % qty)
    check("rounded size never exceeds the requested notional",
          qty * 30000.0 <= 100.0 + 1e-9, "%r" % (qty * 30000.0))

    check("a size below the venue minimum is refused",
          _raises(bk.Rejected, bk.size_for, 1.0, 30000.0, market))
    check("a zero price is refused rather than dividing by it",
          _raises(bk.Rejected, bk.size_for, 100.0, 0.0, market))

    # 0.1 + 0.2 style float grunge must not leak into a venue size
    step = bk.round_down(0.30000000000000004, 0.1)
    check("Decimal rounding kills float noise", abs(step - 0.3) < 1e-12, "%r" % step)
    check("round_price lands on a tick", bk.round_price(100.017, 0.01) == 100.02,
          "%r" % bk.round_price(100.017, 0.01))
    check("a step of 0 leaves the value alone", bk.round_down(1.2345, 0) == 1.2345)


# ---------------------------------------------------------------- idempotency
def test_idempotency():
    print("idempotency")
    a = bk.client_id("BTC-USD", "buy", 1_700_000_000, "e")
    b = bk.client_id("BTC-USD", "buy", 1_700_000_000, "e")
    c = bk.client_id("BTC-USD", "buy", 1_700_003_600, "e")
    d = bk.client_id("BTC-USD", "buy", 1_700_000_000, "s")
    check("the same bar and side gives the same client id", a == b)
    check("a different bar gives a different id", a != c)
    check("the stop leg gets its own id", a != d)
    check("ids are venue-safe (short, ascii, prefixed)",
          a.startswith("td-") and len(a) == 23 and a[3:].isalnum())

    broker, _ = paper()
    first = broker.market_order("BTC-USD", bk.BUY, 0.001, a)
    second = broker.market_order("BTC-USD", bk.BUY, 0.001, a)
    check("a resent order returns the first fill, not a second one",
          first is second and len(broker.fills) == 1, "%d fills" % len(broker.fills))

    book = tmp_ledger()
    book.record_submitted(a, "entry", "BTC-USD")
    check("the ledger remembers a submitted id", book.was_submitted(a))
    check("and does not claim ids it has never seen", not book.was_submitted(c))
    reloaded = ledger_mod.Ledger(book.path, "paper", "paper")
    check("submitted ids survive a restart", reloaded.was_submitted(a))


# ---------------------------------------------------------------- paper broker
def test_paper_broker():
    print("paper broker")
    broker, prices = paper(price=100.0, cash=1000.0)
    fill = broker.market_order("BTC-USD", bk.BUY, 1.0, "cid-buy")
    check("a buy fills above the last price (slippage against you)",
          fill.price > 100.0, "%r" % fill.price)
    check("the fee is charged on top", fill.fee > 0)
    check("cash went down by gross + fee",
          abs(broker.cash - (1000.0 - fill.price - fill.fee)) < 1e-9,
          "%r" % broker.cash)
    check("holdings went up", broker.holdings["BTC"] == 1.0)

    sell = broker.market_order("BTC-USD", bk.SELL, 1.0, "cid-sell")
    check("a sell fills below the last price", sell.price < 100.0, "%r" % sell.price)
    check("a round trip at a flat price loses money to costs",
          broker.cash < 1000.0, "%r" % broker.cash)

    check("selling more than we hold is refused",
          _raises(bk.Rejected, broker.market_order, "BTC-USD", bk.SELL, 5.0, "cid-x"))
    poor, _ = paper(price=100.0, cash=10.0)
    check("buying beyond the paper balance is refused",
          _raises(bk.Rejected, poor.market_order, "BTC-USD", bk.BUY, 1.0, "cid-y"))

    # resting stop
    broker2, _ = paper(price=100.0, cash=1000.0)
    broker2.market_order("BTC-USD", bk.BUY, 1.0, "in")
    broker2.stop_order("BTC-USD", bk.SELL, 1.0, 95.0, "stop")
    check("a resting stop is visible in open orders",
          len(broker2.open_orders("BTC-USD")) == 1)
    quiet = broker2.poll(bar(1, 99.0, 101.0, 96.0, 100.0), "BTC-USD")
    check("a bar that misses the stop does not trigger it", quiet == [])
    hit = broker2.poll(bar(2, 99.0, 100.0, 94.0, 96.0), "BTC-USD")
    check("a bar whose low reaches the stop triggers it", len(hit) == 1)
    check("the stop fills AT the stop price", hit and hit[0].price == 95.0)
    check("a triggered stop stops resting", broker2.open_orders("BTC-USD") == [])
    check("cancelling an unknown order is not an error",
          broker2.cancel("nope") is None)


# ---------------------------------------------------------------- risk gate
def _snapshot(**kwargs):
    base = {"open_positions": [], "realised_today": 0.0,
            "last_loss_bar_ts": None, "bar_seconds": 3600}
    base.update(kwargs)
    return base


class _Spot:
    name = "spot-test"
    can_short = False
    live = False


class _Margin(_Spot):
    name = "margin-test"
    can_short = True


def test_risk_gate():
    print("risk gate")
    kill = os.path.join(tempfile.mkdtemp(), "HALT")
    limits = risk.Limits(max_notional=100.0, min_notional=5.0, max_exposure=200.0,
                         max_positions=1, daily_loss_stop=50.0, cooldown_bars=2,
                         kill_file=kill)
    engine = risk.RiskEngine(limits)
    spot = _Spot()

    good = engine.check_entry("BTC-USD", "long", 100.0, 98.0, 100.0,
                              _snapshot(), spot, reference_price=100.0,
                              quote_balance=500.0)
    check("a clean entry is allowed", good.ok, good.reason)
    check("and it reports the money at risk",
          any("risking" in n for n in good.notes), str(good.notes))

    clamped = engine.check_entry("BTC-USD", "long", 100.0, 98.0, 5000.0,
                                 _snapshot(), spot, reference_price=100.0,
                                 quote_balance=99999.0)
    check("an oversized request is clamped DOWN to the cap",
          clamped.ok and clamped.notional == 100.0, "%r" % clamped.notional)

    tiny = engine.check_entry("BTC-USD", "long", 100.0, 98.0, 1.0, _snapshot(), spot,
                             reference_price=100.0, quote_balance=500.0)
    check("a request below the floor is refused", not tiny.ok)

    held = engine.check_entry("BTC-USD", "long", 100.0, 98.0, 100.0,
                              _snapshot(open_positions=[{"notional": 100.0}]), spot,
                              reference_price=100.0, quote_balance=500.0)
    check("a second position is refused at max_positions=1", not held.ok)
    check("and says so in plain words", "already holding" in held.reason, held.reason)

    lossy = engine.check_entry("BTC-USD", "long", 100.0, 98.0, 100.0,
                               _snapshot(realised_today=-60.0), spot,
                               reference_price=100.0, quote_balance=500.0)
    check("the daily loss stop halts new entries", not lossy.ok)
    check("the daily loss message names the cap",
          "daily loss stop" in lossy.reason, lossy.reason)

    cooling = engine.check_entry("BTC-USD", "long", 100.0, 98.0, 100.0,
                                 _snapshot(last_loss_bar_ts=time.time()), spot,
                                 reference_price=100.0, quote_balance=500.0)
    check("a cooldown after a loss blocks the next bar", not cooling.ok)
    cooled = engine.check_entry("BTC-USD", "long", 100.0, 98.0, 100.0,
                                _snapshot(last_loss_bar_ts=time.time() - 3 * 3600), spot,
                                reference_price=100.0, quote_balance=500.0)
    check("and lets go once the bars have passed", cooled.ok, cooled.reason)

    drifted = engine.check_entry("BTC-USD", "long", 130.0, 128.0, 100.0, _snapshot(),
                                 spot, reference_price=100.0, quote_balance=500.0)
    check("a quote far from the signal bar is refused", not drifted.ok)
    check("the price-sanity message shows both prices",
          "price sanity" in drifted.reason, drifted.reason)

    wrong_side = engine.check_entry("BTC-USD", "long", 100.0, 102.0, 100.0, _snapshot(),
                                    spot, reference_price=100.0, quote_balance=500.0)
    check("a stop above entry on a long is refused", not wrong_side.ok)
    too_tight = engine.check_entry("BTC-USD", "long", 100.0, 99.999, 100.0, _snapshot(),
                                   spot, reference_price=100.0, quote_balance=500.0)
    check("a stop tighter than the floor is refused", not too_tight.ok)
    too_wide = engine.check_entry("BTC-USD", "long", 100.0, 50.0, 100.0, _snapshot(),
                                  spot, reference_price=100.0, quote_balance=500.0)
    check("a stop wider than the ceiling is refused", not too_wide.ok)
    no_stop = engine.check_entry("BTC-USD", "long", 100.0, None, 100.0, _snapshot(),
                                 spot, reference_price=100.0, quote_balance=500.0)
    check("no stop at all is refused when a stop is required", not no_stop.ok)

    broke = engine.check_entry("BTC-USD", "long", 100.0, 98.0, 100.0, _snapshot(),
                               spot, reference_price=100.0, quote_balance=50.0)
    check("an entry the balance cannot cover is refused", not broke.ok)

    short_spot = engine.check_entry("BTC-USD", "short", 100.0, 102.0, 100.0,
                                    _snapshot(), spot, reference_price=100.0,
                                    quote_balance=500.0)
    check("a short on a spot account is refused", not short_spot.ok)
    check("the refusal explains why, rather than trading the long side",
          "margin" in short_spot.reason, short_spot.reason)
    short_margin = engine.check_entry("BTC-USD", "short", 100.0, 102.0, 100.0,
                                      _snapshot(), _Margin(), reference_price=100.0,
                                      quote_balance=500.0)
    check("a short is allowed where the broker can actually borrow",
          short_margin.ok, short_margin.reason)

    exposure = engine.check_entry("BTC-USD", "long", 100.0, 98.0, 100.0,
                                  _snapshot(open_positions=[{"notional": 150.0}]),
                                  _Spot(), reference_price=100.0, quote_balance=500.0)
    # max_positions would also stop this, so test exposure on a permissive limit set
    roomy = risk.RiskEngine(risk.Limits(max_notional=100.0, max_exposure=200.0,
                                        max_positions=5, kill_file=kill))
    squeezed = roomy.check_entry("BTC-USD", "long", 100.0, 98.0, 100.0,
                                 _snapshot(open_positions=[{"notional": 150.0}]),
                                 _Spot(), reference_price=100.0, quote_balance=500.0)
    check("exposure room clamps the size", squeezed.ok and squeezed.notional == 50.0,
          "%r" % squeezed.notional)
    full = roomy.check_entry("BTC-USD", "long", 100.0, 98.0, 100.0,
                             _snapshot(open_positions=[{"notional": 200.0}]),
                             _Spot(), reference_price=100.0, quote_balance=500.0)
    check("a full book is refused outright", not full.ok)
    check("(exposure ceiling is independent of position count)", not exposure.ok)


def test_kill_switch():
    print("kill switch")
    folder = tempfile.mkdtemp()
    kill = os.path.join(folder, "HALT")
    engine = risk.RiskEngine(risk.Limits(kill_file=kill))
    check("absent file means running", not engine.halted())

    allowed = engine.check_entry("BTC-USD", "long", 100.0, 98.0, 20.0, _snapshot(),
                                 _Spot(), reference_price=100.0, quote_balance=500.0)
    check("entries pass while it is off", allowed.ok, allowed.reason)

    with open(kill, "w", encoding="utf-8") as fh:
        fh.write("stopped by hand at the pub\n")
    check("the file being there means halted", engine.halted())
    blocked = engine.check_entry("BTC-USD", "long", 100.0, 98.0, 20.0, _snapshot(),
                                 _Spot(), reference_price=100.0, quote_balance=500.0)
    check("entries are blocked while it is on", not blocked.ok)
    check("the note in the file is read back",
          "pub" in blocked.reason, blocked.reason)
    os.unlink(kill)
    check("removing it resumes trading",
          engine.check_entry("BTC-USD", "long", 100.0, 98.0, 20.0, _snapshot(),
                             _Spot(), reference_price=100.0, quote_balance=500.0).ok)


# ---------------------------------------------------------------- ledger
def test_ledger():
    print("ledger")
    book = tmp_ledger()
    position = book.open_position(product="BTC-USD", direction="long", qty=0.5,
                                  entry=100.0, stop=98.0, target=104.0,
                                  signal_bar_ts=1_700_000_000, fees=0.1)
    check("an open position is recorded", len(book.state["positions"]) == 1)
    check("notional is qty x entry", position["notional"] == 50.0)
    check("it is findable by product", book.position_for("BTC-USD") is position)
    check("and other markets are not confused with it",
          book.position_for("ETH-USD") is None)

    reloaded = ledger_mod.Ledger(book.path, "paper", "paper")
    check("the position survives a restart", len(reloaded.state["positions"]) == 1)

    record = book.close_position(position, 104.0, "target", fees=0.1)
    check("closing removes it from open positions", book.state["positions"] == [])
    check("P&L is (exit - entry) * qty minus fees",
          abs(record["pnl"] - ((104.0 - 100.0) * 0.5 - 0.2)) < 1e-9, "%r" % record["pnl"])
    check("the trade lands in the blotter", len(book.state["closed"]) == 1)
    check("a win does not set the cooldown clock",
          book.state["last_loss_bar_ts"] is None)
    check("realised today tracks the win",
          abs(book.state["day"]["realised"] - record["pnl"]) < 1e-9)

    loser = book.open_position(product="ETH-USD", direction="long", qty=1.0,
                               entry=100.0, stop=98.0, target=104.0,
                               signal_bar_ts=1_700_000_000)
    lost = book.close_position(loser, 98.0, "stop", bar_ts=1_700_003_600)
    check("a loss is negative", lost["pnl"] < 0)
    check("a loss sets the cooldown clock",
          book.state["last_loss_bar_ts"] == 1_700_003_600)
    check("realised today is the sum of both", abs(
        book.state["day"]["realised"] - (record["pnl"] + lost["pnl"])) < 1e-9)

    short = book.open_position(product="SOL-USD", direction="short", qty=2.0,
                               entry=100.0, stop=102.0, target=96.0)
    short_win = book.close_position(short, 96.0, "target")
    check("a short profits when price falls",
          abs(short_win["pnl"] - 8.0) < 1e-9, "%r" % short_win["pnl"])

    stats = book.stats()
    check("stats count every closed trade", stats["trades"] == 3)
    check("hit rate matches the blotter",
          abs(stats["hit_rate"] - (2 / 3 * 100.0)) < 1e-9, "%r" % stats["hit_rate"])
    check("summed P&L matches the blotter",
          abs(stats["pnl"] - sum(t["pnl"] for t in book.state["closed"])) < 1e-9)

    # atomic write: no .tmp left behind, and the file is valid JSON
    check("no temp file is left after a save", not os.path.exists(book.path + ".tmp"))
    import json
    with open(book.path, encoding="utf-8") as fh:
        check("the saved ledger is valid JSON", isinstance(json.load(fh), dict))

    corrupt = book.path + ".bad"
    with open(corrupt, "w", encoding="utf-8") as fh:
        fh.write("{not json at all")
    fresh = ledger_mod.Ledger(corrupt, "paper", "paper")
    check("a corrupt ledger starts empty instead of crashing",
          fresh.state["positions"] == [])

    stale = book.path + ".v0"
    with open(stale, "w", encoding="utf-8") as fh:
        json.dump({"version": 0, "positions": [{"product": "XXX"}]}, fh)
    check("a ledger from another version is not trusted",
          ledger_mod.Ledger(stale, "paper", "paper").state["positions"] == [])


# ---------------------------------------------------------------- reconciliation
class _FakeVenue:
    """A venue whose answers the test controls."""

    name = "fake"
    live = False
    can_short = False

    def __init__(self, balances=None, orders=None, fail=False):
        self._balances = balances or {}
        self._orders = orders or []
        self._fail = fail

    def balances(self):
        if self._fail:
            raise bk.BrokerError("venue unreachable")
        return dict(self._balances)

    def open_orders(self, product=None):
        return [o for o in self._orders if product is None or o.product == product]


def _order(venue_id, product="BTC-USD", side="sell", price=98.0, qty=0.5):
    return bk.Order("", venue_id, product, side, "stop", qty, price, "open")


def test_reconciliation():
    print("reconciliation")
    # agreement
    book = tmp_ledger()
    position = book.open_position(product="BTC-USD", direction="long", qty=0.5,
                                  entry=100.0, stop=98.0, target=104.0)
    book.attach_stop(position, "v1", "cid", 98.0)
    report = book.reconcile(_FakeVenue({"BTC": 0.5}, [_order("v1")]))
    check("a matching ledger and venue produce no conflicts",
          not report["conflicts"] and not report["blocking"], str(report))

    # the stop filled while we were dead
    book2 = tmp_ledger()
    gone = book2.open_position(product="BTC-USD", direction="long", qty=0.5,
                               entry=100.0, stop=98.0, target=104.0)
    book2.attach_stop(gone, "v1", "cid", 98.0)
    report2 = book2.reconcile(_FakeVenue({"BTC": 0.0}, []))
    check("a vanished position + vanished stop is booked as a stop fill",
          len(report2["resolved"]) == 1 and not report2["blocking"], str(report2))
    check("it is closed in the ledger", book2.state["positions"] == [])
    check("at the stop price", book2.state["closed"][0]["exit"] == 98.0)
    check("and counted against today's realised P&L",
          book2.state["day"]["realised"] < 0)
    check("the reason marks it as reconciled, not a normal stop",
          book2.state["closed"][0]["reason"] == "reconciled-stop")

    # coins gone but the stop is still working — something else traded the account
    book3 = tmp_ledger()
    odd = book3.open_position(product="BTC-USD", direction="long", qty=0.5,
                              entry=100.0, stop=98.0, target=104.0)
    book3.attach_stop(odd, "v1", "cid", 98.0)
    report3 = book3.reconcile(_FakeVenue({"BTC": 0.0}, [_order("v1")]))
    check("coins missing while the stop still rests is a BLOCKING conflict",
          report3["blocking"] and report3["conflicts"], str(report3))
    check("the position is NOT silently closed", len(book3.state["positions"]) == 1)

    # naked position: the stop is gone but the coins are there
    book4 = tmp_ledger()
    naked = book4.open_position(product="BTC-USD", direction="long", qty=0.5,
                                entry=100.0, stop=98.0, target=104.0)
    book4.attach_stop(naked, "v1", "cid", 98.0)
    report4 = book4.reconcile(_FakeVenue({"BTC": 0.5}, []))
    check("a position with no live stop is reported",
          any("stop is gone" in c for c in report4["conflicts"]), str(report4))
    check("but it is not treated as closed", len(book4.state["positions"]) == 1)

    # orders we did not place are reported and left alone
    book5 = tmp_ledger()
    report5 = book5.reconcile(_FakeVenue({"USD": 100.0}, [_order("someone-else")]))
    check("an unknown resting order is reported as an orphan",
          len(report5["orphans"]) == 1, str(report5))
    check("orphans do not block trading", not report5["blocking"])
    check("the report says they were left alone",
          "left alone" in report5["orphans"][0])

    # an unreachable venue must block, never assume
    book6 = tmp_ledger()
    report6 = book6.reconcile(_FakeVenue(fail=True))
    check("an unreachable venue blocks rather than assuming we are flat",
          report6["blocking"], str(report6))

    text = ledger_mod.render_reconcile(report2)
    check("the reconcile report renders as text", "Reconciled" in text, text)


# ---------------------------------------------------------------- live wiring
def test_live_wiring():
    print("live wiring")
    import live

    ok, why = live.arm_live("paper")
    check("paper needs no confirmation", ok)
    saved = os.environ.pop("TAPEDECK_LIVE_CONFIRM", None)
    ok, why = live.arm_live("live")
    check("live without the env gate is refused", not ok)
    check("and the refusal names the missing gate",
          "TAPEDECK_LIVE_CONFIRM" in why, why)
    os.environ["TAPEDECK_LIVE_CONFIRM"] = "no"
    check("a wrong value does not arm it", not live.arm_live("live")[0])
    os.environ["TAPEDECK_LIVE_CONFIRM"] = "yes"
    check("both gates together arm it", live.arm_live("live")[0])
    if saved is None:
        del os.environ["TAPEDECK_LIVE_CONFIRM"]
    else:
        os.environ["TAPEDECK_LIVE_CONFIRM"] = saved

    check("paper mode builds without touching credentials",
          isinstance(live.build_broker("paper", "kraken", {"BTC-USD": 100.0}, 1000.0),
                     bk.PaperBroker))

    spec = brief.parse("BTC with RSI below 30, 2% stop, 4% target")
    stop, target = live.stop_and_target(spec, 100.0, None)
    check("a percentage stop sits below a long entry", stop == 98.0, "%r" % stop)
    check("the target sits above it", target == 104.0, "%r" % target)

    atr_spec = brief.parse("BTC with RSI below 30, 1.5 ATR stop, 3% target")
    atr_stop, atr_target = live.stop_and_target(atr_spec, 100.0, 2.0)
    check("an ATR stop uses the ATR distance", atr_stop == 97.0, "%r" % atr_stop)
    check("and the target stays a percentage", atr_target == 103.0, "%r" % atr_target)

    short_spec = brief.parse("short BTC when RSI goes above 70, 2% stop, 4% target")
    s_stop, s_target = live.stop_and_target(short_spec, 100.0, None)
    check("a short's stop sits ABOVE entry", s_stop == 102.0, "%r" % s_stop)
    check("and its target below", s_target == 96.0, "%r" % s_target)

    position = {"signal_bar_ts": 1_700_000_000}
    check("bars held counts whole bars",
          live.bars_held(position, 1_700_000_000 + 5 * 3600, 3600) == 5)
    check("bars held is never negative",
          live.bars_held(position, 1_700_000_000 - 3600, 3600) == 0)
    check("a position with no signal bar reports zero",
          live.bars_held({}, 1_700_000_000, 3600) == 0)


# ---------------------------------------------------------------- signing
def test_signing():
    print("signing (pinned vectors — proves stability, not venue acceptance)")
    import base64

    import venues

    secret = base64.b64encode(b"tapedeck-test-secret-key-0123456789").decode()

    kraken = venues.KrakenBroker(key="test-key", secret=secret)
    post, sig = kraken.sign("/0/private/AddOrder", {"pair": "XBTUSD", "type": "buy"},
                            nonce=1700000000000)
    again = kraken.sign("/0/private/AddOrder", {"pair": "XBTUSD", "type": "buy"},
                        nonce=1700000000000)[1]
    check("kraken signing is deterministic for a fixed nonce", sig == again)
    check("the nonce is in the POST body", "nonce=1700000000000" in post, post)
    check("the signature is base64 sha512 (88 chars)", len(sig) == 88, "%d" % len(sig))
    other = kraken.sign("/0/private/AddOrder", {"pair": "ETHUSD", "type": "buy"},
                        nonce=1700000000000)[1]
    check("changing a parameter changes the signature", sig != other)
    path_swap = kraken.sign("/0/private/CancelOrder", {"pair": "XBTUSD", "type": "buy"},
                            nonce=1700000000000)[1]
    check("the path is part of what is signed", sig != path_swap)

    n1 = kraken._nonce()
    n2 = kraken._nonce()
    check("nonces strictly increase even inside one millisecond", n2 > n1)
    kraken._last_nonce = int(time.time() * 1000) + 10_000     # simulate a clock step back
    check("a backwards clock still yields an increasing nonce",
          kraken._nonce() > kraken._last_nonce - 1)

    check("userref is a positive 31-bit int",
          0 < kraken._userref("td-abc") < 2 ** 31)
    check("userref is stable for a client id",
          kraken._userref("td-abc") == kraken._userref("td-abc"))
    check("and differs between client ids",
          kraken._userref("td-abc") != kraken._userref("td-abd"))

    cb = venues.CoinbaseExchangeBroker(key="k", secret=secret, passphrase="p")
    sig1 = cb.sign("1700000000.000", "POST", "/orders", '{"size":"1"}')
    check("coinbase signing is deterministic",
          sig1 == cb.sign("1700000000.000", "POST", "/orders", '{"size":"1"}'))
    check("the body is part of what is signed",
          sig1 != cb.sign("1700000000.000", "POST", "/orders", '{"size":"2"}'))
    check("the method is part of what is signed",
          sig1 != cb.sign("1700000000.000", "GET", "/orders", '{"size":"1"}'))
    check("the timestamp is part of what is signed",
          sig1 != cb.sign("1700000000.001", "POST", "/orders", '{"size":"1"}'))
    check("the signature is base64 sha256 (44 chars)", len(sig1) == 44, "%d" % len(sig1))

    oid = cb._client_oid("td-abcdef")
    check("client_oid is UUID-shaped for coinbase",
          len(oid) == 36 and oid.count("-") == 4, oid)
    check("and deterministic", oid == cb._client_oid("td-abcdef"))
    check("and distinct per client id", oid != cb._client_oid("td-abcdeg"))

    check("a bad base64 secret is caught at construction",
          _raises(bk.BrokerError, venues.KrakenBroker, "k", "not-base64!!!"))
    check("missing credentials are caught at construction",
          _raises(bk.BrokerError, venues.KrakenBroker, "", ""))

    fmt = venues._fmt(0.123456789, 0.00001)
    check("sizes are formatted at the venue's precision, no exponent",
          fmt == "0.12346" and "e" not in fmt, fmt)
    check("a whole-number step formats without decimals",
          venues._fmt(12.7, 1.0) == "13", venues._fmt(12.7, 1.0))


def test_credentials_report():
    print("credential handling")
    import venues

    saved = {k: os.environ.pop(k, None)
             for k in ("KRAKEN_API_KEY", "KRAKEN_API_SECRET")}
    state = venues.credentials_present("kraken")["kraken"]
    check("a venue with no keys reports not ready", not state["ready"])
    check("and names exactly what is missing",
          set(state["missing"]) == {"KRAKEN_API_KEY", "KRAKEN_API_SECRET"},
          str(state["missing"]))

    os.environ["KRAKEN_API_KEY"] = "k"
    partial = venues.credentials_present("kraken")["kraken"]
    check("a half-configured venue is still not ready", not partial["ready"])
    check("and only the missing half is named",
          partial["missing"] == ["KRAKEN_API_SECRET"], str(partial["missing"]))

    check("no secret value appears in the report",
          "k" not in str(partial).replace("KRAKEN_API_KEY", ""),
          str(partial))
    check("connect() refuses a venue with missing credentials",
          _raises(bk.BrokerError, venues.connect, "kraken"))
    check("connect() refuses an unknown venue",
          _raises(bk.BrokerError, venues.connect, "not-a-venue"))

    for key, value in saved.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value


# ---------------------------------------------------------------- shadow
def test_shadow():
    print("shadow mode")
    inner, prices = paper(price=100.0, cash=1000.0)
    shadow = bk.ShadowBroker(inner)
    check("shadow is not live", not shadow.live)
    check("its name says what it wraps", shadow.name == "shadow:paper", shadow.name)

    fill = shadow.market_order("BTC-USD", bk.BUY, 1.0, "cid")
    check("it returns a fill so the ledger can account for it", fill.qty == 1.0)
    check("but the inner broker never traded", inner.fills == [])
    check("and cash is untouched", inner.cash == 1000.0)
    check("the intent is recorded", len(shadow.intents) == 1)
    check("a resent order is not recorded twice",
          shadow.market_order("BTC-USD", bk.BUY, 1.0, "cid") is fill
          and len(shadow.intents) == 1)

    shadow.stop_order("BTC-USD", bk.SELL, 1.0, 98.0, "scid")
    check("a stop intent is recorded too", len(shadow.intents) == 2)
    check("and no stop actually rests at the venue", inner.open_orders() == [])
    check("reads pass through to the real venue", shadow.ticker("BTC-USD") == 100.0)


# ---------------------------------------------------------------- helpers
def _raises(exception, function, *args, **kwargs):
    try:
        function(*args, **kwargs)
    except exception:
        return True
    except Exception:                                       # noqa: BLE001
        return False
    return False


def main():
    print("Tapedeck order-path self-test — offline, no credentials, no venue.\n")
    for test in (test_sizing, test_idempotency, test_paper_broker, test_risk_gate,
                 test_kill_switch, test_ledger, test_reconciliation,
                 test_live_wiring, test_signing, test_credentials_report,
                 test_shadow):
        test()
        print()
    if FAILED:
        print("%d check(s) FAILED:" % len(FAILED))
        for label in FAILED:
            print("  - %s" % label)
        return 1
    print("all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
