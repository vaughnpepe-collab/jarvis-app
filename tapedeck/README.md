# Tapedeck

**Say what you want to see. It operates the chart.**

```
python tapedeck.py "find me all BTC markets with RSI below 30 and volume +200% at the same time"
```

```
Brief: find me all BTC markets with RSI below 30 and volume +200% at the same time

  Universe   BTC
  Timeframe  1h bars
  Conditions (all must hold on the same bar)
    · RSI(14) below 30
    · volume at least 200% above its 20-bar average (3.00x)
  Will do    chart, scan

  Assumptions made:
    - read 'volume +200%' as 3.00x the 20-bar average volume

1 market matched — 0 live on the newest closed bar.

  BTC-USD      last fired 2026-07-24 14:00 UTC   close 63,994   2 hits in window
       RSI(14)                       27.32  < 30.00
       volume vs 20-bar average       4.16  > 3.00

Chart written: charts/btc-usd-1h.html
```

One plain-English brief goes in. What comes back: the spec it understood, a scan
across the universe, the support and resistance it drew, a backtest of the rules,
and a self-contained HTML chart with **candle-by-candle replay** — the P&L
updating as trades open and close.

No API key. No account. No packages. Nothing is ever ordered, and there is no
code path in this project that could place a trade.

---

## Run it

```
python tapedeck.py "show me SOL daily with support and resistance drawn"
python tapedeck.py "scan the market for RSI above 70 and price above the 200 EMA"
python tapedeck.py "backtest ETH with RSI below 35 and volume +150%, 2% stop, 5% target"
python tapedeck.py "replay last week and show me where my system would have entered"
python tapedeck.py "write me a momentum oscillator that crosses whale activity with price trend"
```

Python 3.8+. Standard library only — no pip install, no build step.

| flag | |
|---|---|
| `--top N` | markets to rank when scanning the whole market (default 40) |
| `--charts N` | how many matching markets to chart (default 6) |
| `--history N` | bars of history per market (default 700) |
| `--fresh` | ignore the cache, refetch |
| `--watch` | keep re-scanning on every bar close, report new firings |
| `--open` | open the chart when it's written |
| `--new` | forget the previous brief |
| `--quiet` | skip the spec echo |

### Watch mode

```
python tapedeck.py "scan the market for RSI below 30 and volume +200%" --watch
```

