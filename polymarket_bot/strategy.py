"""Trading strategies.

HighProbabilityStrategy — the closest honest thing to a "high win rate"
bot. It buys outcomes the market already prices as near-certain (e.g.
$0.94-$0.99) shortly before resolution. If Polymarket prices are well
calibrated, a $0.96 outcome wins ~96% of the time; the profit is the
small gap to $1.00, compounded across many quick-resolving positions.
The win rate is high by construction but can NEVER be 100% — the
losing 4% is exactly what you are being paid to underwrite.

ArbitrageScanner — flags binary markets where YES-ask + NO-ask < $1.00
after fees. Buying both sides locks in a profit regardless of outcome;
genuinely riskless, but rare and fleeting.
"""

from datetime import datetime, timedelta, timezone

from . import api


def _days_until(iso_date):
    if not iso_date:
        return None
    try:
        end = datetime.fromisoformat(iso_date.replace("Z", "+00:00"))
    except ValueError:
        return None
    return (end - datetime.now(timezone.utc)).total_seconds() / 86400


class Candidate:
    def __init__(self, market, outcome_index, price):
        self.market = market
        self.outcome_index = outcome_index
        self.outcome = market.outcomes[outcome_index]
        self.token_id = (
            market.token_ids[outcome_index]
            if len(market.token_ids) == 2
            else None
        )
        self.price = price
        self.days_left = _days_until(market.end_date)

    @property
    def edge(self):
        """Payout per dollar if the outcome wins: buy at .96 -> +4.17%."""
        return (1.0 - self.price) / self.price

    @property
    def annualized(self):
        if not self.days_left or self.days_left <= 0:
            return None
        return self.edge * (365 / self.days_left)


class HighProbabilityStrategy:
    def __init__(
        self,
        min_price=0.94,
        max_price=0.99,
        max_days=21,
        min_liquidity=10_000,
        min_volume_24h=500,
    ):
        self.min_price = min_price
        self.max_price = max_price
        self.max_days = max_days
        self.min_liquidity = min_liquidity
        self.min_volume_24h = min_volume_24h

    def scan(self, max_pages=10):
        """Return Candidates sorted by annualized return, best first."""
        cutoff = (
            datetime.now(timezone.utc) + timedelta(days=self.max_days)
        ).date().isoformat()
        found = []
        for market in api.open_markets(
            min_liquidity=self.min_liquidity,
            min_volume=self.min_volume_24h,
            max_end_date=cutoff,
            max_pages=max_pages,
        ):
            if market.neg_risk or market.volume_24h < self.min_volume_24h:
                continue
            days = _days_until(market.end_date)
            if days is None or days <= 0 or days > self.max_days:
                continue
            for i, price in enumerate(market.prices):
                if self.min_price <= price <= self.max_price:
                    found.append(Candidate(market, i, price))
        found.sort(key=lambda c: c.annualized or 0, reverse=True)
        return found


class ArbitrageScanner:
    """Find binary markets whose two best asks sum below $1.00."""

    def __init__(self, min_profit=0.005, min_liquidity=5_000):
        self.min_profit = min_profit
        self.min_liquidity = min_liquidity

    def scan(self, max_pages=5, max_book_lookups=40):
        hits = []
        looked = 0
        for market in api.open_markets(
            min_liquidity=self.min_liquidity, max_pages=max_pages
        ):
            if len(market.token_ids) != 2 or looked >= max_book_lookups:
                continue
            # Cheap pre-filter on Gamma mid prices before hitting the CLOB.
            if sum(market.prices) > 1.02:
                continue
            looked += 1
            asks = [api.best_ask(t) for t in market.token_ids]
            if any(a is None for a in asks):
                continue
            cost = asks[0][0] + asks[1][0]
            if cost < 1.0 - self.min_profit:
                size = min(asks[0][1], asks[1][1])
                hits.append((market, asks[0][0], asks[1][0], 1.0 - cost, size))
        hits.sort(key=lambda h: h[3], reverse=True)
        return hits
