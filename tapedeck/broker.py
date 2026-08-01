#!/usr/bin/env python3
"""
Tapedeck — the order path.

Everything that can turn a signal into an order lives behind the `Broker`
interface here. The interface is deliberately narrow, because a narrow order path
is an auditable one:

    market_order()   enter or exit, at whatever the book gives us
    stop_order()     one protective stop, resting at the venue
    cancel()         withdraw a resting order
    balances()       what the venue says we hold
    open_orders()    what the venue says is working

There is no leverage, no margin, no borrow, and no short-selling of spot. There
is no withdrawal or transfer call anywhere in this module, and there never should
be — trading permission is all this project asks of a key.

Two rules that exist because of how real order paths fail:

  1. EVERY ORDER CARRIES A DETERMINISTIC CLIENT ID. `client_id()` hashes the
     market, the side and the *bar* that triggered it. Send it twice — a retry
     after a timeout, a restart mid-loop — and the venue sees the same id and
     rejects the duplicate instead of doubling your size. A random id would make
     that failure silent and expensive.
  2. SIZES ARE ROUNDED DOWN TO THE VENUE'S INCREMENT, in Decimal, before they are
     sent. Floating point sizing is how you get a rejected order at 3am, or an
     order for 0.30000000000000004 BTC.

`PaperBroker` implements the whole interface against simulated money using the
same cost model as the backtester, so a paper run and a backtest of the same
rules are comparable rather than merely similar.
"""
import decimal
import hashlib
import json
import os
import time
from collections import namedtuple

# Sizes/quantities are always BASE units (BTC in BTC-USD).
# Notional/cash amounts are always QUOTE units (USD in BTC-USD).
Order = namedtuple("Order", "client_id venue_id product side kind qty price status")
Fill = namedtuple("Fill", "client_id venue_id product side qty price fee ts")
Market = namedtuple("Market", "product base quote min_size size_step price_step")

BUY, SELL = "buy", "sell"


class BrokerError(RuntimeError):
    """The venue said no, or could not be reached."""


class Rejected(BrokerError):
    """The order was refused before it was sent — bad size, no funds, no market."""


# ---------------------------------------------------------------- ids
def client_id(product, side, bar_ts, tag="e"):
    """
    A stable id for the order this bar wants to place.

    Same market + side + bar + tag always gives the same id, which is what makes
    a retry safe: the second send is a duplicate the venue can reject, not a
    second position. `tag` separates the entry ("e"), the protective stop ("s")
    and the exit ("x") on one bar.
    """
    raw = "%s|%s|%d|%s" % (product, side, int(bar_ts), tag)
    return "td-" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:20]


# ---------------------------------------------------------------- sizing
def _dec(value):
    # str() first: Decimal(0.1) is 0.1000000000000000055511151231257827, and
    # rounding against a venue increment with that is how sizes come out wrong.
    return decimal.Decimal(str(value))


def round_down(value, step):
    """Largest multiple of `step` that is <= value. Exact, via Decimal."""
    if not step:
        return float(value)
    v, s = _dec(value), _dec(step)
    return float((v / s).to_integral_value(rounding=decimal.ROUND_FLOOR) * s)


def round_price(value, step):
    """Nearest tick. A price the venue can't represent is a rejected order."""
    if not step:
        return float(value)
    v, s = _dec(value), _dec(step)
    return float((v / s).to_integral_value(rounding=decimal.ROUND_HALF_UP) * s)


def size_for(notional, price, market):
    """
    Base quantity for a target notional, rounded down to the venue's increment.

    Rounding *down* is on purpose: rounding up spends more than the risk limit
    approved, and the limit is the whole point.
    """
    if price <= 0:
        raise Rejected("price %r is not usable for sizing" % price)
    qty = round_down(notional / price, market.size_step)
    if qty < market.min_size:
        raise Rejected(
            "notional %s at %s works out to %s %s, below the venue minimum of %s"
            % (format(notional, ",.2f"), format(price, ",.2f"), trim(qty),
               market.base, trim(market.min_size)))
    return qty


