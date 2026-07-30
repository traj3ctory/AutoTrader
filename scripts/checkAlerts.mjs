import fs from "node:fs";

// Free workaround for TradingView's paid alert limit: poll Bybit's public
// ticker/kline feed (same source scanMovers.mjs uses, no auth) and compare
// against the trigger levels already mapped in SETUP_LEDGER.json. Reports
// only levels that were CROSSED since the last run - not just "near" a level.
//
// Two noise-reduction passes on top of the original instant-ticker crossing:
//
// 1. Hysteresis band: a level only re-arms for the opposite direction once
//    price has cleared a small buffer past it. Chop that oscillates right at
//    a line (JTO/ZEC repeatedly this week) no longer fires a crossing every
//    30 minutes - it has to actually clear the line by ~0.25% each way.
// 2. Close-based confirmation for entry/reclaim/zone levels: these are
//    judged by candle closes per ANALYZE_PROMPT.md ("reclaims, retests, and
//    confirmations are judged by candle closes on the entry timeframe, not
//    wicks"), so the poller now uses the last CLOSED candle's close on the
//    coin's own trade-timeframe (1H Intraday / 5m Scalp) for those levels,
//    instead of the instantaneous ticker price. SL/TP and context_watch
//    levels still use live ticker price - a stop or a market-wide BTC level
//    is worth knowing about the instant it's touched, not on next close.

const ledgerPath = new URL("../SETUP_LEDGER.json", import.meta.url);
const statePath = new URL("../.alert_state.json", import.meta.url);

const HYSTERESIS_PCT = 0.0025; // 0.25% buffer each side of a level before it re-arms

const ledger = JSON.parse(fs.readFileSync(ledgerPath, "utf8"));
const prevState = fs.existsSync(statePath)
  ? JSON.parse(fs.readFileSync(statePath, "utf8"))
  : {};
const prevSides = prevState.levelSides || {};

const res = await fetch("https://api.bybit.com/v5/market/tickers?category=linear");
const data = await res.json();
if (data.retCode !== 0) {
  console.error("Bybit API error:", data.retMsg);
  process.exit(1);
}
const priceBySymbol = new Map(
  data.result.list.map((t) => [t.symbol, Number(t.lastPrice)])
);

// Bybit kline interval codes are plain minutes ("60" = 1H, "5" = 5m).
function klineIntervalFor(setup) {
  return setup.trade_type === "Scalp" ? "5" : "60";
}

const closeCache = new Map();
async function lastClosedCandleClose(symbol, interval) {
  const key = `${symbol}:${interval}`;
  if (closeCache.has(key)) return closeCache.get(key);
  try {
    const url = `https://api.bybit.com/v5/market/kline?category=linear&symbol=${symbol}&interval=${interval}&limit=2`;
    const r = await fetch(url);
    const j = await r.json();
    if (j.retCode !== 0 || !j.result?.list?.length) {
      closeCache.set(key, undefined);
      return undefined;
    }
    // list[0] is the most recent candle and may still be forming; list[1] is
    // the last candle guaranteed closed. Fall back to list[0] if only one
    // candle exists (new listing).
    const candle = j.result.list[1] || j.result.list[0];
    const close = Number(candle[4]);
    closeCache.set(key, close);
    return close;
  } catch {
    closeCache.set(key, undefined);
    return undefined;
  }
}

// Once a position is actually confirmed open, entry/reclaim/zone levels are
// no longer useful triggers - the user already acted on those. Only SL/TP
// crossings matter for managing a live position; entry-style levels would
// just be noise ("price moved through the zone you already bought").
const OPEN_POSITION_STATUSES = new Set(["ENTERED LONG", "ENTERED SHORT", "UR PROFIT", "UR LOSS"]);

function instantLevelsFor(setup) {
  // SL/TP: always instant-ticker, fires the moment price touches them.
  const levels = [];
  if (typeof setup.sl === "number") levels.push({ label: "SL", price: setup.sl });
  if (Array.isArray(setup.tp)) {
    setup.tp.forEach((tp, i) => {
      if (typeof tp === "number") levels.push({ label: `TP${i + 1}`, price: tp });
    });
  }
  return levels;
}

