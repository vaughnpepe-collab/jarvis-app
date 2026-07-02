"""Paper portfolio: positions, risk limits, settlement, stats.

State lives in a JSON file (default polymarket_data/portfolio.json,
gitignored). Every trade is simulated — no real money moves.
"""

import json
import os
from datetime import datetime, timezone

from . import api

DEFAULT_PATH = os.path.join("polymarket_data", "portfolio.json")


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class RiskLimits:
    def __init__(
        self,
        max_position_pct=0.05,   # of bankroll per market
        max_exposure_pct=0.50,   # of bankroll across all open positions
        max_price=0.99,          # never pay more than this per share
    ):
        self.max_position_pct = max_position_pct
        self.max_exposure_pct = max_exposure_pct
        self.max_price = max_price


class Portfolio:
    def __init__(self, path=DEFAULT_PATH, starting_cash=1000.0):
        self.path = path
        if os.path.exists(path):
            with open(path, encoding="utf-8") as fh:
                self.state = json.load(fh)
        else:
            self.state = {
                "cash": starting_cash,
                "starting_cash": starting_cash,
                "positions": [],   # open
                "history": [],     # settled
            }

    def save(self):
        os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
        with open(self.path, "w", encoding="utf-8") as fh:
            json.dump(self.state, fh, indent=2)

    @property
    def cash(self):
        return self.state["cash"]

    @property
    def exposure(self):
        return sum(p["cost"] for p in self.state["positions"])

    @property
    def bankroll(self):
        return self.cash + self.exposure

    def holds(self, market_id):
        return any(p["market_id"] == market_id for p in self.state["positions"])

    def stake_for(self, candidate, limits):
        """Largest stake allowed by the risk limits; 0 if the trade is barred."""
        if candidate.price > limits.max_price or self.holds(candidate.market.id):
            return 0.0
        room = self.bankroll * limits.max_exposure_pct - self.exposure
        stake = min(self.bankroll * limits.max_position_pct, room, self.cash)
        return max(stake, 0.0)

    def buy(self, candidate, stake):
        shares = stake / candidate.price
        self.state["cash"] -= stake
        self.state["positions"].append({
            "market_id": candidate.market.id,
            "question": candidate.market.question,
            "outcome": candidate.outcome,
            "outcome_index": candidate.outcome_index,
            "price": round(candidate.price, 4),
            "shares": round(shares, 4),
            "cost": round(stake, 2),
            "opened": _now(),
            "end_date": candidate.market.end_date,
        })

    def settle(self):
        """Check open positions against resolutions; realize wins/losses."""
        still_open, settled = [], []
        for pos in self.state["positions"]:
            try:
                market = api.market_by_id(pos["market_id"])
            except RuntimeError:
                still_open.append(pos)
                continue
            price = (
                market.prices[pos["outcome_index"]]
                if len(market.prices) > pos["outcome_index"]
                else None
            )
            # A closed market's outcome prices collapse to 1 and 0.
            if not market.closed or price is None or 0.01 < price < 0.99:
                still_open.append(pos)
                continue
            won = price >= 0.99
            payout = pos["shares"] if won else 0.0
            self.state["cash"] += payout
            pos.update({
                "won": won,
                "payout": round(payout, 2),
                "pnl": round(payout - pos["cost"], 2),
                "settled": _now(),
            })
            self.state["history"].append(pos)
            settled.append(pos)
        self.state["positions"] = still_open
        return settled

    def stats(self):
        history = self.state["history"]
        wins = sum(1 for p in history if p["won"])
        pnl = sum(p["pnl"] for p in history)
        return {
            "cash": round(self.cash, 2),
            "exposure": round(self.exposure, 2),
            "bankroll": round(self.bankroll, 2),
            "open_positions": len(self.state["positions"]),
            "settled": len(history),
            "wins": wins,
            "losses": len(history) - wins,
            "win_rate": round(wins / len(history), 4) if history else None,
            "realized_pnl": round(pnl, 2),
            "return_pct": round(
                100 * (self.bankroll / self.state["starting_cash"] - 1), 2
            ),
        }