def trim(value):
    """
    Print a size without exponent notation or a tail of zeros.

    Public because sizes get printed from every layer — the loop, the ledger, the
    reconcile report — and `8e-05 BTC` in a log at 3am helps nobody.
    """
    text = format(_dec(value), "f")
    return text.rstrip("0").rstrip(".") if "." in text else text


# ---------------------------------------------------------------- interface
class Broker:
    """
    What the live loop is allowed to ask a venue to do.

    `live` is the honest flag: True only when a fill costs real money. The loop
    prints it, the ledger records it, and the risk gate reads it.
    """

    name = "abstract"
    live = False
    can_short = False           # spot cannot borrow; margin venues would override

    def market(self, product):
        """
        Trading rules for one product (min size, increments), cached per process.

        Cached in the base rather than in each adapter because every venue pays
        an HTTP round trip for this and the order path asks repeatedly — sizing
        the trade, sending it, then formatting the stop. Increments do not change
        between bars; re-fetching them three times per entry is pure latency in
        front of an order.
        """
        cache = self.__dict__.setdefault("_market_cache", {})
        if product not in cache:
            cache[product] = self._fetch_market(product)
        return cache[product]

    def _fetch_market(self, product):
        """Ask the venue for one product's trading rules. Adapters implement this."""
        raise NotImplementedError

    def ticker(self, product):
        """Last traded price, as a float."""
        raise NotImplementedError

    def balances(self):
        """{'USD': 1234.5, 'BTC': 0.01} — free balance, per currency."""
        raise NotImplementedError

    def market_order(self, product, side, qty, cid):
        """Send a market order. Returns a Fill. Raises BrokerError/Rejected."""
        raise NotImplementedError

    def stop_order(self, product, side, qty, stop_price, cid):
        """Rest a protective stop at the venue. Returns an Order."""
        raise NotImplementedError

    def cancel(self, venue_id, product=None):
        """Withdraw a resting order. Must not raise if it is already gone."""
        raise NotImplementedError

    def open_orders(self, product=None):
        """Resting orders the venue is holding for us."""
        raise NotImplementedError

    # -- shared helpers -------------------------------------------------
    def describe(self):
        return "%s (%s)" % (self.name, "LIVE — real money" if self.live else "simulated")


