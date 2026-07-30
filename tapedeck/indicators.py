#!/usr/bin/env python3
"""
Tapedeck — indicator math.

Pure functions over a candle series. Every series returned is the *same length*
as the input, with `None` through the warm-up period, so a value can always be
read at bar `i` without off-by-one juggling:

    rsi14 = rsi(closes)
    if rsi14[i] is not None and rsi14[i] < 30: ...

No pandas, no numpy — the whole toolkit runs on a clean Python install.
"""


def _closes(bars):
    return [b.close for b in bars]


# ---------------------------------------------------------------- averages
def sma(values, length):
    out, run = [None] * len(values), 0.0
    for i, v in enumerate(values):
        run += v
        if i >= length:
            run -= values[i - length]
        if i >= length - 1:
            out[i] = run / length
    return out


def ema(values, length):
    out = [None] * len(values)
    if len(values) < length:
        return out
    k = 2.0 / (length + 1)
    prev = sum(values[:length]) / length          # seed on the first SMA
    out[length - 1] = prev
    for i in range(length, len(values)):
        prev = (values[i] - prev) * k + prev
        out[i] = prev
    return out


# ---------------------------------------------------------------- momentum
def rsi(values, length=14):
    """Wilder's RSI — the one charting platforms draw."""
    out = [None] * len(values)
    if len(values) <= length:
        return out
    gains = losses = 0.0
    for i in range(1, length + 1):
        change = values[i] - values[i - 1]
        gains += max(change, 0.0)
        losses += max(-change, 0.0)
    avg_gain, avg_loss = gains / length, losses / length
    out[length] = _rsi_value(avg_gain, avg_loss)
    for i in range(length + 1, len(values)):
        change = values[i] - values[i - 1]
        avg_gain = (avg_gain * (length - 1) + max(change, 0.0)) / length
        avg_loss = (avg_loss * (length - 1) + max(-change, 0.0)) / length
        out[i] = _rsi_value(avg_gain, avg_loss)
    return out


def _rsi_value(avg_gain, avg_loss):
    if avg_loss == 0:
        # a dead-flat series has no gains either — calling that "100, screaming
        # overbought" is wrong, so it reads neutral
        return 50.0 if avg_gain == 0 else 100.0
    return 100.0 - 100.0 / (1 + avg_gain / avg_loss)


def macd(values, fast=12, slow=26, signal=9):
    """Returns (macd_line, signal_line, histogram), all input-length."""
    fast_e, slow_e = ema(values, fast), ema(values, slow)
    line = [None if fast_e[i] is None or slow_e[i] is None else fast_e[i] - slow_e[i]
            for i in range(len(values))]
    start = next((i for i, v in enumerate(line) if v is not None), len(line))
    sig_tail = ema(line[start:], signal) if start < len(line) else []
    sig = [None] * start + sig_tail
    hist = [None if line[i] is None or sig[i] is None else line[i] - sig[i]
            for i in range(len(values))]
    return line, sig, hist


# ---------------------------------------------------------------- range / vol
def true_range(bars, i):
    if i == 0:
        return bars[0].high - bars[0].low
    prev = bars[i - 1].close
    return max(bars[i].high - bars[i].low, abs(bars[i].high - prev), abs(bars[i].low - prev))


def atr(bars, length=14):
    out = [None] * len(bars)
    if len(bars) <= length:
        return out
    trs = [true_range(bars, i) for i in range(len(bars))]
    prev = sum(trs[1:length + 1]) / length
    out[length] = prev
    for i in range(length + 1, len(bars)):
        prev = (prev * (length - 1) + trs[i]) / length
        out[i] = prev
    return out


def bollinger(values, length=20, mult=2.0):
    mid = sma(values, length)
    upper, lower = [None] * len(values), [None] * len(values)
    for i in range(len(values)):
        if mid[i] is None:
            continue
        window = values[i - length + 1:i + 1]
        mean = mid[i]
        sd = (sum((v - mean) ** 2 for v in window) / length) ** 0.5
        upper[i], lower[i] = mean + mult * sd, mean - mult * sd
    return mid, upper, lower


