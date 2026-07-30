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

## What markets it works on

**Crypto spot pairs, and only those.** Public, keyless, read-only:

1. **Coinbase Exchange** — primary, 528 tradable spot pairs
2. **Kraken** — fallback when Coinbase has no data for a pair

Coinbase's listings by quote currency, at the time of writing:

| quote | pairs | | quote | pairs |
|---|---:|---|---|---:|
| **USD** | **402** | | USDT | 23 |
| EUR | 35 | | ETH | 6 |
| GBP | 25 | | USDC | 5 |
| BTC | 24 | | INR / SGD / AUD / CAD / BRL | 8 |

The default universe is the **402 USD pairs**. `feed.products()` and
`feed.liquid_products()` take a `quotes` tuple if you want EUR or GBP, though the
brief parser doesn't yet read "in EUR" out of a sentence — pass it in code.

**Timeframes:** `1m`, `5m`, `15m`, `1h`, `6h`, `1d`. Ask for 4h and it uses 6h and
says so. History is paginated, so a few hundred to a few thousand bars per market
is routine.

**Naming:** `BTC-USD` for an exact pair, or just `BTC` for every USD market with
that base. `bitcoin`, `ether`, `solana` and a dozen other full names work too.
Anything else needs the ticker in caps (`HYPE`, `TAO`).

### What it does not cover

No equities, no FX, no futures, no perps, no options, no indices. There is no
venue behind this that lists them, so:

```
python tapedeck.py "scan AAPL for RSI below 30"

Not listed on these venues: AAPL
Tapedeck reads crypto spot markets (402 USD pairs on Coinbase, Kraken as fallback).
No equities, FX or futures — and no way to fake them.

Nothing to scan. Try a listed pair, e.g. BTC-USD, ETH-USD, SOL-USD.
```

Name a symbol it can't find and it stops and tells you. It will not substitute a
market you didn't ask for. Ask for "BTC futures" and it reads BTC **spot** and
lists that as an assumption — no funding, no basis, no leverage anywhere in the
model.