# ---------------------------------------------------------------- paper
class PaperBroker(Broker):
    """
    Simulated money, real prices.

    Fills apply the backtester's cost model — `fee_pct` and `slippage_pct` per
    side — so paper results line up with a backtest of the same rules instead of
    flattering them. Market buys fill at price*(1+slippage), sells at
    price*(1-slippage), and the fee comes out of quote either way.

    Resting stops are held in `self.resting` and triggered by `poll(bar)`, which
    the live loop calls once per closed bar. A stop triggers on the bar's
    low/high and fills at the stop price — the same pessimistic convention the
    backtester uses, and for the same reason: the bar doesn't say where inside
    itself the price went first.
    """

    name = "paper"
    live = False

    def __init__(self, cash=10000.0, price_source=None, fee_pct=0.10,
                 slippage_pct=0.05, markets=None, state_path=None):
        self.cash = float(cash)
        self.holdings = {}                  # base currency -> qty
        self.resting = {}                   # venue_id -> Order
        self.fills = []
        self.fee_pct = fee_pct
        self.slippage_pct = slippage_pct
        self._price_source = price_source   # callable(product) -> float
        self._markets = markets or {}
        self._seq = 0
        self._seen = {}                     # client_id -> Fill/Order, for idempotency
        # A paper venue that forgets everything on exit is not a simulation of a
        # venue, it is a trap: the next start sees no coins and no resting stop,
        # which is indistinguishable from "your stop filled while you were away".
        # That fabricated a loss on every restart until this was persisted.
        self._state_path = state_path
        self._load()

    # -- persistence ---------------------------------------------------
    def _load(self):
        """Restore cash, holdings and resting stops from the last run."""
        if not self._state_path:
            return
        try:
            with open(self._state_path, encoding="utf-8") as fh:
                data = json.load(fh)
        except (OSError, ValueError):
            return
        self.cash = float(data.get("cash", self.cash))
        self.holdings = {k: float(v) for k, v in (data.get("holdings") or {}).items()}
        self._seq = int(data.get("seq", 0))
        self.resting = {k: Order(*v) for k, v in (data.get("resting") or {}).items()}

    def _persist(self):
        """Atomic, same as the ledger — a half-written paper book is a fake loss."""
        if not self._state_path:
            return
        os.makedirs(os.path.dirname(os.path.abspath(self._state_path)) or ".",
                    exist_ok=True)
        tmp = self._state_path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump({"cash": self.cash, "holdings": self.holdings, "seq": self._seq,
                       "resting": {k: list(v) for k, v in self.resting.items()}},
                      fh, indent=1, sort_keys=True)
        os.replace(tmp, self._state_path)

    # -- market data ---------------------------------------------------
    def _fetch_market(self, product):
        if product in self._markets:
            return self._markets[product]
        base, _, quote = product.partition("-")
        # Sane generic increments. A real venue's numbers arrive from its API;
        # these only have to be plausible enough to exercise the sizing path.
        return Market(product, base or product, quote or "USD",
                      min_size=0.0001, size_step=0.00000001, price_step=0.01)

    def ticker(self, product):
        if self._price_source is None:
            raise BrokerError("paper broker has no price source")
        price = self._price_source(product)
        if not price or price <= 0:
            raise BrokerError("no usable price for %s" % product)
        return float(price)

    def balances(self):
        out = {"USD": self.cash}
        out.update({k: v for k, v in self.holdings.items() if v})
        return out

    # -- orders --------------------------------------------------------
    def market_order(self, product, side, qty, cid):
        if cid in self._seen:
            return self._seen[cid]          # duplicate send: same answer, no new fill
        market = self.market(product)
        if qty < market.min_size:
            raise Rejected("%s below minimum size %s" % (trim(qty), trim(market.min_size)))

        raw = self.ticker(product)
        slip = self.slippage_pct / 100.0
        price = raw * (1 + slip) if side == BUY else raw * (1 - slip)
        gross = price * qty
        fee = gross * self.fee_pct / 100.0

        if side == BUY:
            if gross + fee > self.cash + 1e-9:
                raise Rejected("paper cash %s cannot cover %s + %s fee"
                               % (format(self.cash, ",.2f"), format(gross, ",.2f"),
                                  format(fee, ",.2f")))
            self.cash -= gross + fee
            self.holdings[market.base] = self.holdings.get(market.base, 0.0) + qty
        else:
            held = self.holdings.get(market.base, 0.0)
            if qty > held + 1e-12:
                raise Rejected("paper holdings %s %s cannot cover a sale of %s"
                               % (trim(held), market.base, trim(qty)))
            self.holdings[market.base] = held - qty
            self.cash += gross - fee

        self._seq += 1
        fill = Fill(cid, "paper-%d" % self._seq, product, side, qty, price, fee, time.time())
        self.fills.append(fill)
        self._seen[cid] = fill
        self._persist()
        return fill

    def stop_order(self, product, side, qty, stop_price, cid):
        if cid in self._seen:
            return self._seen[cid]
        market = self.market(product)
        self._seq += 1
        order = Order(cid, "paper-%d" % self._seq, product, side, "stop", qty,
                      round_price(stop_price, market.price_step), "open")
        self.resting[order.venue_id] = order
        self._seen[cid] = order
        self._persist()
        return order

    def cancel(self, venue_id, product=None):
        self.resting.pop(venue_id, None)    # already gone is not an error
        self._persist()

    def open_orders(self, product=None):
        return [o for o in self.resting.values()
                if product is None or o.product == product]

    # -- simulation ----------------------------------------------------
    def poll(self, bar, product):
        """
        Did a resting stop trigger inside this bar? Returns the Fills it produced.

        Called once per closed bar by the live loop. A sell stop triggers when the
        bar's low reaches it, a buy stop when the high does, and it fills *at* the
        stop price — no gap modelling, which flatters a gap-down and is called out
        in the caveats rather than hidden.
        """
        out = []
        for venue_id, order in list(self.resting.items()):
            if order.product != product:
                continue
            hit = (bar.low <= order.price if order.side == SELL
                   else bar.high >= order.price)
            if not hit:
                continue
            del self.resting[venue_id]
            market = self.market(product)
            gross = order.price * order.qty
            fee = gross * self.fee_pct / 100.0
            if order.side == SELL:
                self.holdings[market.base] = max(
                    0.0, self.holdings.get(market.base, 0.0) - order.qty)
                self.cash += gross - fee
            else:
                self.cash -= gross + fee
                self.holdings[market.base] = self.holdings.get(market.base, 0.0) + order.qty
            self._seq += 1
            fill = Fill(order.client_id, "paper-%d" % self._seq, product, order.side,
                        order.qty, order.price, fee, time.time())
            self.fills.append(fill)
            out.append(fill)
        if out:
            self._persist()
        return out

    def equity(self, prices=None):
        """Cash plus holdings marked at `prices` (or the live ticker)."""
        total = self.cash
        for base, qty in self.holdings.items():
            if not qty:
                continue
            product = "%s-USD" % base
            try:
                price = (prices or {}).get(product) or self.ticker(product)
            except BrokerError:
                continue
            total += qty * price
        return total


