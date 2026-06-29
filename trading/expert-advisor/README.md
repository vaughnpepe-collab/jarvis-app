# JarvisMacroEA — MetaTrader 5 Expert Advisor

An automated implementation of **The Macro-Structure Method** taught in
[`../course/`](../course/). It trades a single, repeatable model:

> **Macro bias → liquidity sweep → structure shift → asymmetric trade.**

It is a *teaching template*, deliberately readable rather than over-optimised.
Treat every default as a starting point to be backtested, not a holy grail.

> ⚠️ **Risk warning.** Trading leveraged FX/CFDs can lose you more than your
> deposit. Nothing here is financial advice. **Demo-test first.** See
> [`../course/00-disclaimer-and-how-to-use.md`](../course/00-disclaimer-and-how-to-use.md).

---

## What it actually does

On each closed bar of the **entry timeframe** (default M15) it checks, in order:

1. **Macro bias** (default H4 + 50-EMA) — is the market above a rising EMA
   (longs only) or below a falling EMA (shorts only)? *No bias, no trade.*
   *(Druckenmiller / Soros: only swim with the macro tide.)*
2. **Liquidity sweep** — did a recent bar spike beyond a swing low/high and
   **close back through it**? That is the stop-hunt that traps the crowd.
   *(TJR / ICT: price reaches for liquidity before it reverses.)*
3. **Structure shift** — did price then **break the opposing swing** (break of
   structure / change of character) to confirm the reversal?
4. **Asymmetric trade** — stop just beyond the sweep; target the next liquidity
   pool; the trade is only taken if reward:risk ≥ `InpMinRR` (default **3:1**).
   *(Soros/Druckenmiller: it's not how often you're right, it's how big you win
   when you are vs. how small you lose when you're not.)*

Position size is computed from **% of equity at risk** and the stop distance, so
every trade risks the same fraction of the account regardless of stop width.
*(Lipschutz/Krieger: survive first, then size up with conviction.)* In a prime
session an A+ setup is sized up by `InpConvictionMult`, hard-capped at
`InpMaxRiskPct`.

Open trades are moved to break-even at +1R and trailed by ATR to ride trends.

---

## Install

1. Open **MetaTrader 5** → `File ▸ Open Data Folder`.
2. Copy `JarvisMacroEA.mq5` into `MQL5/Experts/`.
3. In **MetaEditor** press **F7** (Compile). It should compile with 0 errors.
4. In MT5, open a chart for your symbol, set it to your **entry timeframe**, and
   drag the EA from the *Navigator* onto the chart.
5. Tick **Allow Algo Trading** (and the global *Algo Trading* toolbar button).

## Recommended first steps (do not skip)

1. **Strategy Tester** (`Ctrl+R`): model *Every tick based on real ticks*, a
   liquid symbol (EURUSD/GBPUSD/XAUUSD), at least 2–3 years of data.
2. Start with **`InpRiskPercent = 0.25`** while you learn its behaviour.
3. Optimise *gently* — a couple of inputs at a time — then **forward-test on a
   demo account for weeks** before considering anything live.

---

## Key inputs

| Input | Default | Meaning |
|---|---|---|
| `InpBiasTF` / `InpBiasEMA` | H4 / 50 | Higher timeframe & EMA defining the macro tide |
| `InpRequireSlope` | true | Require the EMA to slope with the trade |
| `InpEntryTF` | M15 | Timeframe the EA executes on |
| `InpSwingLookback` / `InpFractalWing` | 25 / 2 | How swing highs/lows (liquidity) are detected |
| `InpSweepWindow` | 3 | Recent bars in which the sweep must occur |
| `InpRiskPercent` | 0.5 | Base risk per trade (% equity) |
| `InpConvictionMult` | 2.0 | Risk multiplier on A+ session setups |
| `InpMaxRiskPct` | 2.0 | Hard cap on risk per trade |
| `InpMinRR` | 3.0 | Minimum reward:risk to take a trade |
| `InpSLBufferATR` / `InpATRPeriod` | 0.5 / 14 | Stop buffer beyond the sweep, in ATR |
| `InpMoveToBE` / `InpTrailAfter1R` / `InpTrailATR` | on / on / 1.5 | Trade management |
| `InpUseSessions` + session hours | on, 7–11 & 13–17 | **Server-time** London/NY windows |
| `InpMaxSpreadPts` | 30 | Skip when spread is too wide |
| `InpMagic` | 920628 | Identifies this EA's trades |

> **Session hours are in your broker's server time, not your local time.**
> Check the clock in the MT5 *Market Watch* and adjust the four session inputs
> so they line up with the real London (≈08:00 UK) and New York (≈08:00 ET)
> opens. Getting this wrong is the most common reason the EA "does nothing".

---

## How the code maps to the method

| Course concept | Function in `JarvisMacroEA.mq5` |
|---|---|
| Macro bias | `MacroBias()` |
| Liquidity pools (swing highs/lows) | `FindRecentSwingHigh/Low()` |
| Sweep + structure shift | `TryLong()` / `TryShort()` |
| Asymmetric targets | `NextLiquidityAbove/Below()` + `InpMinRR` |
| Risk-based sizing | `LotsForRisk()` |
| Conviction sizing | `ConvictionMultiplier()` |
| Break-even & trailing | `ManageOpenPositions()` |
| Session/spread discipline | `IsTradingAllowed()` / `InMainSession()` |

Read [`../course/08-how-the-ea-works.md`](../course/08-how-the-ea-works.md) for
the line-by-line walkthrough.

## Known limitations (by design)

- It is a **single model**; the legends were discretionary. Use it as a
  disciplined assistant, not an oracle.
- No news filter — avoid running it blindly through high-impact releases.
- Swing/sweep detection is intentionally simple so you can read and modify it.
- One symbol per chart instance.
