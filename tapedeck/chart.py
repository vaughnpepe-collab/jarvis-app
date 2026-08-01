#!/usr/bin/env python3
"""
Tapedeck — chart writer.

Emits one self-contained HTML file per market: candles, the levels the toolkit
drew, every signal and trade the rules produced, an indicator panel, and a
replay mode that walks the window bar by bar with the PnL updating as trades
open and close.

No CDN, no build step, no dependencies — one file you can open with a
double-click or hand to someone else. All state lives in the page; nothing is
sent anywhere.
"""
import json
import os
import time

import indicators as ind

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ROOT, "charts")


def payload(product, spec, bars, levels, result, extra_series=None):
    """Everything the page needs, as plain JSON-able data."""
    closes = [b.close for b in bars]
    data = {
        "product": product,
        "timeframe": spec["timeframe"],
        "brief": spec["raw"],
        "conditions": [f["text"] for f in spec["filters"]],
        "notes": spec["notes"],
        "generated": time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime()),
        "bars": [[b.ts, b.open, b.high, b.low, b.close, b.volume] for b in bars],
        "levels": levels,
        "ema20": ind.ema(closes, 20),
        "ema50": ind.ema(closes, 50),
        "rsi": ind.rsi(closes, 14),
        "whale": ind.whale_momentum(bars),
        "signals": result.get("signals", []),
        "trades": result.get("trades", []),
        "stats": result.get("stats", {}),
        "assumptions": result.get("assumptions", {}),
        "replay_bars": spec.get("replay_bars"),
    }
    if extra_series:
        data.update(extra_series)
    return data


def write(product, spec, bars, levels, result, caveats, out_dir=None):
    out_dir = out_dir or OUT
    os.makedirs(out_dir, exist_ok=True)
    slug = product.lower().replace("/", "-") + "-" + spec["timeframe"]
    path = os.path.join(out_dir, slug + ".html")
    blob = json.dumps(payload(product, spec, bars, levels, result),
                      separators=(",", ":"), allow_nan=False)
    html = (TEMPLATE
            .replace("/*__DATA__*/null", blob)
            .replace("/*__CAVEATS__*/null", json.dumps(caveats))
            .replace("__TITLE__", "%s %s — Tapedeck" % (product, spec["timeframe"])))
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(html)
    return path


def write_index(entries, out_dir=None):
    """A contents page when a scan charted several markets."""
    out_dir = out_dir or OUT
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "index.html")
    rows = []
    for e in entries:
        stats = e.get("stats") or {}
        hit = "%.0f%%" % stats["hit_rate"] if stats.get("hit_rate") is not None else "—"
        net = "%+.2f%%" % stats["total_pct"] if stats.get("trades") else "—"
        rows.append(
            '<tr><td><a href="%s">%s</a></td><td>%s</td><td class="n">%s</td>'
            '<td class="n">%s</td><td class="n">%s</td><td>%s</td></tr>'
            % (os.path.basename(e["path"]), e["product"], e["timeframe"],
               e.get("hits", "—"), hit, net, e.get("when", "")))
    html = (INDEX_TEMPLATE
            .replace("__ROWS__", "\n".join(rows))
            .replace("__BRIEF__", _escape(entries[0]["brief"] if entries else ""))
            .replace("__COUNT__", str(len(entries)))
            .replace("__GENERATED__", time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime())))
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(html)
    return path


