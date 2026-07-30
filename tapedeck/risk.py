#!/usr/bin/env python3
"""
Tapedeck — the pre-trade gate.

Every entry passes through `RiskEngine.check_entry()` before an order exists.
It answers with a `Decision`: allowed or not, why, and at what size. Nothing in
the live loop is permitted to size a trade by itself.

THE GATE NEVER BLOCKS AN EXIT. Read that twice, because it is the one asymmetry
that matters. A risk limit that can stop you from *closing* a position is not a
risk limit, it is a trap — a daily-loss stop that refuses the sell order which
would end the losing day is precisely backwards. Entries are gated; exits,
cancels and flattens always proceed.

The checks, in the order they run:

    kill switch       a file on disk halts new entries, immediately
    shorting          refused unless the broker can actually borrow (spot cannot)
    daily loss        realised losses past the day's cap stop new entries
    position count    one at a time by default
    cooldown          N bars of silence after a loss
    exposure          total open notional ceiling
    size              clamped down to the per-trade cap; refused below the floor
    price sanity      an intended fill far from the reference price is refused
    stop sanity       a stop on the wrong side, or absurdly tight, is refused
    funds             the quote balance has to actually cover it, fees included

Sizes are clamped DOWN, never up. When a limit and a request disagree, the limit
wins and the decision says so.

None of this makes a strategy profitable. It bounds how wrong one night can go.
"""
import os
import time
from collections import namedtuple

Decision = namedtuple("Decision", "ok reason notional notes")

# Deliberately small defaults. A user who wants size has to say so; a user who
# forgets to configure anything risks pocket change rather than the account.
DEFAULTS = dict(
    max_notional=25.0,          # quote per trade
    min_notional=5.0,           # below this, fees dominate and the venue may refuse
    max_exposure=50.0,          # total open notional
    max_positions=1,
    daily_loss_stop=25.0,       # realised loss in one UTC day that halts entries
    price_band_pct=3.0,         # intended fill vs reference price
    min_stop_pct=0.10,          # a stop closer than this is noise, not protection
    max_stop_pct=25.0,          # a stop further than this is not a stop
    cooldown_bars=1,            # bars of silence after a losing trade
    require_stop=True,
)


class Limits:
    """Numbers the gate enforces. Everything is quote currency (USD) or percent."""

    def __init__(self, **kwargs):
        unknown = set(kwargs) - set(DEFAULTS) - {"kill_file"}
        if unknown:
            raise ValueError("unknown risk limit(s): %s" % ", ".join(sorted(unknown)))
        merged = dict(DEFAULTS)
        merged.update({k: v for k, v in kwargs.items() if v is not None})
        for key, value in merged.items():
            setattr(self, key, value)
        self.kill_file = kwargs.get("kill_file") or os.environ.get(
            "TAPEDECK_KILL_FILE", os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                               "HALT"))

    def describe(self):
        return [
            "max %s per trade, %s total open" % (_money(self.max_notional),
                                                 _money(self.max_exposure)),
            "at most %d position%s at a time" % (self.max_positions,
                                                 "" if self.max_positions == 1 else "s"),
            "entries stop for the day after %s of realised loss"
            % _money(self.daily_loss_stop),
            "%d bar%s cooldown after a loss" % (self.cooldown_bars,
                                                "" if self.cooldown_bars == 1 else "s"),
            "refuse a fill more than %g%% from the reference price" % self.price_band_pct,
            "stop must sit between %g%% and %g%% away" % (self.min_stop_pct, self.max_stop_pct),
            "kill switch: create %s to halt new entries" % self.kill_file,
        ]


def _money(value):
    return "%s%s" % ("$", format(value, ",.2f"))


