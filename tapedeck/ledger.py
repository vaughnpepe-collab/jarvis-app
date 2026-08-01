#!/usr/bin/env python3
"""
Tapedeck — position state that survives the process dying.

The loop will be killed mid-trade eventually: a laptop lid, an OOM, a deploy, a
power cut. When it comes back it must not guess. This module is the memory, and
`reconcile()` is the part that matters — on every start it asks the venue what is
actually true and compares.

Three failure modes it exists to catch:

  1. THE LEDGER THINKS WE HOLD SOMETHING THE VENUE DOESN'T. Usually the protective
     stop filled while we were dead. The position is closed against the stop
     price, marked `reconciled`, and reported — not silently forgotten, because
     the loss is real and the daily-loss counter has to see it.
  2. THE PROTECTIVE STOP IS GONE BUT THE POSITION IS NOT. Cancelled by hand,
     expired, or never accepted. That is a naked position, so it is reported as a
     conflict and the loop replaces the stop before doing anything else.
  3. THE VENUE HOLDS ORDERS WE DON'T KNOW ABOUT. Reported, never auto-cancelled —
     they might be yours from another tool, and cancelling someone else's working
     order because our JSON file is missing a line is not a decision software gets
     to make.

Writes are atomic: a temp file in the same directory, then `os.replace`. A
half-written ledger is worse than no ledger, and `os.replace` is atomic on POSIX
and on Windows.

Realised P&L is tracked per UTC day so the risk gate's daily loss stop has
something honest to read. The day rolls over on date change, not on a timer from
when the process happened to start.
"""
import json
import os
import time

from broker import trim

VERSION = 1


def _today():
    return time.strftime("%Y-%m-%d", time.gmtime())


def _blank(mode="paper", venue="paper"):
    return {
        "version": VERSION,
        "mode": mode,
        "venue": venue,
        "positions": [],
        "submitted": {},
        "closed": [],
        "day": {"date": _today(), "realised": 0.0},
        "last_loss_bar_ts": None,
        "started": time.time(),
    }