Runs the scan once, then wakes on each bar close (aligned to the venue's bar
boundary, plus a few seconds' grace) and re-checks. A setup is announced on the
bar it fires, once — a market that stays in condition for hours doesn't spam you,
and each firing writes its chart. `Ctrl-C` stops it.

It reads and reports. It cannot place an order, because no such code exists here.

### It remembers the last brief

Consecutive runs chain, so a follow-up can refer to what you just said:

```
python tapedeck.py "find BTC with RSI below 30 and volume +200%"
python tapedeck.py "now replay last week and show me where my system would have entered"
```

The second run inherits the conditions and the market from the first, and says so
in its assumptions. `--new` starts clean.

---

## What the chart gives you

Open `charts/<market>-<tf>.html` — one file, no server, works offline.

- Candles, EMA20/50, volume, and an RSI panel
- The **levels** it drew: swing pivots clustered by price, labelled with touch count
- Every bar the conditions **fired**, including ones skipped because a position
  was already open
- Entry and exit markers per trade, with the stop and target rails shown while a
  trade is live
- **Replay** — press `Replay` or `space`, and it walks the window bar by bar with
  realised and open P&L updating live. `←`/`→` step, the slider scrubs.
- An **equity curve** of closed-trade P&L that builds as the replay runs
- **Pan and zoom** — drag the chart to move through history, scroll to zoom,
  double-click (or `Home`) to re-pin the view to the replay cursor. Bars the
  replay hasn't reached stay hidden however far you pan.
- Hover any candle for OHLC, RSI and whale-momentum at that bar

---

## Honesty rules

The genre this belongs to is full of screenshots of numbers with the assumptions
cropped out. The rules here:

1. **No look-ahead.** Conditions are evaluated on a *closed* bar and the position
   opens at the **next bar's open**. You cannot buy the candle that told you to buy.
2. **Costs are on by default** — `FEE_PCT` 0.10% and `SLIPPAGE_PCT` 0.05% per side,
   applied to every fill. You can zero them, but you have to do it on purpose.
3. **The worse branch wins.** When a stop and a target both sit inside one bar,
   the bar doesn't say which came first, so the stop is taken.
4. **Every assumption is printed** next to the result — stop, target, max hold,
   fill rule, costs, stake, and how any vague phrase in your brief got pinned to
   a number.
5. **Vague input is reported, not guessed silently.** `volume +200%` becomes
   `3.00x the 20-bar average` and the run tells you it made that reading.

A backtest describes past bars under stated assumptions. It is not a prediction,
and none of this is financial advice.

---

## How the parser works

`brief.py` is a **deterministic regex parser** — no model call, no key, no network.
The same sentence always produces the same spec, and everything it inferred lands
in `notes` where you can see it. For a tool whose output you're supposed to check,
reproducibility beats flexibility.

It understands, among others:

| you write | it runs |
|---|---|
| `RSI below 30`, `rsi(21) goes above 70` | RSI at any length, either direction |
| `volume +200%`, `volume above 3x average`, `volume spike` | volume vs its 20-bar average |
| `price above the 200 EMA` | close compared against another series |
| `MACD crosses above its signal` | crossings, on any supported field |
| `price crosses back above the 200 EMA` | close crossing a moving average |
| `RSI crosses below 30`, `MACD crosses above zero` | crossing a level |
| `below the lower Bollinger band` | close vs BB(20, 2) |
| `MACD positive` | MACD histogram sign |
| `up more than 5%` | % change over 24 bars |
| `exit when RSI goes above 70` | condition-based exit, filled at that bar's close |
| `1.5 ATR stop`, `2% stop`, `3% target`, `hold 10 bars` | strategy parameters |
| `on the 4 hour`, `daily`, `15m` | timeframe (rounded to a bar the feed has, and it says so) |
| `scan the market`, `all BTC`, `SOL` | universe |
| `replay last week`, `last 30 days` | replay window |

A crossing fires **once**, on the bar that broke through — not on every bar that
stays on the far side. `RSI crosses above 30` is not read as `RSI above 30`, and
sitting exactly on a level is not a cross.

Conditions combine with AND: they must all hold on the same bar. An exit rule is
parsed from its own clause, so `exit when RSI goes above 70, 2% stop` keeps the
stop as a strategy parameter instead of folding it into the exit condition. If an
exit clause can't be read, it says so and falls back to stop/target/time rather
than inventing a rule.

<a id="llm-handoff"></a>
**LLM_HANDOFF** — to accept looser phrasing, put a model in front of `brief.parse`
rather than inside it: have it emit the same spec dict (`symbols`, `timeframe`,
`filters`, `strategy`, `actions`), then hand that straight to `scan.run` /
`backtest.run`. Keep `describe()` in the loop so whatever the model decided is
still printed for a human to read before anything executes.

---

## Data

Public, keyless, read-only:

1. **Coinbase Exchange** — spot, ~400 USD markets, primary
2. **Kraken** — fallback when Coinbase has no data for a pair

Responses cache to `cache/` for about half a bar, so re-running a brief is instant
and a whole-market scan costs one ranking call plus one call per market. If both
venues are unreachable the cache is served stale rather than failing.

This is **spot** data. Ask for futures or perps and it will read spot and tell you
that's what it did — no funding, no basis, no leverage anywhere in the model.

---

## The custom indicator

`indicators.py` has `whale_momentum`, which exists because "write me a momentum
oscillator that crosses whale activity with price trend" deserves an actual
answer rather than a mock-up:

```
whale_i = (volume_i - mean(volume, 50)) / stdev(volume, 50)
trend_i = (EMA(20)_i - EMA(20)_{i-5}) / ATR_i
osc_i   = 100 * tanh(0.5 * whale_i * trend_i)
```

Unusual volume pushing *with* the trend prints strongly positive; heavy volume
pushing against it prints negative; quiet drift sits near zero. Bounded to
-100..100 so it shares an axis with RSI. It's plotted on every chart and readable
on hover. It is **my** definition, not a standard — the formula is nine lines,
change it.

---

## Files

```
tapedeck.py     CLI — brief in, scan + levels + backtest + chart out
brief.py        plain English -> spec, and the "here's what I heard" echo
feed.py         keyless OHLCV with disk cache and venue fallback
indicators.py   RSI, EMA/SMA, ATR, MACD, Bollinger, volume ratio, pivots,
                level clustering, whale-momentum
scan.py         evaluates a spec's conditions across the universe
backtest.py     the rules over history, with costs and no look-ahead
chart.py        writes the self-contained HTML chart + replay
selftest.py     85 offline checks — no network needed
```

```
python selftest.py
```

Runs on synthetic candles and asserts the things that would otherwise fail
quietly: series alignment, RSI at its limits, the no-look-ahead rule, the
stop-before-target rule, hit rate matching the blotter, level clustering not
collapsing into one band, crossings firing exactly once at the transition, exit
clauses not swallowing strategy parameters, bar-close alignment for watch mode,
and the cache never answering a request for more history than it holds.

---

## Limits worth knowing

- One instrument at a time. Nothing here sizes a portfolio or manages risk.
- One venue's spot tape — no consolidated feed, no order book, no funding.
- Long or short, one position at a time, fixed notional, no compounding.
- `levels()` finds horizontal price bands. It does not draw trendlines or channels.
- The scanner checks bars that have **closed**. It is not a live alerting service.
