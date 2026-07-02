"""CLI for the Polymarket paper-trading bot.

    python -m polymarket_bot scan            # rank high-probability candidates
    python -m polymarket_bot arb             # look for YES+NO < $1 arbitrage
    python -m polymarket_bot auto            # scan + paper-buy within risk limits
    python -m polymarket_bot settle          # realize resolved positions
    python -m polymarket_bot portfolio       # positions, win rate, P&L

All trades are simulated. No wallet, no keys, no real money.
"""

import argparse

from .portfolio import Portfolio, RiskLimits, DEFAULT_PATH
from .strategy import ArbitrageScanner, HighProbabilityStrategy


def _fmt_candidate(c, index):
    ann = f"{c.annualized * 100:6.1f}%/yr" if c.annualized else "      n/a"
    return (
        f"{index:>2}. ${c.price:.3f}  edge {c.edge * 100:4.1f}%  {ann}  "
        f"{c.days_left:4.1f}d  [{c.outcome}] {c.market.question[:70]}"
    )


def cmd_scan(args):
    strategy = HighProbabilityStrategy(
        min_price=args.min_price, max_price=args.max_price, max_days=args.max_days
    )
    candidates = strategy.scan()
    if not candidates:
        print("No candidates matched the filters right now.")
        return
    print(f"{len(candidates)} high-probability candidates "
          f"(${args.min_price:.2f}-${args.max_price:.2f}, <{args.max_days}d):\n")
    for i, c in enumerate(candidates[: args.top], 1):
        print(_fmt_candidate(c, i))
        print(f"    {c.market.url()}")


def cmd_arb(args):
    hits = ArbitrageScanner().scan()
    if not hits:
        print("No arbitrage found (normal — real arbs vanish in seconds).")
        return
    for market, yes_ask, no_ask, profit, size in hits:
        print(f"{profit * 100:.2f}% locked  "
              f"({market.outcomes[0]} ${yes_ask:.3f} + "
              f"{market.outcomes[1]} ${no_ask:.3f}, ~{size:.0f} shares)  "
              f"{market.question[:60]}")


def cmd_auto(args):
    portfolio = Portfolio(args.state, starting_cash=args.bankroll)
    limits = RiskLimits(
        max_position_pct=args.max_position, max_exposure_pct=args.max_exposure
    )
    strategy = HighProbabilityStrategy(
        min_price=args.min_price, max_price=args.max_price, max_days=args.max_days
    )
    placed = 0
    for candidate in strategy.scan():
        stake = portfolio.stake_for(candidate, limits)
        if stake < 1.0:
            continue
        portfolio.buy(candidate, stake)
        placed += 1
        print(f"PAPER BUY ${stake:7.2f} of [{candidate.outcome}] at "
              f"${candidate.price:.3f} — {candidate.market.question[:60]}")
        if placed >= args.max_trades:
            break
    portfolio.save()
    if placed == 0:
        print("No trades placed (no candidates, or risk limits are binding).")
    print(f"\nCash ${portfolio.cash:.2f}  exposure ${portfolio.exposure:.2f}  "
          f"open positions {len(portfolio.state['positions'])}")


def cmd_settle(args):
    portfolio = Portfolio(args.state)
    settled = portfolio.settle()
    portfolio.save()
    for pos in settled:
        tag = "WIN " if pos["won"] else "LOSS"
        print(f"{tag} {pos['pnl']:+8.2f}  [{pos['outcome']}] "
              f"{pos['question'][:60]}")
    if not settled:
        print("Nothing resolved yet.")
    _print_stats(portfolio)


def cmd_portfolio(args):
    portfolio = Portfolio(args.state)
    for pos in portfolio.state["positions"]:
        print(f"open  ${pos['cost']:7.2f} at ${pos['price']:.3f}  "
              f"[{pos['outcome']}] {pos['question'][:60]}")
    _print_stats(portfolio)


def _print_stats(portfolio):
    s = portfolio.stats()
    win_rate = f"{s['win_rate'] * 100:.1f}%" if s["win_rate"] is not None else "n/a"
    print(f"\nbankroll ${s['bankroll']:.2f} ({s['return_pct']:+.2f}%)  "
          f"cash ${s['cash']:.2f}  exposure ${s['exposure']:.2f}")
    print(f"settled {s['settled']} (W{s['wins']}/L{s['losses']}, "
          f"win rate {win_rate})  realized P&L ${s['realized_pnl']:+.2f}")


def main():
    parser = argparse.ArgumentParser(
        prog="polymarket_bot", description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--state", default=DEFAULT_PATH,
                        help="portfolio state file (default: %(default)s)")
    sub = parser.add_subparsers(dest="command", required=True)

    def add_filters(p):
        p.add_argument("--min-price", type=float, default=0.94)
        p.add_argument("--max-price", type=float, default=0.99)
        p.add_argument("--max-days", type=float, default=21)

    p_scan = sub.add_parser("scan", help="rank high-probability candidates")
    add_filters(p_scan)
    p_scan.add_argument("--top", type=int, default=15)
    p_scan.set_defaults(func=cmd_scan)

    p_arb = sub.add_parser("arb", help="scan for YES+NO < $1 arbitrage")
    p_arb.set_defaults(func=cmd_arb)

    p_auto = sub.add_parser("auto", help="scan and paper-buy within risk limits")
    add_filters(p_auto)
    p_auto.add_argument("--bankroll", type=float, default=1000.0,
                        help="starting paper cash for a new portfolio")
    p_auto.add_argument("--max-trades", type=int, default=5)
    p_auto.add_argument("--max-position", type=float, default=0.05,
                        help="max fraction of bankroll per market")
    p_auto.add_argument("--max-exposure", type=float, default=0.50,
                        help="max fraction of bankroll at risk overall")
    p_auto.set_defaults(func=cmd_auto)

    p_settle = sub.add_parser("settle", help="realize resolved positions")
    p_settle.set_defaults(func=cmd_settle)

    p_pf = sub.add_parser("portfolio", help="show positions and stats")
    p_pf.set_defaults(func=cmd_portfolio)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