class Ledger:
    def __init__(self, path, mode="paper", venue="paper"):
        self.path = path
        self.state = _blank(mode, venue)
        self.load()
        self.state["mode"] = mode
        self.state["venue"] = venue
        self._roll_day()

    # -- persistence ---------------------------------------------------
    def load(self):
        try:
            with open(self.path, encoding="utf-8") as fh:
                data = json.load(fh)
        except (OSError, ValueError):
            return False
        if not isinstance(data, dict) or data.get("version") != VERSION:
            return False
        self.state = data
        for key, value in _blank().items():         # tolerate an older, thinner file
            self.state.setdefault(key, value)
        return True

    def save(self):
        """Atomic: write beside the target, then replace it in one step."""
        directory = os.path.dirname(os.path.abspath(self.path)) or "."
        os.makedirs(directory, exist_ok=True)
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(self.state, fh, indent=1, sort_keys=True)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, self.path)

    def _roll_day(self):
        if self.state["day"].get("date") != _today():
            self.state["day"] = {"date": _today(), "realised": 0.0}

    # -- idempotency ---------------------------------------------------
    def was_submitted(self, cid):
        """
        Have we already sent this exact order?

        The client id is derived from the bar that triggered it, so this survives a
        restart: the loop that comes back up on the same bar sees its own previous
        send and does not repeat it. This is the last line of defence against a
        double position — the venue's own duplicate rejection is the first.
        """
        return cid in self.state["submitted"]

    def record_submitted(self, cid, kind, product, venue_id=""):
        self.state["submitted"][cid] = {
            "kind": kind, "product": product, "venue_id": venue_id, "ts": time.time()}
        # keep the file from growing without bound over a long-running loop
        if len(self.state["submitted"]) > 2000:
            for old in sorted(self.state["submitted"],
                              key=lambda c: self.state["submitted"][c]["ts"])[:500]:
                del self.state["submitted"][old]
        self.save()

    # -- positions -----------------------------------------------------
    def open_position(self, **fields):
        position = {
            "product": fields["product"],
            "direction": fields.get("direction", "long"),
            "qty": fields["qty"],
            "entry": fields["entry"],
            "stop": fields.get("stop"),
            "target": fields.get("target"),
            "notional": fields["qty"] * fields["entry"],
            "opened_ts": fields.get("opened_ts") or time.time(),
            "signal_bar_ts": fields.get("signal_bar_ts"),
            "entry_cid": fields.get("entry_cid"),
            "stop_venue_id": fields.get("stop_venue_id"),
            "stop_cid": fields.get("stop_cid"),
            "max_hold": fields.get("max_hold"),
            "fees": fields.get("fees", 0.0),
        }
        self.state["positions"].append(position)
        self.save()
        return position

    def position_for(self, product):
        for position in self.state["positions"]:
            if position["product"] == product:
                return position
        return None

    def attach_stop(self, position, venue_id, cid, stop_price):
        position["stop_venue_id"] = venue_id
        position["stop_cid"] = cid
        position["stop"] = stop_price
        self.save()

    def close_position(self, position, exit_price, reason, fees=0.0, bar_ts=None):
        long = position["direction"] != "short"
        move = ((exit_price - position["entry"]) if long
                else (position["entry"] - exit_price))
        gross = move * position["qty"]
        total_fees = float(position.get("fees") or 0) + float(fees or 0)
        pnl = gross - total_fees

        record = dict(position)
        record.update({
            "exit": exit_price, "reason": reason, "closed_ts": time.time(),
            "gross": gross, "fees": total_fees, "pnl": pnl,
            "pct": (move / position["entry"] * 100.0) if position["entry"] else 0.0,
        })
        self.state["closed"].append(record)
        self.state["positions"] = [p for p in self.state["positions"]
                                   if p is not position]
        self._roll_day()
        self.state["day"]["realised"] = round(
            self.state["day"].get("realised", 0.0) + pnl, 10)
        if pnl < 0:
            self.state["last_loss_bar_ts"] = bar_ts or time.time()
        self.save()
        return record

    # -- views ---------------------------------------------------------
    def snapshot(self, bar_seconds=None):
        self._roll_day()
        return {
            "open_positions": list(self.state["positions"]),
            "realised_today": self.state["day"].get("realised", 0.0),
            "last_loss_bar_ts": self.state.get("last_loss_bar_ts"),
            "bar_seconds": bar_seconds,
        }

    def stats(self):
        closed = self.state["closed"]
        if not closed:
            return {"trades": 0, "pnl": 0.0, "wins": 0, "losses": 0,
                    "hit_rate": None, "fees": 0.0}
        wins = [t for t in closed if t["pnl"] > 0]
        return {
            "trades": len(closed),
            "pnl": sum(t["pnl"] for t in closed),
            "wins": len(wins),
            "losses": len(closed) - len(wins),
            "hit_rate": len(wins) / len(closed) * 100.0,
            "fees": sum(t.get("fees") or 0 for t in closed),
        }

    # -- reconciliation ------------------------------------------------
    def reconcile(self, broker):
        """
        Compare what we believe against what the venue says. Returns a report.

        `report["blocking"]` is True when a human should look before anything
        trades. The loop refuses to open new positions while it is set.
        """
        report = {"conflicts": [], "resolved": [], "orphans": [], "blocking": False}
        try:
            balances = broker.balances()
        except Exception as exc:                    # noqa: BLE001 - report, never crash
            report["conflicts"].append("could not read balances from %s: %s"
                                       % (broker.name, exc))
            report["blocking"] = True
            return report

        for position in list(self.state["positions"]):
            product = position["product"]
            base = product.partition("-")[0]
            held = float(balances.get(base, 0.0))
            expected = float(position["qty"])

            try:
                resting = broker.open_orders(product)
            except Exception as exc:                # noqa: BLE001
                report["conflicts"].append("could not list open orders for %s: %s"
                                           % (product, exc))
                report["blocking"] = True
                continue
            stop_id = position.get("stop_venue_id")
            stop_alive = any(o.venue_id == stop_id for o in resting) if stop_id else False

            # 1. the venue does not have the coins the ledger says we hold
            if held < expected * 0.95:
                if stop_id and not stop_alive:
                    price = position.get("stop") or position["entry"]
                    self.close_position(position, price, "reconciled-stop")
                    report["resolved"].append(
                        "%s: the protective stop filled while we were not running — "
                        "closed at the stop price %s and counted against today's "
                        "realised P&L" % (product, format(price, ",.2f")))
                else:
                    report["conflicts"].append(
                        "%s: ledger says %s %s, venue shows %s and the stop is still "
                        "working. Something else traded this account."
                        % (product, trim(expected), base, trim(held)))
                    report["blocking"] = True
                continue

            # 2. the position is real but unprotected
            if stop_id and not stop_alive:
                report["conflicts"].append(
                    "%s: position is open but its protective stop is gone — the loop "
                    "will replace it before anything else" % product)
            elif not stop_id:
                report["conflicts"].append(
                    "%s: position has no stop recorded at all" % product)

        # 3. orders at the venue that we did not place
        known = {p.get("stop_venue_id") for p in self.state["positions"]}
        try:
            for order in broker.open_orders():
                if order.venue_id and order.venue_id not in known:
                    report["orphans"].append(
                        "%s %s %s @ %s (id %s) — not ours as far as this ledger "
                        "knows; left alone" % (order.product, order.side, order.kind,
                                               order.price, order.venue_id))
        except Exception:                           # noqa: BLE001 - orphans are advisory
            pass
        return report


def render_reconcile(report):
    lines = []
    if report["resolved"]:
        lines.append("  Reconciled while we were away:")
        lines += ["    · %s" % r for r in report["resolved"]]
    if report["conflicts"]:
        lines.append("  ! Conflicts between this ledger and the venue:")
        lines += ["    · %s" % c for c in report["conflicts"]]
    if report["orphans"]:
        lines.append("  Orders at the venue this ledger does not recognise:")
        lines += ["    · %s" % o for o in report["orphans"]]
    if not lines:
        lines.append("  Ledger and venue agree.")
    return "\n".join(lines)


if __name__ == "__main__":
    import sys
    path = sys.argv[1] if len(sys.argv) > 1 else "state/paper.json"
    book = Ledger(path)
    stats = book.stats()
    print("Ledger %s — mode %s, venue %s" % (path, book.state["mode"], book.state["venue"]))
    print("  open positions   %d" % len(book.state["positions"]))
    for position in book.state["positions"]:
        print("    %s %s %s @ %s stop %s"
              % (position["direction"], trim(position["qty"]), position["product"],
                 format(position["entry"], ",.2f"),
                 format(position["stop"] or 0, ",.2f")))
    print("  closed trades    %d" % stats["trades"])
    if stats["trades"]:
        print("  realised P&L     %+.2f  (%d won / %d lost, %.1f%% hit rate)"
              % (stats["pnl"], stats["wins"], stats["losses"], stats["hit_rate"]))
    print("  realised today   %+.2f" % book.state["day"].get("realised", 0.0))
