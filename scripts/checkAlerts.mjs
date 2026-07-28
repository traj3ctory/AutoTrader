import fs from "node:fs";

// Free workaround for TradingView's paid alert limit: poll Bybit's public
// ticker feed (same endpoint scanMovers.mjs uses, no auth) and compare
// against the trigger levels already mapped in SETUP_LEDGER.json. Reports
// only levels that were CROSSED since the last run (previous price and
// current price on opposite sides of the level) - not just "near" a level.

const ledgerPath = new URL("../SETUP_LEDGER.json", import.meta.url);
const statePath = new URL("../.alert_state.json", import.meta.url);

const ledger = JSON.parse(fs.readFileSync(ledgerPath, "utf8"));
const prevState = fs.existsSync(statePath)
  ? JSON.parse(fs.readFileSync(statePath, "utf8"))
  : {};

const res = await fetch("https://api.bybit.com/v5/market/tickers?category=linear");
const data = await res.json();
if (data.retCode !== 0) {
  console.error("Bybit API error:", data.retMsg);
  process.exit(1);
}
const priceBySymbol = new Map(
  data.result.list.map((t) => [t.symbol, Number(t.lastPrice)])
);

// Once a position is actually confirmed open, entry/reclaim/zone levels are
// no longer useful triggers - the user already acted on those. Only SL/TP
// crossings matter for managing a live position; entry-style levels would
// just be noise ("price moved through the zone you already bought").
const OPEN_POSITION_STATUSES = new Set(["ENTERED LONG", "ENTERED SHORT", "UR PROFIT", "UR LOSS"]);

function levelsFor(coin, setup) {
  const levels = [];
  const isOpenPosition = OPEN_POSITION_STATUSES.has(setup.position_status);

  if (typeof setup.sl === "number") {
    levels.push({ label: "SL", price: setup.sl });
  }
  if (Array.isArray(setup.tp)) {
    setup.tp.forEach((tp, i) => {
      if (typeof tp === "number") levels.push({ label: `TP${i + 1}`, price: tp });
    });
  }

  if (isOpenPosition) return levels; // skip entry/reclaim/zone triggers - already in the trade

  if (typeof setup.reclaim === "number") {
    levels.push({ label: "RECLAIM", price: setup.reclaim });
  }
  if (setup.watch_zone && typeof setup.watch_zone === "object") {
    if (typeof setup.watch_zone.low === "number") {
      levels.push({ label: `${setup.watch_zone.label || "ZONE"} low`, price: setup.watch_zone.low });
    }
    if (typeof setup.watch_zone.high === "number") {
      levels.push({ label: `${setup.watch_zone.label || "ZONE"} high`, price: setup.watch_zone.high });
    }
  }
  if (setup.entry && typeof setup.entry === "object") {
    if (typeof setup.entry.low === "number") {
      levels.push({ label: "ENTRY low", price: setup.entry.low });
    }
    if (typeof setup.entry.high === "number") {
      levels.push({ label: "ENTRY high", price: setup.entry.high });
    }
  }
  return levels;
}

// Context-only coins (currently just BTC) are never trade candidates - no
// entry/SL/TP, just key S/R levels for early warning that a market-wide move
// may be coming before it cascades through the tradeable coins' own alerts.
function levelsForContext(entry) {
  const levels = [];
  for (const field of ["key_resistance", "key_support", "deeper_support"]) {
    const zone = entry[field];
    if (zone && typeof zone === "object") {
      if (typeof zone.low === "number") levels.push({ label: `${zone.label || field} low`, price: zone.low });
      if (typeof zone.high === "number") levels.push({ label: `${zone.label || field} high`, price: zone.high });
    }
  }
  return levels;
}

const crossings = [];
const newState = {};
const firstRun = Object.keys(prevState).length === 0;

for (const [coin, setup] of Object.entries(ledger.setups || {})) {
  const symbol = coin.replace(/\.P$/, "");
  const currPrice = priceBySymbol.get(symbol);
  if (currPrice === undefined) continue;

  const prevPrice = prevState[coin];
  newState[coin] = currPrice;

  if (firstRun || prevPrice === undefined) continue; // no baseline yet, skip detection this run

  for (const level of levelsFor(coin, setup)) {
    const wasBelow = prevPrice < level.price;
    const isBelow = currPrice < level.price;
    if (wasBelow !== isBelow) {
      const direction = wasBelow ? "crossed UP through" : "crossed DOWN through";
      crossings.push(
        `${coin}: ${direction} ${level.label} (${level.price}) — now ${currPrice} (was ${prevPrice})`
      );
    }
  }
}

for (const [coin, entry] of Object.entries(ledger.context_watch || {})) {
  const symbol = coin.replace(/\.P$/, "");
  const currPrice = priceBySymbol.get(symbol);
  if (currPrice === undefined) continue;

  const prevPrice = prevState[coin];
  newState[coin] = currPrice;

  if (firstRun || prevPrice === undefined) continue;

  for (const level of levelsForContext(entry)) {
    const wasBelow = prevPrice < level.price;
    const isBelow = currPrice < level.price;
    if (wasBelow !== isBelow) {
      const direction = wasBelow ? "crossed UP through" : "crossed DOWN through";
      crossings.push(
        `${coin} (context): ${direction} ${level.label} (${level.price}) — now ${currPrice} (was ${prevPrice}) - market-wide move possible, check the tradeable coins`
      );
    }
  }
}

fs.writeFileSync(statePath, JSON.stringify(newState, null, 2) + "\n");

if (firstRun) {
  console.log("First run - baseline prices saved, no crossings can be detected yet. Next run onward will report crossings.");
} else if (crossings.length === 0) {
  console.log("No triggers crossed since last check.");
} else {
  console.log(`${crossings.length} trigger(s) crossed:\n`);
  crossings.forEach((line) => console.log(" - " + line));
}