def _escape(text):
    return (text.replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


# --------------------------------------------------------------------------- #
# The page. Kept as one template so a chart is a single portable file.
# --------------------------------------------------------------------------- #
TEMPLATE = r"""<!DOCTYPE html>
<html lang="en"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>__TITLE__</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
:root{
  --bg:#0a0e0c; --panel:#0f1512; --line:#1b2420; --ink:#e8f0ea;
  --muted:#7d8f85; --up:#3fcf8e; --down:#ef5d5d; --accent:#c8f542;
  --blue:#5aa9ff; --amber:#f0b429;
}
body{background:var(--bg);color:var(--ink);font:14px/1.45 ui-monospace,SFMono-Regular,
  Menlo,Consolas,"Liberation Mono",monospace;overflow-x:hidden}
.wrap{max-width:1500px;margin:0 auto;padding:18px}
header{display:flex;flex-wrap:wrap;align-items:baseline;gap:14px;margin-bottom:4px}
h1{font-size:20px;letter-spacing:.02em}
h1 span{color:var(--accent)}
.tf{color:var(--muted);font-size:13px}
.brief{color:var(--muted);font-size:13px;margin:6px 0 14px;
  border-left:2px solid var(--accent);padding-left:10px}
.brief b{color:var(--ink);font-weight:400}
.chips{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:14px}
.chip{background:var(--panel);border:1px solid var(--line);border-radius:999px;
  padding:4px 12px;font-size:12px;color:var(--muted)}
.chip b{color:var(--accent);font-weight:600}
#stage{position:relative;background:var(--panel);border:1px solid var(--line);
  border-radius:10px;overflow:hidden}
canvas{display:block;width:100%;cursor:crosshair}
#tip{position:absolute;pointer-events:none;background:rgba(6,10,8,.94);
  border:1px solid var(--line);border-radius:6px;padding:8px 10px;font-size:12px;
  line-height:1.6;display:none;white-space:pre;z-index:5}
.bar{display:flex;flex-wrap:wrap;align-items:center;gap:10px;margin-top:12px}
button,select{background:var(--panel);color:var(--ink);border:1px solid var(--line);
  border-radius:7px;padding:7px 13px;font:inherit;font-size:13px;cursor:pointer}
button:hover,select:hover{border-color:var(--accent);color:var(--accent)}
button.on{background:var(--accent);color:#0a0e0c;border-color:var(--accent);font-weight:600}
button:disabled{opacity:.4;cursor:default}
input[type=range]{flex:1;min-width:180px;accent-color:var(--accent)}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));
  gap:14px;margin-top:16px}
.card{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:14px}
.card h2{font-size:11px;letter-spacing:.14em;text-transform:uppercase;
  color:var(--muted);margin-bottom:10px;font-weight:600}
.kv{display:flex;justify-content:space-between;gap:12px;padding:3px 0}
.kv span:first-child{color:var(--muted)}
.big{font-size:26px;letter-spacing:-.01em}
.pos{color:var(--up)} .neg{color:var(--down)} .dim{color:var(--muted)}
table{width:100%;border-collapse:collapse;font-size:12px}
th{text-align:left;color:var(--muted);font-weight:600;padding:5px 8px 5px 0;
  border-bottom:1px solid var(--line);font-size:11px;letter-spacing:.08em;
  text-transform:uppercase}
td{padding:5px 8px 5px 0;border-bottom:1px solid rgba(27,36,32,.6)}
td.n,th.n{text-align:right}
.scroll{max-height:260px;overflow-y:auto}
.note{color:var(--muted);font-size:12px;margin-top:6px}
.spark{width:100%;height:56px;margin-top:12px;display:block}
.hint{color:var(--muted);font-size:11px;margin-top:8px;letter-spacing:.02em}
ul.caveats{list-style:none;font-size:12px;color:var(--muted)}
ul.caveats li{padding:3px 0 3px 14px;position:relative}
ul.caveats li:before{content:"—";position:absolute;left:0}
footer{color:var(--muted);font-size:11px;margin:22px 0 8px;line-height:1.7}
@media (max-width:640px){.wrap{padding:12px}h1{font-size:17px}}
</style></head>
<body><div class="wrap">

<header>
  <h1><span>■</span> <span id="hProduct"></span></h1>
  <div class="tf" id="hTf"></div>
</header>
<div class="brief">asked: <b id="hBrief"></b></div>
<div class="chips" id="hChips"></div>

<div id="stage">
  <canvas id="cv"></canvas>
  <div id="tip"></div>
</div>

<div class="bar">
  <button id="bPlay">▶ Replay</button>
  <button id="bStep">Step ▸</button>
  <button id="bEnd">Skip to end</button>
  <select id="bSpeed">
    <option value="1">1x</option><option value="2">2x</option>
    <option value="4" selected>4x</option><option value="8">8x</option>
    <option value="16">16x</option>
  </select>
  <input type="range" id="bScrub" min="1" value="1">
  <span class="dim" id="bPos"></span>
</div>
<div class="hint">drag the chart to pan · scroll to zoom · double-click or Home to
  re-pin to the cursor · space plays, ←/→ step</div>

<div class="grid">
  <div class="card">
    <h2>Replay P&amp;L <span class="dim" id="pnlMode"></span></h2>
    <div class="big" id="pnlTotal">—</div>
    <div class="kv"><span>realised</span><span id="pnlReal">—</span></div>
    <div class="kv"><span>open</span><span id="pnlOpen">—</span></div>
    <div class="kv"><span>closed trades</span><span id="pnlCount">0</span></div>
    <div class="kv"><span>hit rate so far</span><span id="pnlHit">—</span></div>
    <canvas id="eq" class="spark"></canvas>
    <div class="note" id="pnlNote"></div>
  </div>

  <div class="card">
    <h2>Full-window result</h2>
    <div class="big" id="stNet">—</div>
    <div class="kv"><span>trades</span><span id="stTrades">—</span></div>
    <div class="kv"><span>hit rate</span><span id="stHit">—</span></div>
    <div class="kv"><span>avg / trade</span><span id="stAvg">—</span></div>
    <div class="kv"><span>best / worst</span><span id="stBW">—</span></div>
    <div class="kv"><span>profit factor</span><span id="stPF">—</span></div>
    <div class="kv"><span>max drawdown</span><span id="stDD">—</span></div>
    <div class="note">Theoretical, costs included. Not a forecast.</div>
  </div>

  <div class="card">
    <h2>Levels drawn</h2>
    <div id="lvList"></div>
    <div class="note">Swing pivots clustered by price; more touches = more attended.</div>
  </div>

  <div class="card">
    <h2>Rules as run</h2>
    <div id="asList"></div>
  </div>
</div>

<div class="grid">
  <div class="card" style="grid-column:1/-1">
    <h2>Trade blotter <span class="dim" id="blCount"></span></h2>
    <div class="scroll"><table>
      <thead><tr><th>#</th><th>signal (UTC)</th><th>entry</th><th>exit</th>
        <th>exit on</th><th class="n">bars</th><th class="n">net %</th>
        <th class="n">P&amp;L</th></tr></thead>
      <tbody id="blBody"></tbody>
    </table></div>
  </div>
</div>

<div class="grid">
  <div class="card" style="grid-column:1/-1">
    <h2>Read this with the numbers</h2>
    <ul class="caveats" id="cvList"></ul>
  </div>
</div>

<footer id="foot"></footer>
</div>

<script>
const D = /*__DATA__*/null;
const CAVEATS = /*__CAVEATS__*/null;

const bars = D.bars.map(b => ({ts:b[0], o:b[1], h:b[2], l:b[3], c:b[4], v:b[5]}));
const N = bars.length;
const cv = document.getElementById('cv'), ctx = cv.getContext('2d');
const tip = document.getElementById('tip');

let cursor = N;                          // bars revealed by the replay
let view = Math.min(200, N);             // candles on screen (zoom)
let right = N;                           // rightmost visible bar (pan)
let follow = true;                       // keep the right edge pinned to the cursor
let playing = false, timer = null, hover = null;
let drag = null;
const tradeByEntry = new Map(), tradeByExit = new Map(), signalSet = new Set(D.signals);
D.trades.forEach((t, i) => { t.n = i + 1;
  tradeByEntry.set(t.entry_index, t); tradeByExit.set(t.exit_index, t); });

/* ---------------------------------------------------------------- helpers */
const fmtP = v => v >= 1000 ? v.toLocaleString(undefined,{maximumFractionDigits:0})
  : v >= 1 ? v.toFixed(2) : v.toPrecision(4);
const fmtMoney = v => (v >= 0 ? '+' : '-') +
  Math.abs(v).toLocaleString(undefined,{minimumFractionDigits:2,maximumFractionDigits:2});
const fmtTime = ts => {
  const d = new Date(ts * 1000), p = n => String(n).padStart(2,'0');
  return d.getUTCFullYear() + '-' + p(d.getUTCMonth()+1) + '-' + p(d.getUTCDate()) +
    ' ' + p(d.getUTCHours()) + ':' + p(d.getUTCMinutes());
};
const cls = v => v > 0 ? 'pos' : v < 0 ? 'neg' : 'dim';

/* ---------------------------------------------------------------- drawing */
let L = {};                              // layout, recomputed on resize
function layout() {
  const dpr = window.devicePixelRatio || 1;
  const w = cv.parentElement.clientWidth;
  const h = Math.max(420, Math.min(660, Math.round(window.innerHeight * 0.62)));
  cv.width = w * dpr; cv.height = h * dpr; cv.style.height = h + 'px';
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  const padR = 74, padL = 8, padT = 14, padB = 22;
  const priceH = Math.round((h - padT - padB) * 0.62);
  const oscH   = Math.round((h - padT - padB) * 0.20);
  const volH   = (h - padT - padB) - priceH - oscH - 16;
  L = {w, h, padL, padR, padT, padB, priceH, oscH, volH,
       plotW: w - padL - padR,
       priceTop: padT, priceBot: padT + priceH,
       oscTop: padT + priceH + 8, oscBot: padT + priceH + 8 + oscH,
       volTop: padT + priceH + oscH + 16, volBot: h - padB};
}

function visible() {
  // never past the cursor — bars the replay hasn't reached must stay hidden
  const end = Math.max(1, Math.min(follow ? cursor : right, cursor));
  const start = Math.max(0, end - view);
  return {start, end};
}

function clampPan() {
  right = Math.max(Math.min(view, cursor), Math.min(right, cursor));
}

function scales() {
  const {start, end} = visible();
  const slice = bars.slice(start, end);
  let lo = Infinity, hi = -Infinity, vmax = 0;
  for (const b of slice) { lo = Math.min(lo, b.l); hi = Math.max(hi, b.h);
                           vmax = Math.max(vmax, b.v); }
  // keep drawn levels in frame when they're close to price
  for (const lv of D.levels) if (lv.price > lo * 0.97 && lv.price < hi * 1.03) {
    lo = Math.min(lo, lv.price); hi = Math.max(hi, lv.price); }
  const pad = (hi - lo) * 0.07 || hi * 0.01;
  lo -= pad; hi += pad;
  const n = end - start;
  const cw = L.plotW / Math.max(n, 1);
  return {
    start, end, lo, hi, vmax, cw,
    x: i => L.padL + (i - start) * cw + cw / 2,
    y: p => L.priceBot - (p - lo) / (hi - lo) * (L.priceBot - L.priceTop),
    yv: v => L.volBot - (vmax ? v / vmax : 0) * (L.volBot - L.volTop),
  };
}

function grid(s) {
  ctx.strokeStyle = '#1b2420'; ctx.fillStyle = '#7d8f85';
  ctx.lineWidth = 1; ctx.font = '11px ui-monospace,monospace';
  ctx.textAlign = 'left'; ctx.textBaseline = 'middle';
  for (let k = 0; k <= 5; k++) {
    const p = s.lo + (s.hi - s.lo) * k / 5, y = Math.round(s.y(p)) + .5;
    ctx.beginPath(); ctx.moveTo(L.padL, y); ctx.lineTo(L.w - L.padR, y); ctx.stroke();
    ctx.fillText(fmtP(p), L.w - L.padR + 7, y);
  }
  // time ticks
  ctx.textAlign = 'center'; ctx.textBaseline = 'top';
  const step = Math.max(1, Math.floor((s.end - s.start) / 6));
  for (let i = s.start; i < s.end; i += step) {
    const t = fmtTime(bars[i].ts);
    // keep the first/last label off the edges instead of letting them clip
    const x = Math.min(Math.max(s.x(i), L.padL + 34), L.w - L.padR - 34);
    ctx.fillText(t.slice(5, 16), x, L.volBot + 6);
  }
}

function candles(s) {
  const bw = Math.max(1, Math.min(s.cw * 0.68, 14));
  for (let i = s.start; i < s.end; i++) {
    const b = bars[i], up = b.c >= b.o, x = s.x(i);
    ctx.strokeStyle = up ? '#3fcf8e' : '#ef5d5d';
    ctx.fillStyle = up ? '#3fcf8e' : '#ef5d5d';
    ctx.beginPath();
    ctx.moveTo(Math.round(x) + .5, s.y(b.h));
    ctx.lineTo(Math.round(x) + .5, s.y(b.l));
    ctx.stroke();
    const yo = s.y(b.o), yc = s.y(b.c);
    ctx.fillRect(x - bw / 2, Math.min(yo, yc), bw, Math.max(1, Math.abs(yc - yo)));
    // volume
    ctx.globalAlpha = .45;
    ctx.fillRect(x - bw / 2, s.yv(b.v), bw, L.volBot - s.yv(b.v));
    ctx.globalAlpha = 1;
  }
}

function line(s, series, colour, width) {
  ctx.strokeStyle = colour; ctx.lineWidth = width || 1.4;
  ctx.beginPath(); let started = false;
  for (let i = s.start; i < s.end; i++) {
    const v = series[i];
    if (v === null || v === undefined) { started = false; continue; }
    const x = s.x(i), y = s.y(v);
    if (!started) { ctx.moveTo(x, y); started = true; } else ctx.lineTo(x, y);
  }
  ctx.stroke(); ctx.lineWidth = 1;
}

function levels(s) {
  ctx.font = '10px ui-monospace,monospace'; ctx.textBaseline = 'bottom';
  for (const lv of D.levels) {
    if (lv.price < s.lo || lv.price > s.hi) continue;
    const y = Math.round(s.y(lv.price)) + .5;
    ctx.strokeStyle = lv.kind === 'support' ? 'rgba(90,169,255,.55)' : 'rgba(240,180,41,.55)';
    ctx.setLineDash([5, 4]); ctx.beginPath();
    ctx.moveTo(L.padL, y); ctx.lineTo(L.w - L.padR, y); ctx.stroke();
    ctx.setLineDash([]);
    ctx.fillStyle = lv.kind === 'support' ? 'rgba(90,169,255,.9)' : 'rgba(240,180,41,.9)';
    ctx.textAlign = 'left';
    ctx.fillText(lv.kind[0].toUpperCase() + ' ' + fmtP(lv.price) + '  x' + lv.touches,
                 L.padL + 4, y - 2);
  }
}

function marks(s) {
  for (let i = s.start; i < s.end; i++) {
    // a bar where the conditions fired but no trade opened (already in one)
    if (signalSet.has(i) && !tradeByEntry.has(i + 1)) {
      ctx.fillStyle = 'rgba(200,245,66,.35)';
      const x = s.x(i), y = s.y(bars[i].l) + 12;
      ctx.beginPath(); ctx.arc(x, y, 2.6, 0, Math.PI * 2); ctx.fill();
    }
  }
  for (const t of D.trades) {
    if (t.entry_index >= s.end) continue;
    const open = t.exit_index >= cursor;      // still running at the cursor
    if (t.entry_index >= s.start) {
      const x = s.x(t.entry_index), y = s.y(t.entry);
      ctx.fillStyle = '#c8f542';
      ctx.beginPath(); ctx.moveTo(x, y + 16); ctx.lineTo(x - 6, y + 27);
      ctx.lineTo(x + 6, y + 27); ctx.closePath(); ctx.fill();
      ctx.fillStyle = '#0a0e0c'; ctx.font = 'bold 9px ui-monospace,monospace';
      ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
      ctx.fillText(String(t.n), x, y + 24);
    }
    if (!open && t.exit_index < s.end && t.exit_index >= s.start) {
      const x = s.x(t.exit_index), y = s.y(t.exit);
      ctx.fillStyle = t.net_pct >= 0 ? '#3fcf8e' : '#ef5d5d';
      ctx.beginPath(); ctx.moveTo(x, y - 16); ctx.lineTo(x - 6, y - 27);
      ctx.lineTo(x + 6, y - 27); ctx.closePath(); ctx.fill();
    }
    // stop / target rails while the trade is live
    if (open && t.entry_index < cursor) {
      const x0 = s.x(Math.max(t.entry_index, s.start)), x1 = L.w - L.padR;
      for (const [price, colour] of [[t.stop, 'rgba(239,93,93,.8)'],
                                     [t.target, 'rgba(63,207,142,.8)']]) {
        if (price < s.lo || price > s.hi) continue;
        const y = Math.round(s.y(price)) + .5;
        ctx.strokeStyle = colour; ctx.setLineDash([3, 3]);
        ctx.beginPath(); ctx.moveTo(x0, y); ctx.lineTo(x1, y); ctx.stroke();
        ctx.setLineDash([]);
      }
    }
    // completed trades get a tinted span
    if (!open && t.exit_index >= s.start) {
      const x0 = s.x(Math.max(t.entry_index, s.start)), x1 = s.x(t.exit_index);
      ctx.fillStyle = t.net_pct >= 0 ? 'rgba(63,207,142,.07)' : 'rgba(239,93,93,.07)';
      ctx.fillRect(x0, L.priceTop, Math.max(1, x1 - x0), L.priceBot - L.priceTop);
    }
  }
}

function oscillator(s) {
  const series = D.rsi, top = L.oscTop, bot = L.oscBot;
  ctx.strokeStyle = '#1b2420';
  ctx.strokeRect(L.padL, top, L.plotW, bot - top);
  const y = v => bot - (v / 100) * (bot - top);
  for (const [v, colour] of [[70, 'rgba(239,93,93,.45)'], [30, 'rgba(63,207,142,.45)']]) {
    const yy = Math.round(y(v)) + .5;
    ctx.strokeStyle = colour; ctx.setLineDash([4, 4]);
    ctx.beginPath(); ctx.moveTo(L.padL, yy); ctx.lineTo(L.w - L.padR, yy); ctx.stroke();
    ctx.setLineDash([]);
    ctx.fillStyle = colour; ctx.font = '10px ui-monospace,monospace';
    ctx.textAlign = 'left'; ctx.textBaseline = 'middle';
    ctx.fillText(String(v), L.w - L.padR + 7, yy);
  }
  ctx.strokeStyle = '#b98cff'; ctx.lineWidth = 1.4; ctx.beginPath();
  let started = false;
  for (let i = s.start; i < s.end; i++) {
    const v = series[i];
    if (v === null || v === undefined) { started = false; continue; }
    const x = s.x(i), yy = y(v);
    if (!started) { ctx.moveTo(x, yy); started = true; } else ctx.lineTo(x, yy);
  }
  ctx.stroke(); ctx.lineWidth = 1;
  ctx.fillStyle = '#7d8f85'; ctx.textAlign = 'left'; ctx.textBaseline = 'top';
  ctx.fillText('RSI(14)', L.padL + 4, top + 3);
}

function crosshair(s) {
  if (hover === null || hover < s.start || hover >= s.end) { tip.style.display = 'none'; return; }
  const b = bars[hover], x = Math.round(s.x(hover)) + .5;
  ctx.strokeStyle = 'rgba(232,240,234,.22)'; ctx.setLineDash([3, 3]);
  ctx.beginPath(); ctx.moveTo(x, L.priceTop); ctx.lineTo(x, L.volBot); ctx.stroke();
  ctx.setLineDash([]);
  const rsi = D.rsi[hover], wh = D.whale[hover];
  const t = tradeByEntry.get(hover), tx = tradeByExit.get(hover);
  const rows = [
    fmtTime(b.ts) + ' UTC',
    'O ' + fmtP(b.o) + '   H ' + fmtP(b.h),
    'L ' + fmtP(b.l) + '   C ' + fmtP(b.c),
    'vol ' + b.v.toLocaleString(undefined,{maximumFractionDigits:2}),
    'RSI ' + (rsi === null ? '—' : rsi.toFixed(1)) +
      '   whale ' + (wh === null || wh === undefined ? '—' : wh.toFixed(1)),
  ];
  if (signalSet.has(hover)) rows.push('▸ conditions fired here');
  if (t)  rows.push('▲ trade #' + t.n + ' opened at ' + fmtP(t.entry));
  if (tx) rows.push('▼ trade #' + tx.n + ' closed (' + tx.reason + ') ' +
                    tx.net_pct.toFixed(2) + '%');
  tip.textContent = rows.join('\n');
  tip.style.display = 'block';
  const box = tip.getBoundingClientRect();
  let left = s.x(hover) + 14;
  if (left + box.width > L.w - 8) left = s.x(hover) - box.width - 14;
  tip.style.left = Math.max(4, left) + 'px';
  tip.style.top = (L.priceTop + 8) + 'px';
}

function draw() {
  layout();
  ctx.clearRect(0, 0, L.w, L.h);
  const s = scales();
  grid(s);
  marks(s);                 // spans behind the candles
  candles(s);
  line(s, D.ema20, 'rgba(90,169,255,.85)');
  line(s, D.ema50, 'rgba(240,180,41,.75)');
  levels(s);
  oscillator(s);
  crosshair(s);
  paintPnl();
}

/* ---------------------------------------------------------------- panels */
function drawEquity(closedPnls) {
  const eq = document.getElementById('eq');
  const ec = eq.getContext('2d');
  const dpr = window.devicePixelRatio || 1;
  const w = eq.clientWidth || 240, h = 56;
  eq.width = w * dpr; eq.height = h * dpr;
  ec.setTransform(dpr, 0, 0, dpr, 0, 0);
  ec.clearRect(0, 0, w, h);

  // cumulative realised P&L, one step per closed trade
  const pts = [0];
  for (const p of closedPnls) pts.push(pts[pts.length - 1] + p);
  const lo = Math.min(...pts, 0), hi = Math.max(...pts, 0);
  const span = (hi - lo) || 1;
  const x = i => (pts.length < 2 ? 0 : i / (pts.length - 1) * (w - 2)) + 1;
  const y = v => h - 4 - (v - lo) / span * (h - 8);

  const zero = Math.round(y(0)) + .5;
  ec.strokeStyle = 'rgba(232,240,234,.18)'; ec.setLineDash([3, 3]);
  ec.beginPath(); ec.moveTo(0, zero); ec.lineTo(w, zero); ec.stroke();
  ec.setLineDash([]);

  if (pts.length < 2) {
    ec.fillStyle = '#7d8f85'; ec.font = '11px ui-monospace,monospace';
    ec.textAlign = 'left'; ec.textBaseline = 'middle';
    ec.fillText('equity curve — no closed trades yet', 2, h / 2);
    return;
  }

  const last = pts[pts.length - 1];
  const colour = last >= 0 ? '#3fcf8e' : '#ef5d5d';
  ec.beginPath(); ec.moveTo(x(0), y(pts[0]));
  for (let i = 1; i < pts.length; i++) ec.lineTo(x(i), y(pts[i]));
  ec.strokeStyle = colour; ec.lineWidth = 1.6; ec.stroke();

  ec.lineTo(x(pts.length - 1), zero); ec.lineTo(x(0), zero); ec.closePath();
  ec.fillStyle = last >= 0 ? 'rgba(63,207,142,.12)' : 'rgba(239,93,93,.12)';
  ec.fill();

  ec.fillStyle = colour;
  ec.beginPath(); ec.arc(x(pts.length - 1), y(last), 2.6, 0, Math.PI * 2); ec.fill();
}

function paintPnl() {
  let realised = 0, closed = 0, wins = 0, openPnl = 0, openTrade = null;
  const closedPnls = [];
  for (const t of D.trades) {
    if (t.exit_index < cursor) {
      realised += t.pnl; closed++; if (t.net_pct > 0) wins++;
      closedPnls.push(t.pnl);
    } else if (t.entry_index < cursor) {
      openTrade = t;
      const now = bars[Math.min(cursor - 1, N - 1)].c;
      const move = t.direction === 'long' ? (now - t.entry) : (t.entry - now);
      openPnl = 1000 * (move / t.entry * 100 - 0.30) / 100;   // same costs as the run
    }
  }
  const total = realised + openPnl;
  const el = id => document.getElementById(id);
  el('pnlTotal').textContent = fmtMoney(total);
  el('pnlTotal').className = 'big ' + cls(total);
  el('pnlReal').textContent = fmtMoney(realised);
  el('pnlReal').className = cls(realised);
  el('pnlOpen').textContent = openTrade ? fmtMoney(openPnl) + '  (#' + openTrade.n + ' live)' : '—';
  el('pnlOpen').className = openTrade ? cls(openPnl) : 'dim';
  el('pnlCount').textContent = closed;
  el('pnlHit').textContent = closed ? (wins / closed * 100).toFixed(0) + '%' : '—';
  el('pnlMode').textContent = cursor >= N ? '(full window)' : '(at ' + fmtTime(bars[cursor-1].ts) + ')';
  const v = visible();
  el('bPos').textContent = cursor + ' / ' + N + ' bars · showing ' +
    (v.end - v.start) + (follow ? '' : ' (panned)');
  el('bScrub').value = cursor;
  drawEquity(closedPnls);
}

function paintStatic() {
  const el = id => document.getElementById(id);
  el('hProduct').textContent = D.product;
  el('hTf').textContent = D.timeframe + ' bars · ' + N + ' loaded · ' + D.generated;
  el('hBrief').textContent = D.brief;
  document.title = D.product + ' ' + D.timeframe + ' — Tapedeck';

  const chips = D.conditions.map(c => '<div class="chip"><b>■</b> ' + esc(c) + '</div>');
  if (!D.conditions.length) chips.push('<div class="chip">no conditions — chart only</div>');
  el('hChips').innerHTML = chips.join('');

  const st = D.stats || {};
  if (st.trades) {
    el('stNet').textContent = (st.total_pct >= 0 ? '+' : '') + st.total_pct.toFixed(2) + '%';
    el('stNet').className = 'big ' + cls(st.total_pct);
    el('stTrades').textContent = st.trades + ' (' + st.wins + 'W / ' + st.losses + 'L)';
    el('stHit').textContent = st.hit_rate.toFixed(1) + '%';
    el('stAvg').textContent = st.avg_pct.toFixed(2) + '%';
    el('stBW').textContent = st.best_pct.toFixed(2) + '% / ' + st.worst_pct.toFixed(2) + '%';
    el('stPF').textContent = st.profit_factor === null ? 'no losers' : st.profit_factor.toFixed(2);
    el('stDD').textContent = fmtMoney(-st.max_drawdown);
  } else {
    el('stNet').textContent = 'no trades';
    el('stNet').className = 'big dim';
  }

  el('lvList').innerHTML = D.levels.length
    ? D.levels.map(lv => '<div class="kv"><span>' + lv.kind + '</span><span>' +
        fmtP(lv.price) + ' <span class="dim">x' + lv.touches + '</span></span></div>').join('')
    : '<div class="dim">none found in this window</div>';

  el('asList').innerHTML = Object.entries(D.assumptions || {}).length
    ? Object.entries(D.assumptions).map(([k, v]) =>
        '<div class="kv"><span>' + esc(k.replace(/_/g, ' ')) + '</span><span style="text-align:right;max-width:60%">' +
        esc(String(v)) + '</span></div>').join('')
    : '<div class="dim">chart only — no strategy was run</div>';

  el('blBody').innerHTML = D.trades.length ? D.trades.map(t =>
    '<tr><td>' + t.n + '</td><td>' + fmtTime(t.signal_ts) + '</td><td>' + fmtP(t.entry) +
    '</td><td>' + fmtP(t.exit) + '</td><td>' + t.reason + '</td><td class="n">' +
    t.bars_held + '</td><td class="n ' + cls(t.net_pct) + '">' + t.net_pct.toFixed(2) +
    '</td><td class="n ' + cls(t.pnl) + '">' + fmtMoney(t.pnl) + '</td></tr>').join('')
    : '<tr><td colspan="8" class="dim">no trades in this window</td></tr>';
  el('blCount').textContent = D.trades.length ? '(' + D.trades.length + ')' : '';

  el('cvList').innerHTML = (CAVEATS || []).concat(D.notes.map(n => 'brief: ' + n))
    .map(c => '<li>' + esc(c) + '</li>').join('');

  el('foot').innerHTML =
    'Tapedeck · spot market data, read-only · no orders are placed by this page or the tool that wrote it.<br>' +
    'Nothing here is financial advice. Numbers describe past bars under the stated assumptions.';

  const scrub = el('bScrub');
  scrub.max = N; scrub.value = N;
  if (D.replay_bars && D.replay_bars < N) el('pnlNote').textContent =
    'Brief asked for the last ' + D.replay_bars + ' bars — press Replay to walk them.';
}

const esc = s => String(s).replace(/[&<>"]/g, c =>
  ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));

/* ---------------------------------------------------------------- controls */
function setCursor(v) {
  cursor = Math.max(1, Math.min(N, v));
  if (follow) right = cursor; else clampPan();
  draw();
  if (cursor >= N) stop();
}
function play() {
  if (cursor >= N) { cursor = Math.max(1, N - (D.replay_bars || view)); follow = true; }
  playing = true;
  document.getElementById('bPlay').textContent = '❚❚ Pause';
  document.getElementById('bPlay').classList.add('on');
  tick();
}
function stop() {
  playing = false;
  if (timer) { clearTimeout(timer); timer = null; }
  document.getElementById('bPlay').textContent = '▶ Replay';
  document.getElementById('bPlay').classList.remove('on');
}
function tick() {
  if (!playing) return;
  setCursor(cursor + 1);
  if (cursor < N) {
    const speed = Number(document.getElementById('bSpeed').value);
    timer = setTimeout(tick, 240 / speed);
  }
}

document.getElementById('bPlay').onclick = () => playing ? stop() : play();
document.getElementById('bStep').onclick = () => { stop(); setCursor(cursor + 1); };
document.getElementById('bEnd').onclick  = () => {
  stop(); follow = true; view = Math.min(200, N); setCursor(N);
};
document.getElementById('bScrub').oninput = e => { stop(); setCursor(Number(e.target.value)); };

function barAt(clientX) {
  const rect = cv.getBoundingClientRect(), s = scales();
  const i = Math.round((clientX - rect.left - L.padL - s.cw / 2) / s.cw) + s.start;
  return (i >= s.start && i < s.end) ? i : null;
}

cv.addEventListener('mousedown', e => {
  drag = {x: e.clientX, right: follow ? cursor : right};
  cv.style.cursor = 'grabbing';
});
window.addEventListener('mouseup', () => { drag = null; cv.style.cursor = 'crosshair'; });

cv.addEventListener('mousemove', e => {
  if (drag) {
    // drag right = walk back in time
    const moved = (e.clientX - drag.x) / Math.max(scales().cw, 0.5);
    const next = Math.round(drag.right - moved);
    if (next !== right || follow) { follow = false; right = next; clampPan(); }
    hover = null;
    draw();
    return;
  }
  hover = barAt(e.clientX);
  draw();
});
cv.addEventListener('mouseleave', () => { hover = null; draw(); });

cv.addEventListener('wheel', e => {
  e.preventDefault();
  const anchor = barAt(e.clientX);
  const before = view;
  view = Math.max(30, Math.min(N, Math.round(view * (e.deltaY > 0 ? 1.18 : 0.85))));
  if (view === before) return;
  if (anchor !== null && !follow) {
    // keep the bar under the pointer roughly where it was
    const frac = (anchor - (right - before)) / before;
    right = Math.round(anchor + (1 - frac) * view);
    clampPan();
  }
  draw();
}, {passive: false});

cv.addEventListener('dblclick', () => { follow = true; view = Math.min(200, N); draw(); });

window.addEventListener('resize', draw);
window.addEventListener('keydown', e => {
  if (e.key === ' ') { e.preventDefault(); playing ? stop() : play(); }
  if (e.key === 'ArrowRight') { stop(); setCursor(cursor + 1); }
  if (e.key === 'ArrowLeft')  { stop(); setCursor(cursor - 1); }
  if (e.key === 'Home') { follow = true; view = Math.min(200, N); draw(); }
});

paintStatic();
draw();
</script>
</body></html>
"""

INDEX_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Tapedeck — scan results</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{background:#0a0e0c;color:#e8f0ea;font:14px/1.5 ui-monospace,SFMono-Regular,Menlo,
  Consolas,"Liberation Mono",monospace;padding:26px}
.wrap{max-width:1000px;margin:0 auto}
h1{font-size:19px;margin-bottom:4px}h1 span{color:#c8f542}
.sub{color:#7d8f85;font-size:13px;margin-bottom:18px}
.brief{color:#7d8f85;font-size:13px;border-left:2px solid #c8f542;padding-left:10px;
  margin-bottom:20px}
table{width:100%;border-collapse:collapse;background:#0f1512;border:1px solid #1b2420;
  border-radius:10px;overflow:hidden}
th{text-align:left;font-size:11px;letter-spacing:.1em;text-transform:uppercase;
  color:#7d8f85;padding:10px;border-bottom:1px solid #1b2420}
td{padding:10px;border-bottom:1px solid rgba(27,36,32,.6)}
td.n,th.n{text-align:right}
a{color:#c8f542;text-decoration:none}a:hover{text-decoration:underline}
footer{color:#7d8f85;font-size:11px;margin-top:20px;line-height:1.7}
</style></head><body><div class="wrap">
<h1><span>■</span> Tapedeck — __COUNT__ market(s) charted</h1>
<div class="sub">__GENERATED__</div>
<div class="brief">asked: __BRIEF__</div>
<table>
<thead><tr><th>market</th><th>tf</th><th class="n">hits</th><th class="n">hit rate</th>
<th class="n">net</th><th>last fired (UTC)</th></tr></thead>
<tbody>
__ROWS__
</tbody></table>
<footer>Spot market data, read-only. No orders are placed. Backtest figures are
theoretical, include costs, and are not a forecast. Not financial advice.</footer>
</div></body></html>
"""
