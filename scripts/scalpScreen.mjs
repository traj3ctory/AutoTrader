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

function vwap24h(candles) {
  const seg = candles.slice(-24);
  const num = seg.reduce((sum, c) => sum + ((c.h + c.l + c.c) / 3) * c.v, 0);
  const den = seg.reduce((sum, c) => sum + c.v, 0);
  return den > 0 ? num / den : null;
}

async function screen(symbol) {
  const [c4h, c1h, c15m] = await Promise.all([
    fetchKline(symbol, "240"),
    fetchKline(symbol, "60"),
    fetchKline(symbol, "15"),
  ]);

  const price = c15m[c15m.length - 1].c;
  const a4h = atr(c4h, 14);
  const { highs, lows } = pivots(c4h, 2, 40);
  const nearSupply = highs.filter((h) => h > price).slice(-3).reverse();
  const nearDemand = lows.filter((l) => l < price).slice(-3);
  const ema9_1h = ema(c1h.map((c) => c.c), 9);
  const ema9_15m = ema(c15m.map((c) => c.c), 9);
  const vwap = vwap24h(c1h);
  const effLong = directionalEfficiency(c1h, 8);

  const vwapBias = vwap == null ? "N/A" : price > vwap ? "LONG-OK" : "SHORT-OK";
  const effGate = effLong >= EFFICIENCY_GATE ? "TRENDING (pass)" : "CHOPPY (fail - Watch Only cap)";

  return {
    symbol, price,
    atr4hPct: a4h ? (a4h / price) * 100 : null,
    nearSupply, nearDemand,
    ema9_1h, ema9_15m,
    priceVsEma1h: ema9_1h ? (price > ema9_1h ? "ABOVE" : "BELOW") : "N/A",
    vwap, vwapBias,
    directionalEfficiency: effLong,
    effGate,
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
  console.log(`VWAP (24h): ${r.vwap?.toFixed(6)}  -> GATE: ${r.vwapBias}`);
  console.log(`9 EMA 1H: ${r.ema9_1h?.toFixed(6)} (price ${r.priceVsEma1h})  | 9 EMA 15m: ${r.ema9_15m?.toFixed(6)}`);
  console.log(`Directional efficiency (1H, 8c): ${r.directionalEfficiency.toFixed(2)} -> GATE: ${r.effGate}`);
  console.log(`Nearest 4H supply: ${r.nearSupply.join(", ") || "none in window"}`);
  console.log(`Nearest 4H demand: ${r.nearDemand.join(", ") || "none in window"}`);
}
