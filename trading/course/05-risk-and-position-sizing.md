# 05 — Risk & Position Sizing

> *"Survive first. Make money second."*

This is the most important module in the course. **Entries are commodities;
risk management is the edge.** Lipschutz said position sizing was the single most
important part of his trading. Druckenmiller built a career on capital
preservation. Krieger's leverage only worked because his downside was defined.
If you internalise nothing else, internalise this.

## Rule 1 — Risk a fixed, small fraction of equity per trade

Decide *in money/percent terms*, **before** the trade, how much you will lose if
you're wrong. The EA uses **% of equity** (`InpRiskPercent`, default **0.5%**).

Why fixed-fractional:

- It makes every trade the **same emotional size**, so a wide stop and a tight
  stop hurt equally little. You stop caring about any single trade.
- It **compounds** on the way up and **de-risks** automatically on the way down
  (0.5% of a shrinking account is fewer dollars).
- It makes a losing streak survivable. At 0.5% risk, **ten losses in a row** is
  about a **5% drawdown** — annoying, not fatal. At 5% risk, the same streak is a
  ~40% drawdown that can end you psychologically and mathematically.

**Recommended starting point: 0.25%–0.5% per trade.** Beginners overestimate how
much volatility they can stomach. Start absurdly small.

## Rule 2 — Size is *derived* from the stop, never guessed

This is the mechanical heart of the method. You do **not** pick a lot size and
then a stop. You pick the **stop** (where the idea is wrong — beyond the sweep),
decide the **risk in money**, and let arithmetic give you the size:

```
risk money     = equity × risk%                       e.g. 10,000 × 0.5% = $50
stop distance  = |entry − stop|                        e.g. 25 pips
loss per lot   = stop distance × value-per-pip-per-lot
lot size       = risk money ÷ loss per lot
```

A wide stop → smaller position. A tight stop → larger position. **The dollar risk
is identical either way.** This is exactly what `LotsForRisk()` does in the EA,
using the broker's tick value/size and then snapping to the allowed volume step.

> Never trade a fixed lot size. A 0.10-lot trade with a 10-pip stop and a 0.10-lot
> trade with a 100-pip stop risk *ten times* different amounts. That's not a
> strategy, it's a random number generator.

## Rule 3 — Asymmetry: only take 3:1+ (recap from module 04)

Risk-per-trade controls the *downside*; the **minimum reward:risk** controls the
*upside*. The EA refuses trades below `InpMinRR` (default 3:1). Combined, these
two rules are the Druckenmiller equation: *small, equal losses; large wins.*

## Rule 4 — Press conviction, but cap it

Soros: "When you're right, you can't be right enough." Krieger pressed rare
opportunities. **But** they could afford it because the *base* size was
controlled and the downside defined. We encode that nuance:

- **Base risk** is small (0.5%).
- When an A+ setup appears in a prime session, the EA multiplies risk by
  `InpConvictionMult` (default 2×)…
- …but **hard-caps** total risk at `InpMaxRiskPct` (default 2%).

So conviction *scales* risk within a ceiling — it never removes the ceiling. You
"go for the jugular" with 1.5–2× normal size on your best setups, not with the
whole account. Build your own conviction tiers (e.g. H4-only vs. H4+Daily
agreement) and test whether the extra size actually improves your expectancy.

> `ConvictionMultiplier()` and the `MathMin(..., InpMaxRiskPct)` clamp in
> `OpenTrade()` implement this. Edit `ConvictionMultiplier()` to add your own
> alignment checks.

## Rule 5 — Portfolio & correlation limits (do this manually)

The per-trade rules don't see the *whole book*. Protect yourself with hard limits:

- **Max concurrent risk:** cap total open risk (e.g. 2–3% across all positions).
  `InpMaxPositions` caps the *count* per symbol; you manage correlation across
  symbols yourself. EURUSD long + GBPUSD long + AUDUSD long is essentially **one
  big USD short** — three positions, one bet.
- **Daily loss limit:** if you're down e.g. 2–3% on the day, **stop**. Disable
  algo trading. Tomorrow exists.
- **No averaging into losers.** The EA never does this; neither should you. Adding
  to a loser is how small, survivable mistakes become account-ending ones.

## The drawdown table (print this and put it on your wall)

| Drawdown | Gain needed to recover |
|---|---|
| −10% | +11% |
| −25% | +33% |
| −50% | +100% |
| −75% | +300% |

Losses compound against you **non-linearly**. This single table is *why* every
legend in this course obsessed over not losing. Protecting capital isn't
cautious — it's the only mathematically sane way to play.

➡️ Next: [06 — Trade management](06-trade-management.md)
