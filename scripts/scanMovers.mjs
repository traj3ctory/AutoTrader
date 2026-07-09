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

const rows = data.result.list
  .filter((t) => t.symbol.endsWith("USDT"))
  .filter((t) => !EXCLUDE.has(t.symbol))
  .filter((t) => Number(t.turnover24h) >= MIN_TURNOVER_USD)
  .map((t) => ({
    symbol: t.symbol,
    ticker: `${t.symbol}.P`,
    pct: Number(t.price24hPcnt) * 100,
    turnover: Number(t.turnover24h),
    lastPrice: Number(t.lastPrice),
    alreadyActive: ACTIVE.has(`${t.symbol}.P`),
  }));

const gainers = rows
  .filter((r) => r.pct > 0)
  .sort((a, b) => b.pct - a.pct)
  .slice(0, TOP_N);

const losers = rows
  .filter((r) => r.pct < 0)
  .sort((a, b) => a.pct - b.pct)
  .slice(0, TOP_N);

const fmt = (r) =>
  `${r.ticker.padEnd(16)} ${r.pct >= 0 ? "+" : ""}${r.pct.toFixed(2)}%  turnover $${(r.turnover / 1e6).toFixed(1)}M  price ${r.lastPrice}${r.alreadyActive ? "  [already in ledger]" : ""}`;

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
  `Filters: USDT perps only, BTC/ETH excluded (market filters not candidates), min $${(MIN_TURNOVER_USD / 1e6).toFixed(0)}M 24h turnover.`,
  "This is a candidate shortlist only. No analysis, ledger writes, or chart drawing happens here — run `Analyze [coin]` on whichever ones look worth a real read.",
];

const output = lines.join("\n");
console.log(output);

const outPath = new URL("../MOVER_SCAN.md", import.meta.url);
fs.writeFileSync(outPath, output + "\n");