def volume_ratio(bars, length=20):
    """Bar volume as a multiple of the trailing average. 3.0 == '+200%'."""
    vols = [b.volume for b in bars]
    avg = sma(vols, length)
    return [None if not avg[i] else vols[i] / avg[i] for i in range(len(bars))]


def whale_momentum(bars, vol_len=50, trend_len=20, slope=5):
    """
    "A momentum oscillator that crosses whale activity with price trend."

    Not a standard indicator — this is Tapedeck's own composite, defined here so
    it can be read, argued with and changed:

        whale_i = (volume_i - mean(volume, vol_len)) / stdev(volume, vol_len)
        trend_i = (EMA(trend_len)_i - EMA(trend_len)_{i-slope}) / ATR_i
        osc_i   = 100 * tanh(0.5 * whale_i * trend_i)

    Reads as: big unusual volume pushing *with* the trend prints strongly
    positive; big volume pushing against it prints negative; quiet drift sits
    near zero. Bounded to -100..100 so it can share an axis with RSI.
    """
    import math

    vols = [b.volume for b in bars]
    vol_mean = sma(vols, vol_len)
    trend_ema, atr_series = ema(_closes(bars), trend_len), atr(bars)
    out = [None] * len(bars)
    for i in range(len(bars)):
        if (vol_mean[i] is None or atr_series[i] in (None, 0)
                or i < slope or trend_ema[i] is None or trend_ema[i - slope] is None):
            continue
        window = vols[i - vol_len + 1:i + 1]
        sd = (sum((v - vol_mean[i]) ** 2 for v in window) / vol_len) ** 0.5
        if sd == 0:
            continue
        whale = (vols[i] - vol_mean[i]) / sd
        trend = (trend_ema[i] - trend_ema[i - slope]) / atr_series[i]
        out[i] = 100.0 * math.tanh(0.5 * whale * trend)
    return out


def pct_change(values, length=1):
    out = [None] * len(values)
    for i in range(length, len(values)):
        base = values[i - length]
        if base:
            out[i] = (values[i] - base) / base * 100.0
    return out


# ---------------------------------------------------------------- structure
def pivots(bars, left=3, right=3):
    """Swing highs/lows: a bar whose extreme beats `left`/`right` neighbours."""
    highs, lows = [], []
    for i in range(left, len(bars) - right):
        window = bars[i - left:i + right + 1]
        if bars[i].high >= max(b.high for b in window):
            highs.append(i)
        if bars[i].low <= min(b.low for b in window):
            lows.append(i)
    return highs, lows


def levels(bars, left=3, right=3, tolerance=0.004, top=4):
    """
    Horizontal support/resistance the way you'd draw it by hand: collect swing
    pivots, cluster the ones sitting at the same price, keep the best-attended.

    Returns [{price, touches, kind, last_index}], strongest first.
    """
    highs, lows = pivots(bars, left, right)
    raw = ([(bars[i].low, "support", i) for i in lows]
           + [(bars[i].high, "resistance", i) for i in highs])
    if not raw:
        return []
    raw.sort(key=lambda r: r[0])

    # Compare against the cluster's anchor, not its previous member: chaining off
    # the neighbour lets a dense run of pivots merge into one band far wider than
    # `tolerance`, which is how you end up with a single "level" touched 119 times.
    clusters, current = [], [raw[0]]
    for point in raw[1:]:
        if abs(point[0] - current[0][0]) / current[0][0] <= tolerance:
            current.append(point)
        else:
            clusters.append(current)
            current = [point]
    clusters.append(current)

    out = []
    for group in clusters:
        prices = [p[0] for p in group]
        kinds = [p[1] for p in group]
        out.append({
            "price": sum(prices) / len(prices),
            "touches": len(group),
            "kind": max(set(kinds), key=kinds.count),
            "last_index": max(p[2] for p in group),
        })
    # well-attended first, then most recent — that's what a trader actually watches
    out.sort(key=lambda lv: (-lv["touches"], -lv["last_index"]))
    return out[:top]