Responses cache to `cache/` for about half a bar, so re-running a brief is instant
and a whole-market scan costs one ranking call plus one call per market. If both
venues are unreachable the cache is served stale rather than failing.

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
selftest.py     94 offline checks — no network needed
```

```
python selftest.py
```

Runs on synthetic candles and asserts the things that would otherwise fail
quietly: series alignment, RSI at its limits, the no-look-ahead rule, the
stop-before-target rule, hit rate matching the blotter, level clustering not
collapsing into one band, crossings firing exactly once at the transition, exit
clauses not swallowing strategy parameters, bar-close alignment for watch mode,
the cache never answering a request for more history than it holds, and an
unlisted symbol never silently becoming a market you didn't ask for.

---

## Limits worth knowing

- One instrument at a time. Nothing here sizes a portfolio or manages risk.
- One venue's spot tape — no consolidated feed, no order book, no funding.
- Long or short, one position at a time, fixed notional, no compounding.
- `levels()` finds horizontal price bands. It does not draw trendlines or channels.
- The scanner checks bars that have **closed**. It is not a live alerting service.

---

# Execution — trading a brief automatically

Everything above is read-only. This part sends orders.

```
python live.py "BTC with RSI below 30 and volume +200%, 1.5 ATR stop, 3% target"
```

`tapedeck.py` **cannot trade**. It has no order path and no credential handling —
the read-only tool stays read-only, and every line that can spend money lives in
`live.py` and the four modules it imports. That split is the point: the trading
surface is small enough to read in one sitting.

## Three modes

| mode | money | keys | what it does |
|---|---|---|---|
| `--mode paper` *(default)* | simulated | none | real prices, simulated fills, full blotter |
| `--mode shadow` | none | read keys | authenticates, reads your real balances and market rules, **prints** the orders it would send |
| `--mode live` | **real** | trade keys | sends orders |

Run them in that order. Shadow is the stage that tells you whether your sizing,
the venue's increments and your actual funds survive contact with the real
account — before an order exists.

## Arming live mode takes two independent actions

```
--mode live                    on the command line
TAPEDECK_LIVE_CONFIRM=yes      in the environment
```

Miss either and it refuses, names the missing gate, and exits without sending
anything. One gate is too easy to trip with a stale shell alias.

## Keys

From the environment only — never a CLI argument (those land in shell history and
in `ps` output), never a file in the repo.

| `--venue` | environment variables | signing |
|---|---|---|
| `kraken` | `KRAKEN_API_KEY`, `KRAKEN_API_SECRET` | HMAC-SHA512 |
| `coinbase-exchange` | `CB_EXCHANGE_KEY`, `CB_EXCHANGE_SECRET`, `CB_EXCHANGE_PASSPHRASE` | HMAC-SHA256 |
| `coinbase-advanced` | `CB_CDP_KEY_NAME`, `CB_CDP_PRIVATE_KEY` | ES256 JWT |

`python venues.py` reports which venues are configured. It prints presence only,
never a value — a truncated key in a log is still a leaked key.

Grant the key **trade** permission and nothing more. There is no withdrawal or
transfer call anywhere in this project, and no venue requires withdrawal
permission to place an order. A trading key that cannot move coins off the
exchange is a categorically smaller problem if it leaks.

`coinbase-advanced` is the one adapter with a dependency: ES256 is not in the
standard library, so it needs `pip install "PyJWT[crypto]"`. Everything else,
including all of paper mode, stays dependency-free.

## How a bar is traded — and why it matches the backtest

The backtester evaluates conditions on a **closed** bar and enters at the **next
bar's open**. Live, the moment a bar closes *is* the next bar's open, so a market
order placed immediately after the close is the faithful equivalent. That is why
the loop is bar-aligned rather than polling every few seconds: it makes the live
rule and the tested rule the same rule.

Each bar close, per market:

1. refresh candles
2. let resting stops resolve (paper simulates; live asks the venue)
3. manage an open position — stop gone? target hit? exit signal? held too long?
4. otherwise test the entry conditions, then ask the risk gate
5. on a permitted entry: send the order, then **immediately** park a protective
   stop at the venue

If step 5's stop cannot be placed, the position is closed again at once. A
position without a stop is the one state this loop will not sit in — it would
rather take a small round-trip loss than hold something unprotected.

## The risk gate

Every entry passes `risk.RiskEngine.check_entry()` before an order exists.
Nothing in the loop sizes a trade by itself.

```
kill switch       a file on disk halts new entries, immediately
shorting          refused unless the broker can actually borrow (spot cannot)
daily loss        realised losses past the day's cap stop new entries
position count    one at a time by default
cooldown          N bars of silence after a loss
exposure          total open notional ceiling
size              clamped DOWN to the per-trade cap; refused below the floor
price sanity      an intended fill far from the signal bar's close is refused
stop sanity       a stop on the wrong side, or absurdly tight, is refused
funds             the quote balance has to cover it, fees included
```

`--max-notional`, `--max-exposure`, `--max-positions`, `--daily-loss` and
`--cooldown` set the numbers. The defaults are deliberately tiny; a user who
wants size has to say so.

**The gate never blocks an exit.** A risk limit that can stop you from *closing* a
position is not a limit, it is a trap — a daily-loss stop that refuses the sell
order which would end the losing day is precisely backwards. Entries are gated;
exits, cancels and flattens always proceed.

## Stopping it

```
touch HALT                          stop opening new positions, keep managing open ones
python live.py --flatten            close everything now
Ctrl-C                              stop the loop, leave positions as they are
```

`HALT` is a file rather than a flag so you can stop a running loop from another
terminal, from a phone over SSH, or from a cron job, without finding the process.

## Crash safety

The loop will be killed mid-trade eventually. `ledger.py` is the memory and
`reconcile()` is the part that matters — on every start it asks the venue what is
actually true and compares:

- **ledger holds something the venue doesn't** → usually the stop filled while we
  were dead. Booked at the stop price, marked `reconciled-stop`, counted against
  the daily loss. Not silently forgotten.
- **position is real but its stop is gone** → a naked position. Reported, and the
  stop is replaced before anything else happens.
- **venue holds orders we don't know about** → reported, never auto-cancelled.
  They might be yours from another tool.

If the ledger and the venue disagree in a way that can't be resolved safely, it
refuses to trade until you look, or until you pass `--adopt`.

Every order carries a **deterministic client id** hashed from the market, the side
and the bar that triggered it. Send it twice — a retry after a timeout, a restart
mid-loop — and the venue sees a duplicate and rejects it instead of doubling your
size. Submitted ids are recorded *before* the send, so the worst case of a crash
between those two lines is a signal you skip, never an order you send twice.

## Verification status

```
python selftest_live.py     148 offline checks — no network, no credentials, no venue
```

Covers: sizes rounding down and never up, a retried order not becoming two
positions, every risk rejection, the kill switch, the daily loss stop, a short on
spot being refused rather than quietly flipped, ledger P&L matching the blotter, a
corrupt or wrong-version ledger starting empty instead of crashing, all four
reconciliation outcomes, and the signing schemes against pinned vectors.

Paper mode has been run end to end against live Coinbase data: entry, protective
stop, position surviving three separate processes, target/stop/time exits,
`--flatten`, and both refusal paths.

**The live adapters have not been exercised against a funded account from this
repo.** No keys were available, and claiming an order path works when it has never
placed an order would be the most dangerous sentence in this README. The signing
tests prove the implementations don't drift; they cannot prove a venue accepts
them. `--mode shadow` is how you find out, and it is the first thing you should
run.

## What none of this does

- A stop is an instruction, not a guarantee. Gaps, halts and thin books all fill
  it worse than its price — sometimes far worse.
- Limits are per-process. Two Tapedecks on one account do not know about each
  other and will happily double your exposure.
- The daily loss stop counts **realised** losses. An open position can be far
  underwater without tripping it.
- A backtested edge is not evidence that live fills will resemble the backtest's.
  Costs, latency and slippage are where paper profits go.
- Nothing here models funding, borrow, tax, or a venue freezing withdrawals.

Not advice. The strategy is yours; this only executes it.
