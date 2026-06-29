# 04 — The Entry Model

Everything so far converges here into one checklist. This is the exact model the
EA automates. If a setup fails **any** line, there is no trade — discipline lives
in the word *no*.

## The long checklist (mirror everything for shorts)

| # | Condition | Why | EA mechanism |
|---|---|---|---|
| 1 | **H4 bias is UP** (price > rising 50-EMA) | Trade with the tide | `MacroBias()` |
| 2 | **Active session** (London or NY) | Real liquidity, real moves | `InMainSession()` |
| 3 | **Spread acceptable** | Don't pay the edge away | `IsTradingAllowed()` |
| 4 | **Liquidity sweep**: a recent bar dipped below a swing low and closed back above it | The crowd is trapped | sweep loop in `TryLong()` |
| 5 | **Structure shift**: last closed bar closed **above** the recent swing high | Order flow confirmed up | BOS check in `TryLong()` |
| 6 | **Reward:Risk ≥ 3:1** to the next liquidity pool | Asymmetry (Druckenmiller) | `InpMinRR` |
| 7 | **Stop hides beyond the sweep** (+ ATR buffer) | Invalidation point | `InpSLBufferATR` |

Only when **all seven** are true does the EA fire.

## Anatomy of the trade

```
                                    ┌─ TP: next swing high (buy-side liquidity)
                                    │   reward = 3R+
        recent swing high ───────┐  │
                          ╱╲     │  │   ← (5) close ABOVE swing high = BOS → ENTRY
   ──────────────────────╱──╲────┼──┼────────────────────
              ╲         ╱     ╲  │  │
   swing low ──╲───────╱        ╲│  │
                ╲╱ (4) sweep & reclaim
                 │
                 └─ SL: just below the sweep low − ATR buffer   risk = 1R
```

- **Entry:** market order on the close that confirms the structure shift.
- **Stop:** below the *sweep* extreme (the lowest point of the grab) minus a small
  ATR buffer, so normal noise doesn't clip you but a *real* failure does.
- **Target:** the next opposing liquidity pool (the next swing high). If that pool
  isn't far enough away to give 3R, the EA falls back to a fixed `InpMinRR`
  multiple of the risk. *Never* take a trade that can't pay at least 3:1.

## Why this is asymmetric (the whole point)

Your risk is the *narrow* distance from entry to just beyond the sweep — and the
sweep is, by definition, an extreme the market just rejected. Your reward is the
*wide* distance to the next liquidity pool the market is being drawn toward. You
are routinely risking 1 to make 3+. With a payoff like that you can be **wrong
more often than right and still grind upward**:

| Win rate | Avg R:R | Expectancy per trade |
|---|---|---|
| 40% | 3:1 | **+0.6R** |
| 35% | 3:1 | **+0.4R** |
| 50% | 3:1 | **+1.0R** |

This is Druckenmiller's lesson made concrete: it isn't the win rate, it's the
size of the wins vs. the losses.

## Variations you can test (good first projects)

1. **FVG entry (tighter stop).** Instead of entering on the BOS close, wait for a
   retrace into the fair value gap left by the structure-shift move and enter
   there. Tighter risk → higher R:R, fewer fills.
2. **Order-block stop.** Place the stop below the order block instead of the
   sweep for a different invalidation.
3. **Two-target scale-out.** Take half at 2R, trail the rest (Lipschutz-style
   trading *around* a core). Covered in module 06.
4. **Bias strength tiers.** Size larger when H4 *and* Daily agree (module 05's
   conviction logic).

## The discipline rule

The model will *not* trigger often — maybe a handful of times a week per symbol
in the right sessions. **That is correct.** The legends traded rarely and waited
for the pitch they wanted. If you find yourself forcing setups that miss a line
on the checklist, you have stopped trading the method and started gambling.

➡️ Next: [05 — Risk & position sizing](05-risk-and-position-sizing.md)
