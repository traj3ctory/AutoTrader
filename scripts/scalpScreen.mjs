// Fast, objective pre-screen for Scalp-type Analyze passes, run BEFORE the
// TradingView structural/visual read. Pulls Bybit public kline data (no
// auth) and computes the numeric side of standard scalper criteria that
// ANALYZE_PROMPT.md didn't previously cover: VWAP directional bias, 9 EMA
// trend/pullback reference, 4H ATR% (for SL buffer calibration), nearby 4H
// pivot supply/demand, and a directional-efficiency score that replaces
// eyeballing "orderly trend vs chop" with a real number.
//
// This does NOT replace the TradingView chart read or the source-of-truth
// hierarchy in ANALYZE_PROMPT.md - it only decides, cheaply, whether a scalp
// candidate clears the objective gates before spending a chart pass on it.
// TradingView still does the final structural zone confirmation and Pine
// rendering.
//
// Gates (hard, per user decision 2026-07-30): a coin fails a gate = capped
// at Watch Only for that side, same severity class as the existing HTF veto.
//   - VWAP: no long below 24h rolling VWAP, no short above it.
//   - Directional efficiency (1H, last 8 candles): < 0.4 = CHOPPY, scalp
//     entries capped at Watch Only regardless of structure (objective
//     version of the Candle-Shape-Judgment Rule).
//
// Usage: node scripts/scalpScreen.mjs HYPEUSDT XRPUSDT DOGEUSDT

const EFFICIENCY_GATE = 0.4;

async function fetchKline(symbol, interval, limit = 150) {
  const url = `https://api.bybit.com/v5/market/kline?category=linear&symbol=${symbol}&interval=${interval}&limit=${limit}`;
  const res = await fetch(url);
  const data = await res.json();
  if (data.retCode !== 0) throw new Error(`${symbol} ${interval}: ${data.retMsg}`);
  return data.result.list
    .slice()
    .reverse()
    .map(([t, o, h, l, c, v]) => ({
      t: Number(t), o: Number(o), h: Number(h), l: Number(l), c: Number(c), v: Number(v),
    }));
}

function atr(candles, period = 14) {
  const trs = [];
  for (let i = 1; i < candles.length; i++) {
    const { h, l } = candles[i];
    const pc = candles[i - 1].c;
    trs.push(Math.max(h - l, Math.abs(h - pc), Math.abs(l - pc)));
  }
  if (trs.length < period) return null;
  return trs.slice(-period).reduce((a, b) => a + b, 0) / period;
}

function ema(values, period) {
  if (values.length < period) return null;
  const k = 2 / (period + 1);
  let e = values.slice(0, period).reduce((a, b) => a + b, 0) / period;
  for (let i = period; i < values.length; i++) e = values[i] * k + e * (1 - k);
  return e;
}

// Full EMA series (not just the final value) - needed to detect crossovers and slope.
function emaSeries(values, period) {
  if (values.length < period) return [];
  const k = 2 / (period + 1);
  const out = new Array(values.length).fill(null);
  let e = values.slice(0, period).reduce((a, b) => a + b, 0) / period;
  out[period - 1] = e;
  for (let i = period; i < values.length; i++) {
    e = values[i] * k + e * (1 - k);
    out[i] = e;
  }
  return out;
}

// 9/20 EMA cross + slope, used as the required entry trigger once price is
// already reacting at a mapped zone (per ANALYZE_PROMPT.md's Scalp Entry
// Trigger rule) - never a standalone signal, since a bare EMA cross in open
// air is exactly the whipsaw-prone setup the efficiency gate exists to block.
function emaCrossSignal(candles, lookback = 3) {
  const closes = candles.map((c) => c.c);
  const e9 = emaSeries(closes, 9);
  const e20 = emaSeries(closes, 20);
  const n = closes.length;
  if (!e9[n - 1] || !e20[n - 1] || !e9[n - 1 - lookback] || !e20[n - 1 - lookback]) {
    return { cross: "N/A", slope: "N/A" };
  }
  let cross = "NONE";
  for (let i = n - lookback; i < n; i++) {
    if (e9[i] == null || e20[i] == null || e9[i - 1] == null || e20[i - 1] == null) continue;
    if (e9[i - 1] <= e20[i - 1] && e9[i] > e20[i]) cross = "BULLISH_CROSS";
    if (e9[i - 1] >= e20[i - 1] && e9[i] < e20[i]) cross = "BEARISH_CROSS";
  }
  const slopeVal = e9[n - 1] - e9[n - 1 - lookback];
  const slope = slopeVal > 0 ? "UP" : slopeVal < 0 ? "DOWN" : "FLAT";
  return { cross, slope, ema9: e9[n - 1], ema20: e20[n - 1] };
}

