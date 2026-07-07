# Polymarket Trading Bot (paper trading)

A dependency-free Python bot that scans [Polymarket](https://polymarket.com)
for high-probability opportunities and manages a **simulated** portfolio.
It uses only Polymarket's public data APIs — no wallet, no keys, no real
money at risk.

## The honest truth about "100% win rate"

**No trading bot can guarantee a 100% win rate.** Anyone selling one is
running a scam. Prediction-market prices *are* probabilities: an outcome
priced at $0.97 loses roughly 3% of the time, and that 3% is exactly the
risk you're paid to take. The two strategies here are the closest honest
approximations:

1. **High-probability harvesting** (`scan` / `auto`) — buy outcomes the
   market prices at $0.94–$0.99 that resolve within ~3 weeks. Win rate is
   high *by construction* (~94–99% if prices are calibrated), and losses
   are capped by position sizing. A single loss wipes out many wins'
   profits, which is why the risk limits matter more than the picks.
2. **Arbitrage scanning** (`arb`) — find binary markets where the YES ask
   plus the NO ask is under $1.00. Buying both sides locks in profit no
   matter what happens. This *is* riskless in theory — and therefore
   nearly always already taken. Expect it to find nothing most runs.

## Usage

```bash
# Rank current high-probability candidates
python -m polymarket_bot scan

# Look for riskless YES+NO arbitrage
python -m polymarket_bot arb

# Paper-trade: scan and buy up to 5 positions within risk limits
python -m polymarket_bot auto --bankroll 1000

# Later: settle resolved markets and see your win rate / P&L
python -m polymarket_bot settle
python -m polymarket_bot portfolio
```

Portfolio state persists in `polymarket_data/portfolio.json` (gitignored).
Run `auto` every day or two and `settle` after, and the stats build up a
real track record you can judge before ever considering real money.

## Risk limits (defaults)

| Limit | Default | Flag |
|---|---|---|
| Per-market stake | 5% of bankroll | `--max-position` |
| Total open exposure | 50% of bankroll | `--max-exposure` |
| Price band | $0.94–$0.99 | `--min-price` / `--max-price` |
| Time to resolution | ≤ 21 days | `--max-days` |
| Market liquidity | ≥ $10k | (in `strategy.py`) |

One position per market, never buys above $0.99, and stops when the
exposure cap is hit.

## Going live (deliberately not implemented)

Real orders would require Polymarket's `py-clob-client`, a funded Polygon
wallet, and its private key in this environment. Before that ever makes
sense: run this paper bot for at least a month, check that the realized
win rate matches the entry prices, and understand that past calibration
does not guarantee future calibration. Also check your jurisdiction —
Polymarket is unavailable to US persons for real-money trading.