# ---------------------------------------------------------------- bundle
def compute(bars, rsi_len=14, vol_len=20):
    """Everything the scanner and chart need, in one pass."""
    closes = _closes(bars)
    macd_line, macd_sig, macd_hist = macd(closes)
    mid, upper, lower = bollinger(closes)
    return {
        "close": closes,
        "rsi": rsi(closes, rsi_len),
        "ema20": ema(closes, 20),
        "ema50": ema(closes, 50),
        "sma200": sma(closes, 200),
        "atr": atr(bars),
        "vol_ratio": volume_ratio(bars, vol_len),
        "change_1": pct_change(closes, 1),
        "change_24": pct_change(closes, 24),
        "macd": macd_line,
        "macd_signal": macd_sig,
        "macd_hist": macd_hist,
        "bb_mid": mid,
        "bb_upper": upper,
        "bb_lower": lower,
        "whale_momentum": whale_momentum(bars),
    }


# ---------------------------------------------------------------- dynamic refs
def series(bars, kind, length=None):
    """
    Build one named series on demand — this is what lets a plain-English brief
    ask for any length ("above the 200 EMA") instead of a fixed handful.
    """
    closes = _closes(bars)
    if kind == "close":
        return closes
    if kind == "rsi":
        return rsi(closes, length or 14)
    if kind == "ema":
        return ema(closes, length or 20)
    if kind == "sma":
        return sma(closes, length or 50)
    if kind == "atr":
        return atr(bars, length or 14)
    if kind == "vol_ratio":
        return volume_ratio(bars, length or 20)
    if kind == "change":
        return pct_change(closes, length or 1)
    if kind == "volume":
        return [b.volume for b in bars]
    if kind == "whale":
        return whale_momentum(bars)
    if kind in ("macd", "macd_signal", "macd_hist"):
        line, sig, hist = macd(closes)
        return {"macd": line, "macd_signal": sig, "macd_hist": hist}[kind]
    if kind in ("bb_upper", "bb_lower", "bb_mid"):
        mid, upper, lower = bollinger(closes, length or 20)
        return {"bb_mid": mid, "bb_upper": upper, "bb_lower": lower}[kind]
    raise ValueError("unknown series %r" % kind)


def label(kind, length=None):
    """Human name for a series reference, for the 'here's what I heard' echo."""
    names = {
        "close": "close price", "rsi": "RSI", "ema": "EMA", "sma": "SMA",
        "atr": "ATR", "vol_ratio": "volume vs average", "change": "% change",
        "volume": "volume", "whale": "whale-momentum", "macd": "MACD line",
        "macd_signal": "MACD signal", "macd_hist": "MACD histogram",
        "bb_upper": "Bollinger upper", "bb_lower": "Bollinger lower",
        "bb_mid": "Bollinger mid",
    }
    base = names.get(kind, kind)
    if kind == "vol_ratio":
        return "volume vs %d-bar average" % (length or 20)
    if kind == "change":
        return "%% change over %d bar(s)" % (length or 1)
    return "%s(%d)" % (base, length) if length else base


# what the brief parser is allowed to reference, and how to say it
FIELDS = {
    "rsi": "RSI (14)",
    "vol_ratio": "volume vs 20-bar average (3.0 = +200%)",
    "close": "close price",
    "ema20": "EMA (20)",
    "ema50": "EMA (50)",
    "sma200": "SMA (200)",
    "atr": "ATR (14)",
    "change_1": "% change this bar",
    "change_24": "% change over 24 bars",
    "macd": "MACD line",
    "macd_hist": "MACD histogram",
    "bb_upper": "Bollinger upper (20, 2)",
    "bb_lower": "Bollinger lower (20, 2)",
}
