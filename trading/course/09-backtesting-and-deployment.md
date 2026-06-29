# 09 — Backtesting & Deployment

A strategy you haven't tested is a *belief*, not an edge. This module is the
bridge between "interesting idea" and "thing I'd risk money on". Rushing it is
the most expensive mistake beginners make.

## Stage 0 — Compile

In **MetaEditor**, open `JarvisMacroEA.mq5` and press **F7**. Fix nothing — it
should compile with **0 errors**. (Warnings about unused parameters are fine.)

## Stage 1 — Backtest (Strategy Tester, `Ctrl+R`)

Settings that matter:

- **Modelling:** *Every tick based on real ticks* (the most realistic). Avoid
  "Open prices only" for a model that reads intrabar sweeps.
- **Symbol:** start with one liquid market (EURUSD, GBPUSD, or XAUUSD).
- **Period:** the **entry timeframe** (M15 by default).
- **Date range:** at least **2–3 years**, ideally spanning different regimes
  (trending *and* ranging, a crisis if possible).
- **Deposit & leverage:** realistic for your real account.
- **Spread:** use *Current* or a realistic fixed value — **not** the broker's
  rosy minimum.

Run it, then read the report critically.

### What "good" looks like (and what's a mirage)

| Metric | Look for | Beware |
|---|---|---|
| **Profit factor** | > 1.3 over many trades | > 3 on few trades = curve-fit |
| **Number of trades** | ≥ 200 for significance | < 50 means nothing |
| **Max drawdown** | one you could *actually* sit through | "only 5%" on 30 trades is luck |
| **Expectancy** | positive and stable | great year + terrible year averaging out |
| **Equity curve** | steady, gentle slope | a few giant trades carrying it all |

> **Costs are real.** Make sure the test includes spread and, ideally, commission
> and a slippage assumption. A strategy that only works at zero cost doesn't work.

## Stage 2 — Optimise *gently* (and distrust the results)

The Strategy Tester can optimise inputs, but optimisation is where dreams go to
die. The danger is **curve-fitting**: tuning the EA to the *past* until it's
perfect on history and useless on the future.

Rules to stay honest:

- **Optimise few inputs** (1–3), over **sensible ranges**, looking for a **broad
  plateau** of decent results — not a single razor-sharp peak. A peak surrounded
  by losses is an accident you can't repeat.
- **Walk-forward / out-of-sample.** Optimise on 2021–2023, then test the chosen
  settings, **untouched**, on 2024–2025. Only out-of-sample performance counts.
- **Prefer robust settings.** A slightly worse setting that works across many
  symbols and periods beats a "perfect" one that works on exactly one.

If a parameter has to be *exactly* 47 to be profitable, it's noise. Throw it out.

## Stage 3 — Forward-test on demo (do not skip)

Run the EA on a **demo account, in real time, for weeks** (ideally 1–3 months).
This catches what backtests can't: real spread behaviour, slippage, broker fills,
weekend gaps, and your own reactions. Confirm:

- Live trades match what the backtest led you to expect.
- **Sessions are correct in your broker's server time** (the #1 live surprise).
- Lot sizing produces the risk % you intended on a real symbol.

If demo results diverge wildly from the backtest, find out *why* before going
further. Usually it's spread, session offset, or "open prices only" backtesting
hiding intrabar reality.

## Stage 4 — Go live, tiny

Only after a clean forward test, and only with money you can afford to lose:

1. Start at **0.25% risk or less**, regardless of what backtests suggested.
2. **One symbol.** Add others only once the first is boringly consistent.
3. Keep the **daily loss limit** and ability to flatten for news (module 06).
4. **Journal every live trade** (module 07) and compare to the demo.
5. Scale risk up *slowly* (e.g. toward 0.5%) only after a meaningful, profitable,
   rule-adherent live sample — not after one good week.

## A reality check

Most automated strategies that look brilliant in a backtest **underperform
live**. That's normal, not failure. The professional's edge isn't a magic EA — it
is the *discipline of this exact process*: test honestly, deploy small, journal,
and only scale what has genuinely proven itself. The traders this course is named
after all shared one trait — they protected their capital while they waited to be
sure. Do the same.

➡️ Next: [10 — Your trading plan (template)](10-trading-plan-template.md)
