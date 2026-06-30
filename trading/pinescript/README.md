# JarvisMacroStructure — TradingView (Pine v5)

A **chart companion** to the MT5 Expert Advisor. It marks the same setups the EA
trades — **macro bias + liquidity sweep + structure shift** — and draws the stop
and a 3R target so you can study the method visually on any TradingView chart.

> ⚠️ Educational only — **not financial advice**. This indicator *marks* setups;
> it does not place orders or size positions. See [`../course/`](../course/).

## Install

1. TradingView ▸ open any chart ▸ **Pine Editor** (bottom panel).
2. Paste the contents of [`JarvisMacroStructure.pine`](JarvisMacroStructure.pine).
3. **Add to chart.** Set the chart to your entry timeframe (e.g. M15).

## What you'll see

- **LONG / SHORT triangles** when bias + sweep + break-of-structure align.
- An **orange line** = the higher-timeframe bias EMA.
- **Grey circles** = the active swing highs/lows (liquidity pools).
- **SL / TP rays + labels** on each signal (TP at your `Min reward:risk`).
- A faint **background tint** showing the current macro bias (teal up / red down).

## Inputs (mirror the EA)

- **Bias:** timeframe, EMA length, require-slope.
- **Structure:** pivot left/right bars, sweep window.
- **Risk drawing:** min reward:risk, ATR length, stop buffer, show levels.
- **Direction:** enable longs / shorts (use to enforce your macro view).

## Set an alert

The script exposes two `alertcondition`s — **"Jarvis LONG setup"** and
**"Jarvis SHORT setup"**. Add an alert, pick the condition, and TradingView will
ping you when a setup forms so you don't have to watch the screen.

## Notes & honesty

- Signals confirm on the **bar close**; an in-progress bar can change. The pivot
  logic also lags by `pivot right` bars by design (that's how a swing is
  confirmed) — same as any pivot-based tool.
- This is a simplified read of the method (it targets a fixed R multiple rather
  than scanning for the next liquidity pool like the EA). Treat it as a study
  aid, not a signal service. Backtest your own rules before trading them.