class RiskEngine:
    """
    Stateless with respect to trading — it reads a snapshot and answers.

    `snapshot` is what the ledger knows right now:
        open_positions   list of dicts with 'notional'
        realised_today   negative for a losing day
        last_loss_bar_ts epoch of the bar that closed the last losing trade
        bar_seconds      the timeframe, so cooldown can be measured in bars
    """

    def __init__(self, limits=None):
        self.limits = limits or Limits()
        self.rejections = []

    # -- the switch ----------------------------------------------------
    def halted(self):
        """
        Is the kill switch on?

        A file, not a flag: you can stop a running loop from another terminal,
        from a phone over SSH, from a cron job, without finding the process.
        `touch HALT` and no new position will be opened. Open positions keep being
        managed to their stop or target — abandoning a live position unmanaged
        would be a worse outcome than the one you were trying to prevent.
        """
        return os.path.exists(self.limits.kill_file)

    def halt_reason(self):
        try:
            with open(self.limits.kill_file, encoding="utf-8") as fh:
                note = fh.read().strip()
            return note or "kill switch file present"
        except OSError:
            return "kill switch file present"

    # -- the gate ------------------------------------------------------
    def check_entry(self, product, direction, price, stop_price, requested_notional,
                    snapshot, broker, reference_price=None, quote_balance=None):
        notes = []
        lim = self.limits

        if self.halted():
            return self._no("halted — %s" % self.halt_reason(), notes)

        if direction == "short" and not getattr(broker, "can_short", False):
            return self._no(
                "the brief is short and %s is a spot account — selling what you do "
                "not hold requires margin, which this project deliberately has no "
                "path for" % broker.name, notes)

        realised = snapshot.get("realised_today", 0.0)
        if realised <= -abs(lim.daily_loss_stop):
            return self._no("daily loss stop: %s realised today, cap is %s"
                            % (_money(realised), _money(-abs(lim.daily_loss_stop))), notes)

        open_positions = snapshot.get("open_positions") or []
        if len(open_positions) >= lim.max_positions:
            return self._no("already holding %d position%s (cap %d)"
                            % (len(open_positions),
                               "" if len(open_positions) == 1 else "s",
                               lim.max_positions), notes)

        cooldown = self._cooldown_left(snapshot)
        if cooldown > 0:
            return self._no("cooling off for %d more bar%s after the last loss"
                            % (cooldown, "" if cooldown == 1 else "s"), notes)

        notional = float(requested_notional)
        if notional > lim.max_notional:
            notes.append("size clamped from %s to the %s per-trade cap"
                         % (_money(notional), _money(lim.max_notional)))
            notional = lim.max_notional

        exposure = sum(float(p.get("notional") or 0) for p in open_positions)
        room = lim.max_exposure - exposure
        if room <= 0:
            return self._no("no exposure room: %s already open, ceiling is %s"
                            % (_money(exposure), _money(lim.max_exposure)), notes)
        if notional > room:
            notes.append("size clamped to %s — the remaining exposure room"
                         % _money(room))
            notional = room

        if notional < lim.min_notional:
            return self._no("%s is below the %s minimum — fees would eat it"
                            % (_money(notional), _money(lim.min_notional)), notes)

        if price is None or price <= 0:
            return self._no("no usable price for %s" % product, notes)

        if reference_price:
            drift = abs(price / reference_price - 1.0) * 100.0
            if drift > lim.price_band_pct:
                return self._no(
                    "price sanity: the venue quotes %s but the bar that fired closed "
                    "at %s (%.2f%% apart, band is %g%%) — a stale feed or a fast "
                    "market, either way not a fill to take blind"
                    % (_money(price), _money(reference_price), drift, lim.price_band_pct),
                    notes)

        if lim.require_stop and not stop_price:
            return self._no("no stop price — entering without one is not permitted", notes)
        if stop_price:
            long = direction != "short"
            if (long and stop_price >= price) or (not long and stop_price <= price):
                return self._no("stop %s is on the wrong side of %s for a %s"
                                % (_money(stop_price), _money(price), direction), notes)
            distance = abs(price - stop_price) / price * 100.0
            if distance < lim.min_stop_pct:
                return self._no("stop is %.3f%% away — closer than the %g%% floor, it "
                                "would be triggered by noise"
                                % (distance, lim.min_stop_pct), notes)
            if distance > lim.max_stop_pct:
                return self._no("stop is %.1f%% away — past the %g%% ceiling"
                                % (distance, lim.max_stop_pct), notes)
            notes.append("risking %s if the stop fills (%.2f%% of the position)"
                         % (_money(notional * distance / 100.0), distance))

        if quote_balance is not None:
            needed = notional * 1.01          # headroom for fees on the way in
            if quote_balance < needed:
                return self._no("balance %s cannot cover %s plus fees"
                                % (_money(quote_balance), _money(notional)), notes)

        return Decision(True, "within limits", notional, notes)

    # -- helpers -------------------------------------------------------
    def _cooldown_left(self, snapshot):
        bars = self.limits.cooldown_bars
        last = snapshot.get("last_loss_bar_ts")
        step = snapshot.get("bar_seconds")
        if not bars or not last or not step:
            return 0
        elapsed = (time.time() - last) / step
        return max(0, int(bars - elapsed + 0.999))

    def _no(self, reason, notes):
        self.rejections.append(reason)
        return Decision(False, reason, 0.0, notes)


def caveats():
    """What the gate does not protect you from. Printed with every live run."""
    return [
        "A stop is an instruction, not a guarantee. Gaps, halts and thin books all "
        "fill it worse than its price — sometimes far worse.",
        "Limits are per-process. Two Tapedecks on one account do not know about "
        "each other and will happily double your exposure.",
        "The daily loss stop counts REALISED losses. An open position can be far "
        "underwater without tripping it.",
        "Nothing here models funding, borrow, tax, or a venue freezing withdrawals.",
        "A backtested edge is not evidence that live fills will resemble the "
        "backtest's. Costs, latency and slippage are where paper profits go.",
    ]


if __name__ == "__main__":
    engine = RiskEngine()
    print("Risk limits in force by default:\n")
    for line in engine.limits.describe():
        print("  - %s" % line)
    print("\nWhat it cannot protect you from:\n")
    for line in caveats():
        print("  - %s" % line)
