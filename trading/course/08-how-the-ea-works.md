# 08 — How the Expert Advisor Works

This module connects the method to the code in
[`../expert-advisor/JarvisMacroEA.mq5`](../expert-advisor/JarvisMacroEA.mq5).
You don't need to be a programmer to trade it, but understanding it builds the
trust required to follow it — and lets you customise it (the real goal).

## The lifecycle

```
OnInit()  ─ create the H4-EMA and ATR indicator handles, set the magic number.
OnTick()  ─ runs on every price tick:
              1. ManageOpenPositions()   ← break-even & trailing, every tick
              2. is this a NEW entry-TF bar? if not, stop here
              3. IsTradingAllowed()?      ← session + spread + algo permission
              4. already at max positions? stop
              5. bias = MacroBias()       ← +1 / −1 / 0
              6. TryLong() or TryShort()  ← the module-04 checklist
OnDeinit()─ release indicator handles.
```

**Decisions are made once per closed bar; management happens every tick.** This
avoids acting on an unfinished candle (a classic backtest-vs-live trap) while
still trailing stops smoothly.

## Function-by-function

### `MacroBias()` — module 02

Reads the H4 50-EMA and the last closed H4 close. Returns **+1** if close is above
a *rising* EMA, **−1** if below a *falling* EMA, **0** otherwise. The slope check
is toggled by `InpRequireSlope`. This is the gate: bias `0` means no trade.

### `FindRecentSwingHigh()` / `FindRecentSwingLow()` — module 03

Scan back up to `InpSwingLookback` bars for a fractal swing: a bar whose
high (low) is the highest (lowest) within `InpFractalWing` bars on each side.
Returns the price and bar index of the most recent one — your liquidity pools.

### `TryLong()` (and mirror `TryShort()`) — the module-04 checklist

1. Find the recent swing low (sell-side liquidity).
2. **Sweep test:** within the last `InpSweepWindow` bars, did a bar's low go
   *below* that swing low and *close back above* it? Track the sweep extreme.
3. Find the recent swing high; **structure-shift test:** did the last closed bar
   close *above* it (break of structure)?
4. Compute ATR, set entry (Ask), stop = sweep low − `InpSLBufferATR`×ATR.
5. Target = next liquidity pool above (`NextLiquidityAbove()`); if that's < min
   R:R away, fall back to `InpMinRR` × risk.
6. Apply the conviction multiplier and call `OpenTrade()`.

If any test fails, the function simply returns — no trade. Discipline = the early
`return`.

### `LotsForRisk()` — module 05 (the most important function)

```
risk money   = equity × risk%
loss per lot = (stop distance ÷ tick size) × tick value
lots         = risk money ÷ loss per lot   → snapped to the broker's volume step
```

Position size is *derived from the stop*, so every trade risks the chosen % of
equity regardless of stop width. Then it's clamped to the symbol's
min/max/step volume.

### `ConvictionMultiplier()` + the clamp in `OpenTrade()` — module 05

Returns a risk multiplier (default 2× on prime-session setups). `OpenTrade()`
then does `MathMin(InpRiskPercent × mult, InpMaxRiskPct)` so conviction can scale
risk **only up to the hard cap**. This is where you'd add your own tiers (e.g.
"H4 *and* Daily agree → 1.5×").

### `ManageOpenPositions()` — module 06

Every tick, for each of *this EA's* positions (matched by magic number & symbol):
compute the current R-multiple; at ≥ +1R move the stop to break-even
(`InpMoveToBE`) and/or trail by `InpTrailATR`×ATR (`InpTrailAfter1R`). It only
ever tightens the stop, never loosens it.

### `IsTradingAllowed()` / `InMainSession()` — modules 04 & 07

Blocks new trades unless algo trading is permitted, the spread is below
`InpMaxSpreadPts`, and (if `InpUseSessions`) the **server-time** hour falls inside
a London or New York window. **Set these to your broker's server time** — see the
EA README.

## What it deliberately does *not* do

- **No fundamental bias.** That's your job (module 02). Use `InpAllowLongs` /
  `InpAllowShorts` to enforce your macro view.
- **No news filter.** Don't let it run blind through FOMC/NFP/CPI.
- **No FVG/order-block entry** in the base version — a suggested extension
  (module 04).
- **No pyramiding or scale-outs** — suggested extensions (module 06).

These omissions are intentional: the EA is small enough to **read in full and
modify**. That is the point. Make it yours, then test the changes (module 09).

## Safe ways to customise

Start with **inputs** (no coding): timeframes, EMA period, swing lookback, R:R,
risk %, sessions. Then graduate to **code**: add conviction tiers in
`ConvictionMultiplier()`, a scale-out in `ManageOpenPositions()`, or an FVG entry
in `TryLong()`. Change **one thing at a time** and backtest each change so you
know what each lever actually does.

➡️ Next: [09 — Backtesting & deployment](09-backtesting-and-deployment.md)
