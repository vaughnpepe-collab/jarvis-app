# 02 — Top-Down Macro Bias

> *"The first thing I look at is the big picture."* — the entire macro school.

Before you ever look for an entry, you must answer one question: **which way is
the tide running?** Druckenmiller and Soros made their fortunes by being on the
right side of large, slow-moving currents and then doing nothing that fought
them. Everything in this method filters down from bias.

## Two layers of bias

### 1. Fundamental / macro bias (the *why*)

This is the Soros/Druckenmiller layer. For a currency, the dominant drivers are:

- **Relative interest rates & central-bank direction.** Money flows toward
  currencies whose central banks are hiking (or expected to) and away from those
  cutting. This is the single biggest FX driver.
- **Growth & inflation surprises** relative to expectations (reflexivity:
  surprises move belief, belief moves price).
- **Risk sentiment** — "risk-on" vs "risk-off" flows into havens (USD, JPY, CHF,
  gold) vs. higher-yielders.
- **Positioning & policy stress** — pegs, interventions, crowded trades. Soros's
  GBP short and Krieger's NZD short were both *policy-vs-reality* stories.

You don't need to be an economist. You need a **simple, defensible directional
thesis** you can state in one sentence, e.g.:

> "The Fed is on hold while the ECB is still cutting → I favour USD over EUR →
> my bias on EURUSD is **down**."

If you can't state it, you don't have a bias — you have a guess.

### 2. Technical bias (the *confirmation*)

The market is the final arbiter. Don't fight price even if you love the story.
We confirm bias mechanically so it can be automated:

- **Higher-timeframe trend.** On a high timeframe (the EA uses **H4**), is price
  **above a rising moving average** (bullish) or **below a falling one**
  (bearish)? The EA uses a **50-period EMA** and optionally requires the EMA to
  be sloping the right way.
- **Higher-timeframe structure.** Is the HTF making **higher highs & higher
  lows** (uptrend) or **lower highs & lower lows** (downtrend)? Structure is the
  subject of module 03.

When the fundamental story and the technical picture **agree**, you have a real
bias and you only hunt entries in that direction. When they conflict, **stand
aside** — that is itself a position (Druckenmiller was happy to hold cash).

## The bias workflow

1. **Weekly / Daily:** what is the macro story and the dominant trend? Write the
   one-sentence thesis.
2. **H4 (the EA's bias timeframe):** price vs. the 50-EMA, and HH/HL vs. LH/LL.
   This produces a single answer: **long-only**, **short-only**, or **no-trade**.
3. **Drop to the entry timeframe (M15)** *only* to look for setups in that one
   direction. You are never "looking for a trade"; you are looking for *your*
   trade.

## Why bias first matters so much

A mechanical entry trigger (module 04) will fire in both directions all day. Most
of those signals are noise. The bias filter is what turns a coin-flip pattern
into an *edge*: you only take the sweeps and structure shifts that are **aligned
with the larger move**, where the asymmetric reward actually lives. This is the
difference between "I trade liquidity grabs" and "I trade liquidity grabs **in
the direction of a strong H4 trend during the London/NY sessions**."

## How the EA encodes this

`MacroBias()` in `JarvisMacroEA.mq5`:

- Pulls the **H4 50-EMA** and the last closed H4 close.
- Returns **+1** (long-only) if close is above a rising EMA, **−1** (short-only)
  if below a falling EMA, **0** (stand aside) otherwise.
- `OnTick()` refuses to even look for entries when bias is `0`.

The fundamental layer can't be coded — *that's your job.* Use the EA's session
and direction inputs (`InpAllowLongs` / `InpAllowShorts`) to enforce your macro
view: if your thesis says "USD strength", you might disable EURUSD longs entirely
and let the EA only short rallies.

➡️ Next: [03 — Market structure & liquidity](03-market-structure-and-liquidity.md)
