import fs from "node:fs";

const ledgerPath = new URL("../SETUP_LEDGER.json", import.meta.url);
const ledger = JSON.parse(fs.readFileSync(ledgerPath, "utf8"));

const ACTIVE = new Set(Object.keys(ledger.setups || {}));
const EXCLUDE = new Set(["BTCUSDT", "ETHUSDT"]); // market filters, not candidates
const TOP_N = 10;
const MIN_TURNOVER_USD = 3_000_000; // filter out illiquid/thin symbols

const res = await fetch("https://api.bybit.com/v5/market/tickers?category=linear");
const data = await res.json();
if (data.retCode !== 0) {
  console.error("Bybit API error:", data.retMsg);
  process.exit(1);
}

const RANGE_PCT_MIN = 8; // flag symbols whose 24h high-low span is at least this % of price
const NET_TO_RANGE_MAX = 0.6; // net 24h move must be under this fraction of the range (i.e. it round-tripped)

const rows = data.result.list
  .filter((t) => t.symbol.endsWith("USDT"))
  .filter((t) => !EXCLUDE.has(t.symbol))
  .filter((t) => Number(t.turnover24h) >= MIN_TURNOVER_USD)
  .map((t) => {
    const lastPrice = Number(t.lastPrice);
    const high = Number(t.highPrice24h);
    const low = Number(t.lowPrice24h);
    const rangePct = lastPrice > 0 ? ((high - low) / lastPrice) * 100 : 0;
    return {
      symbol: t.symbol,
      ticker: `${t.symbol}.P`,
      pct: Number(t.price24hPcnt) * 100,
      turnover: Number(t.turnover24h),
      lastPrice,
      high,
      low,
      rangePct,
      alreadyActive: ACTIVE.has(`${t.symbol}.P`),
    };
  });

const gainers = rows
  .filter((r) => r.pct > 0)
  .sort((a, b) => b.pct - a.pct)
  .slice(0, TOP_N);

const losers = rows
  .filter((r) => r.pct < 0)
  .sort((a, b) => a.pct - b.pct)
  .slice(0, TOP_N);

// Catches structural intraday moves that 24h% misses: a coin can swing hard within
// the day (sweep low -> reclaim, or spike -> fade) and still net out flat/small on
// 24h%, so it never clears the gainers/losers cut despite a real, tradeable setup
// (this is what happened with FARTCOIN on 2026-07-28 - a dip-sweep-bounce with a
// real RR never showed up here because its 24h% was only -6.5%).
const sweepCandidates = rows
  .filter((r) => r.rangePct >= RANGE_PCT_MIN)
  .filter((r) => Math.abs(r.pct) <= r.rangePct * NET_TO_RANGE_MAX)
  .sort((a, b) => b.rangePct - a.rangePct)
  .slice(0, TOP_N);

const fmt = (r) =>
  `${r.ticker.padEnd(16)} ${r.pct >= 0 ? "+" : ""}${r.pct.toFixed(2)}%  turnover $${(r.turnover / 1e6).toFixed(1)}M  price ${r.lastPrice}${r.alreadyActive ? "  [already in ledger]" : ""}`;

const fmtSweep = (r) =>
  `${r.ticker.padEnd(16)} range ${r.rangePct.toFixed(1)}% (H ${r.high} / L ${r.low})  net ${r.pct >= 0 ? "+" : ""}${r.pct.toFixed(2)}%  turnover $${(r.turnover / 1e6).toFixed(1)}M  price ${r.lastPrice}${r.alreadyActive ? "  [already in ledger]" : ""}`;

const now = new Date().toISOString();
const lines = [
  `# Bybit mover scan — ${now}`,
  "",
  `## Top ${TOP_N} gainers (24h)`,
  ...gainers.map(fmt),
  "",
  `## Top ${TOP_N} losers (24h)`,
  ...losers.map(fmt),
  "",
  `## Intraday range movers (net 24h% small, but swung hard within the day)`,
  ...(sweepCandidates.length ? sweepCandidates.map(fmtSweep) : ["(none this run)"]),
  "",
  `Filters: USDT perps only, BTC/ETH excluded (market filters not candidates), min $${(MIN_TURNOVER_USD / 1e6).toFixed(0)}M 24h turnover.`,
  `Range-mover filters: 24h high-low span >= ${RANGE_PCT_MIN}% of price, net 24h% move <= ${NET_TO_RANGE_MAX * 100}% of that range (i.e. it round-tripped rather than trending).`,
  "This is a candidate shortlist only. No analysis, ledger writes, or chart drawing happens here — run `Analyze [coin]` on whichever ones look worth a real read.",
];

const output = lines.join("\n");
console.log(output);

const outPath = new URL("../MOVER_SCAN.md", import.meta.url);
fs.writeFileSync(outPath, output + "\n");