function closeConfirmedLevelsFor(setup) {
  // RECLAIM/ZONE/ENTRY: judged by candle close, not wick - skip entirely
  // once a position is open, same as before.
  if (OPEN_POSITION_STATUSES.has(setup.position_status)) return [];
  const levels = [];
  if (typeof setup.reclaim === "number") levels.push({ label: "RECLAIM", price: setup.reclaim });
  if (setup.watch_zone && typeof setup.watch_zone === "object") {
    if (typeof setup.watch_zone.low === "number") {
      levels.push({ label: `${setup.watch_zone.label || "ZONE"} low`, price: setup.watch_zone.low });
    }
    if (typeof setup.watch_zone.high === "number") {
      levels.push({ label: `${setup.watch_zone.label || "ZONE"} high`, price: setup.watch_zone.high });
    }
  }
  if (setup.entry && typeof setup.entry === "object") {
    if (typeof setup.entry.low === "number") levels.push({ label: "ENTRY low", price: setup.entry.low });
    if (typeof setup.entry.high === "number") levels.push({ label: "ENTRY high", price: setup.entry.high });
  }
  return levels;
}

// Context-only coins (currently just BTC) are never trade candidates - no
// entry/SL/TP, just key S/R levels for early warning that a market-wide move
// may be coming before it cascades through the tradeable coins' own alerts.
// Kept on instant ticker (same reasoning as SL/TP - worth knowing immediately).
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
const newSides = {};
const firstRun = Object.keys(prevSides).length === 0 && !prevState.prices;

// Hysteresis-aware crossing check. Returns true (and records the new side)
// only when price has cleared the buffer band on the opposite side from the
// last confirmed side. Price sitting inside the buffer band is "inside" -
// no state change, no alert, still armed for whichever side it last cleared.
function checkCrossing(sideKey, price, levelPrice) {
  const buffer = Math.abs(levelPrice) * HYSTERESIS_PCT;
  const side = price > levelPrice + buffer ? "above" : price < levelPrice - buffer ? "below" : "inside";
  const prevSide = prevSides[sideKey];

  if (side === "inside") {
    // Stay armed for whatever side was last confirmed; don't overwrite with "inside".
    if (prevSide !== undefined) newSides[sideKey] = prevSide;
    return null;
  }
  newSides[sideKey] = side;
  if (prevSide === undefined || firstRun) return null; // no baseline yet
  if (side !== prevSide) return side; // real, hysteresis-confirmed crossing
  return null;
}

for (const [coin, setup] of Object.entries(ledger.setups || {})) {
  const symbol = coin.replace(/\.P$/, "");
  const tickerPrice = priceBySymbol.get(symbol);
  if (tickerPrice === undefined) continue;

  for (const level of instantLevelsFor(setup)) {
    const sideKey = `${coin}:${level.label}`;
    const newSide = checkCrossing(sideKey, tickerPrice, level.price);
    if (newSide) {
      const direction = newSide === "above" ? "crossed UP through" : "crossed DOWN through";
      crossings.push(
        `${coin}: ${direction} ${level.label} (${level.price}) — now ${tickerPrice} (was near ${prevSides[sideKey] === "above" ? "above" : "below"} it)`
      );
    }
  }

  const closeLevels = closeConfirmedLevelsFor(setup);
  if (closeLevels.length) {
    const interval = klineIntervalFor(setup);
    const closedPrice = await lastClosedCandleClose(symbol, interval);
    if (closedPrice !== undefined) {
      for (const level of closeLevels) {
        const sideKey = `${coin}:${level.label}`;
        const newSide = checkCrossing(sideKey, closedPrice, level.price);
        if (newSide) {
          const direction = newSide === "above" ? "closed UP through" : "closed DOWN through";
          crossings.push(
            `${coin}: ${direction} ${level.label} (${level.price}) on the last closed ${interval === "5" ? "5m" : "1H"} candle — close ${closedPrice}`
          );
        }
      }
    }
  }
}

for (const [coin, entry] of Object.entries(ledger.context_watch || {})) {
  const symbol = coin.replace(/\.P$/, "");
  const tickerPrice = priceBySymbol.get(symbol);
  if (tickerPrice === undefined) continue;

  for (const level of levelsForContext(entry)) {
    const sideKey = `${coin}:${level.label}`;
    const newSide = checkCrossing(sideKey, tickerPrice, level.price);
    if (newSide) {
      const direction = newSide === "above" ? "crossed UP through" : "crossed DOWN through";
      crossings.push(
        `${coin} (context): ${direction} ${level.label} (${level.price}) — now ${tickerPrice} - market-wide move possible, check the tradeable coins`
      );
    }
  }
}

fs.writeFileSync(statePath, JSON.stringify({ levelSides: newSides }, null, 2) + "\n");

if (firstRun) {
  console.log("First run - baseline levels armed, no crossings can be detected yet. Next run onward will report hysteresis-confirmed crossings.");
} else if (crossings.length === 0) {
  console.log("No triggers crossed since last check.");
} else {
  console.log(`${crossings.length} trigger(s) crossed:\n`);
  crossings.forEach((line) => console.log(" - " + line));
}
