# 03 — Market Structure & Liquidity

This is the TJR / smart-money engine room. Bias (module 02) tells you *which
direction*; structure and liquidity tell you *where and when* to pull the
trigger. Master these four ideas and the entry model in module 04 becomes
obvious.

## 1. Swing points = pools of liquidity

A **swing high** is a candle whose high is higher than the candles on either side
of it. A **swing low** is the mirror. They matter because of *where stops sit*:

- Below an obvious swing **low** rest the stop-losses of longs and the sell-stop
  entries of breakout sellers → a pool of **sell-side liquidity**.
- Above an obvious swing **high** rest the stops of shorts and buy-stop breakout
  buyers → a pool of **buy-side liquidity**.

Large players need to fill big orders. To buy a lot, they need a lot of sellers —
which is exactly what triggers when price dips below a swing low. So price is
*drawn* to obvious highs and lows. Think of swing points as magnets.

> In the EA, `FindRecentSwingHigh()` / `FindRecentSwingLow()` detect these using
> a simple fractal: the highest/lowest bar within `InpFractalWing` bars on each
> side.

## 2. The liquidity sweep (a.k.a. stop hunt / liquidity grab)

A **sweep** is when price spikes *beyond* a swing point — grabbing the liquidity
resting there — and then **closes back on the original side**. The wick pokes
through; the body rejects.

```
        ┌── swing high (buy-side liquidity)
        │        ╱╲   ← wick sweeps above the high...
   ─────┴───────╱──╲────────────
                    ╲  ← ...then closes back below it (sweep complete)
```

A sweep traps the breakout crowd: buyers who chased the break above the high are
now offside, and their stops below become *fuel* for the move down. This is the
"trap" Soros and the macro guys exploited at the fundamental level — TJR's
contribution is recognising it as a **mechanical, repeatable candlestick event**.

> In the EA, `TryLong()` / `TryShort()` check whether, within the last
> `InpSweepWindow` bars, a bar's low went **below** a swing low (or high above a
> swing high) and **closed back through** it.

## 3. Market structure shift (Break of Structure / Change of Character)

A sweep alone isn't enough — price pokes highs and lows constantly. We need
**confirmation** that the order flow has actually turned. That confirmation is a
**break of structure (BOS)** / **change of character (CHoCH)**:

- After sweeping a swing **low** (in an up-bias), price then **closes above the
  most recent swing high**. The down-move failed and buyers are now in control —
  a change of character to the upside.
- After sweeping a swing **high** (in a down-bias), price **closes below the
  recent swing low**.

Sweep = *the trap is set*. Structure shift = *the trapdoor opens*. You want both.

> In the EA, after confirming the sweep, `TryLong()` requires the **last closed
> bar to close above the recent swing high** (and `TryShort()` the mirror) before
> it will trade.

## 4. Fair value gaps & order blocks (refinements)

Two optional refinements from the same school, useful for *where* to enter:

- **Fair Value Gap (FVG):** a three-candle imbalance where price moved so fast it
  left a gap (candle 1's wick and candle 3's wick don't overlap). Price often
  retraces to "fill" the gap before continuing — a precise entry zone.
- **Order block:** the last opposing candle before an explosive move. Price often
  returns to it before continuing.

The base EA keeps things simple and enters on the structure shift itself rather
than waiting for a retrace into an FVG/order block. Module 04 explains how you
could extend it to use these for tighter stops — a great first customisation
project.

## Putting the picture together

A textbook long, *in an up-bias*:

```
1. H4 bias = UP (module 02)                    → we only look for longs
2. Price sweeps a recent swing low (grabs SSL) → the crowd's stops are hit
3. Price closes back above that low            → rejection
4. Price closes above the recent swing high    → break of structure (CHoCH)
5. → ENTER long; stop below the sweep; target the next swing high (BSL)
```

Every concept above exists to make step 5 a **high-probability, asymmetric**
trade — small risk to the sweep, large reward to the next liquidity pool.

➡️ Next: [04 — The entry model](04-the-entry-model.md)
