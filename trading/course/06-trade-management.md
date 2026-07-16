# 06 — Trade Management

The entry is maybe 20% of the result. **What you do after you're in** — when to
protect, when to let it run, when to add, when to quit — is where Lipschutz said
the real money is made. He didn't just enter and wait for a target; he *traded
around a core position*, managing it as the story unfolded.

## The default management plan (what the EA does)

1. **Enter** with full stop and target set (modules 04–05).
2. **At +1R, move the stop to break-even** (`InpMoveToBE`). The trade is now
   "free": worst case is a scratch. This single habit transforms your psychology —
   most of your trades become risk-free fairly quickly, so you can sit calmly
   through the noise on the winners.
3. **After +1R, trail the stop by ATR** (`InpTrailAfter1R`, distance
   `InpTrailATR`). This locks in open profit while giving the trend room to
   breathe — the mechanical version of "let your winners run".
4. **Exit** at the liquidity-pool target, the trailing stop, or break-even.

That's a complete, hands-off plan. Everything below is optional sophistication
you can backtest before adopting.

## Break-even: the nuance

Moving to break-even too *early* (before +1R) is a classic mistake — you get
stopped out of good trades by normal noise, right before they work. Waiting for
**+1R** means the trade has already proven it can travel as far as your risk
before you protect it. Test moving to BE at +1R vs. +1.5R on your data; markets
differ.

## Letting winners run vs. taking the target

Two philosophies, both legitimate:

- **Fixed target (default).** Exit at the next liquidity pool / 3R. Simple,
  mechanical, high "win feel". Easiest to follow.
- **Trail and ride.** Take partial at the target and trail the rest for the
  occasional 5–10R trend trade. This is where the *asymmetric outliers* that pay
  for everything else come from — but it requires the discipline to give back
  open profit on the runners.

### A common hybrid: scale-out (the Lipschutz "core")

> *Not in the base EA — a great extension to code yourself.*

- Close **half at 2R**, move the rest to break-even.
- **Trail the remaining half** with the ATR stop toward the next liquidity pool
  and beyond.

You bank a guaranteed profit, remove all risk, and keep a runner for the home
run. The downside: it caps some of your biggest trades. Backtest whether
"runner" or "fixed target" has better expectancy on *your* symbol before
committing.

## Adding to winners (pyramiding) — advanced & optional

The macro legends scaled *into* winning positions as the thesis confirmed —
never into losers. If you pyramid:

- **Only add on a fresh, valid setup** in the same direction (a new sweep+shift),
  not on hope.
- **Each add gets its own stop**, and your *total* open risk must stay within the
  portfolio cap from module 05. Adds are smaller than the original.
- Move the whole position's protective stop up as structure builds, so a winner
  can never become a loser.

Pyramiding is how a good trade becomes a *great* one — and how an undisciplined
trader blows up. Demo it for a long time first.

## When to override the machine

Mostly: **don't.** The point of mechanising the method is to remove the
in-the-moment emotion that wrecks discretionary traders. But there are sane
manual overrides:

- **High-impact news** (FOMC, NFP, CPI) inside the next hour → consider flattening
  or not opening new risk. The base EA has no news filter; *you* are the filter.
- **Thesis breaks** (module 02 bias flips on the H4) → it's legitimate to close
  early rather than wait for the stop, exactly as Druckenmiller exited the moment
  his reason was gone.
- **Hitting your daily loss limit** → disable algo trading for the day. No
  exceptions.

Decide these rules **in advance** and write them in your plan (module 10). An
override you invent mid-trade is just an emotion wearing a disguise.

➡️ Next: [07 — Psychology & journaling](07-psychology-and-journaling.md)
