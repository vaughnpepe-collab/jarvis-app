# The Macro-Structure Method

A trading course **and** a working MetaTrader 5 Expert Advisor, distilled from
the edges of five very different market operators:

- **George Soros** — reflexivity, asymmetric macro bets, "go for the jugular".
- **Stanley Druckenmiller** — top-down macro, concentration, capital preservation.
- **Bill Lipschutz** — FX, conviction, trading *around* a core, position sizing.
- **Andrew Krieger** — disciplined aggression and leverage on high-conviction trades.
- **TJR (modern ICT / smart-money style)** — liquidity sweeps, market structure,
  session timing, mechanical entries.

None of them traded the same way. What they *share* is the spine of this course:
**find the dominant tide, wait for the crowd to be trapped, enter with a tiny
risk and an enormous potential reward, and manage the winners ruthlessly.**

> ⚠️ **This is education, not financial advice.** Trading leveraged products can
> lose you more than you deposit. Everything here is for learning and should be
> tested on a **demo account**. Read
> [`course/00-disclaimer-and-how-to-use.md`](course/00-disclaimer-and-how-to-use.md)
> before anything else.

## Contents

| # | Module |
|---|---|
| 00 | [Disclaimer & how to use this course](course/00-disclaimer-and-how-to-use.md) |
| 01 | [The mindset of legends](course/01-mindset-of-legends.md) |
| 02 | [Top-down macro bias](course/02-macro-bias.md) |
| 03 | [Market structure & liquidity](course/03-market-structure-and-liquidity.md) |
| 04 | [The entry model](course/04-the-entry-model.md) |
| 05 | [Risk & position sizing](course/05-risk-and-position-sizing.md) |
| 06 | [Trade management](course/06-trade-management.md) |
| 07 | [Psychology & journaling](course/07-psychology-and-journaling.md) |
| 08 | [How the Expert Advisor works](course/08-how-the-ea-works.md) |
| 09 | [Backtesting & deployment](course/09-backtesting-and-deployment.md) |
| 10 | [Your trading plan (template)](course/10-trading-plan-template.md) |

## The Expert Advisor

- Code: [`expert-advisor/JarvisMacroEA.mq5`](expert-advisor/JarvisMacroEA.mq5)
- Install & inputs: [`expert-advisor/README.md`](expert-advisor/README.md)

## The one-paragraph summary

Read the macro tide on a high timeframe and only trade with it. Wait on a lower
timeframe for price to **sweep liquidity** (spike past an obvious high/low and
snap back, trapping the crowd), then **shift structure** in your direction. Risk
a tiny, fixed fraction of your account with your stop hidden beyond the sweep,
and aim for at least 3× that risk by targeting the next pool of liquidity. Lose
small and often; win big occasionally; press hard only when everything lines up.