function pivots(candles, lookback = 2, window = 40) {
  const recent = candles.slice(-window);
  const highs = [], lows = [];
  for (let i = lookback; i < recent.length - lookback; i++) {
    const seg = recent.slice(i - lookback, i + lookback + 1);
    if (recent[i].h === Math.max(...seg.map((c) => c.h))) highs.push(recent[i].h);
    if (recent[i].l === Math.min(...seg.map((c) => c.l))) lows.push(recent[i].l);
  }
  return {
    highs: [...new Set(highs.map((h) => +h.toFixed(6)))].sort((a, b) => b - a),
    lows: [...new Set(lows.map((l) => +l.toFixed(6)))].sort((a, b) => a - b),
  };
}

function directionalEfficiency(candles, n = 8) {
  const seg = candles.slice(-n);
  const netMove = Math.abs(seg[seg.length - 1].c - seg[0].o);
  const totalRange = seg.reduce((sum, c) => sum + (c.h - c.l), 0);
  return totalRange > 0 ? netMove / totalRange : 0;
}

// Session-anchored VWAP (resets 00:00 UTC daily), matching the "VWAP resets
// every day" rule - NOT a rolling window. Computed on the signal timeframe
// (5m) per the corrected Scalp Entry Rule (2026-08-03: this was previously a
// 24h rolling average on 1H candles, a real bug - fixed here).
function sessionVwap(candles5m) {
  const now = candles5m[candles5m.length - 1].t;
  const dayStart = Math.floor(now / 86400000) * 86400000;
  const seg = candles5m.filter((c) => c.t >= dayStart);
  if (!seg.length) return null;
  const num = seg.reduce((sum, c) => sum + ((c.h + c.l + c.c) / 3) * c.v, 0);
  const den = seg.reduce((sum, c) => sum + c.v, 0);
  return den > 0 ? num / den : null;
}

async function screen(symbol) {
  const [c4h, c1h, c15m, c5m] = await Promise.all([
    fetchKline(symbol, "240"),
    fetchKline(symbol, "60"),
    fetchKline(symbol, "15"),
    fetchKline(symbol, "5"),
  ]);

  const price = c5m[c5m.length - 1].c;
  const a4h = atr(c4h, 14);
  const { highs, lows } = pivots(c4h, 2, 40);
  const nearSupply = highs.filter((h) => h > price).slice(-3).reverse();
  const nearDemand = lows.filter((l) => l < price).slice(-3);
  const ema9_1h = ema(c1h.map((c) => c.c), 9);
  const vwap = sessionVwap(c5m);
  const effLong = directionalEfficiency(c1h, 8);

  // Signal timeframe is 5m, per the corrected Scalp Entry Rule (4H trend ->
  // 1H zone -> 15m refinement -> 5m EMA/VWAP/entry). 15m is zone-refinement
  // only and never produces the cross itself.
  const signal = emaCrossSignal(c5m, 3);

  const vwapBias = vwap == null ? "N/A" : price > vwap ? "LONG-OK" : "SHORT-OK";
  const effGate = effLong >= EFFICIENCY_GATE ? "TRENDING (pass)" : "CHOPPY (fail - Watch Only cap)";

  return {
    symbol, price,
    atr4hPct: a4h ? (a4h / price) * 100 : null,
    nearSupply, nearDemand,
    ema9_1h,
    priceVsEma1h: ema9_1h ? (price > ema9_1h ? "ABOVE" : "BELOW") : "N/A",
    vwap, vwapBias,
    directionalEfficiency: effLong,
    effGate,
    signal,
  };
}

const symbols = process.argv.slice(2);
if (symbols.length === 0) {
  console.error("Usage: node scripts/scalpScreen.mjs SYMBOL [SYMBOL...]");
  process.exit(1);
}

for (const symbol of symbols) {
  const r = await screen(symbol);
  console.log(`\n===== ${r.symbol} =====`);
  console.log(`Price: ${r.price}`);
  console.log(`4H ATR%: ${r.atr4hPct?.toFixed(2)}%  (SL buffer basis: ~50% of this beyond structure)`);
  console.log(`Session VWAP (00:00 UTC reset): ${r.vwap?.toFixed(6)}  -> GATE: ${r.vwapBias}`);
  console.log(`9 EMA 1H (trend reference only): ${r.ema9_1h?.toFixed(6)} (price ${r.priceVsEma1h})`);
  console.log(`Directional efficiency (1H, 8c): ${r.directionalEfficiency.toFixed(2)} -> GATE: ${r.effGate}`);
  console.log(`5m EMA 9/20 (SIGNAL TIMEFRAME): cross=${r.signal.cross}, slope=${r.signal.slope}`);
  console.log(`  -> Entry trigger valid ONLY if this 5m cross occurred at/immediately after a reaction at the 15m-refined zone. A bare cross with no zone is not a signal.`);
  console.log(`Nearest 4H supply: ${r.nearSupply.join(", ") || "none in window"}`);
  console.log(`Nearest 4H demand: ${r.nearDemand.join(", ") || "none in window"}`);
}