# ---------------------------------------------------------------- shadow
class ShadowBroker(Broker):
    """
    Reads from a real venue, sends nothing.

    Wraps a live broker: balances, tickers and market rules are the venue's real
    answers, but `market_order` and `stop_order` only record what *would* have
    been sent. This is the forward-run stage — it tells you whether your sizing,
    your increments and your funds survive contact with the real account, before
    a single order exists.

    Ledger accounting still happens against the recorded intent, so a shadow run
    produces a full blotter you can compare against a backtest of the same window.
    """

    name = "shadow"
    live = False

    def __init__(self, inner, fee_pct=0.10, slippage_pct=0.05):
        self.inner = inner
        self.name = "shadow:" + inner.name
        self.intents = []
        self.fee_pct = fee_pct
        self.slippage_pct = slippage_pct
        self._seq = 0
        self._seen = {}

    def _fetch_market(self, product):
        return self.inner.market(product)

    def ticker(self, product):
        return self.inner.ticker(product)

    def balances(self):
        return self.inner.balances()

    def open_orders(self, product=None):
        return self.inner.open_orders(product)

    def market_order(self, product, side, qty, cid):
        if cid in self._seen:
            return self._seen[cid]
        # Same cost model as paper and the backtester, rather than a number of its
        # own: a shadow blotter is only useful if it can be compared against them.
        raw = self.ticker(product)
        slip = self.slippage_pct / 100.0
        price = raw * (1 + slip) if side == BUY else raw * (1 - slip)
        self._seq += 1
        fill = Fill(cid, "shadow-%d" % self._seq, product, side, qty, price,
                    price * qty * self.fee_pct / 100.0, time.time())
        self.intents.append(("market", product, side, qty, price))
        self._seen[cid] = fill
        return fill

    def stop_order(self, product, side, qty, stop_price, cid):
        if cid in self._seen:
            return self._seen[cid]
        self._seq += 1
        order = Order(cid, "shadow-%d" % self._seq, product, side, "stop", qty,
                      stop_price, "open")
        self.intents.append(("stop", product, side, qty, stop_price))
        self._seen[cid] = order
        return order

    def cancel(self, venue_id, product=None):
        self.intents.append(("cancel", product, None, None, venue_id))
