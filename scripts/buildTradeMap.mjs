import fs from "node:fs";

const ledgerPath = new URL("../SETUP_LEDGER.json", import.meta.url);
const outputPath = new URL("../AUTOTRADER_TRADE_MAP_TEMPLATE.pine", import.meta.url);

const ledger = JSON.parse(fs.readFileSync(ledgerPath, "utf8"));
const setups = Object.values(ledger.setups || {});

// R:R floors: TP1 is a hard floor (rating capped when missed); TP2 is a
// structural placement band (warn only).
const FLOORS = {
  Scalp: { tp1: 1.5, band: [2.5, 3.5] },
  Intraday: { tp1: 2.0, band: [3.0, 4.0] },
};
const STALE_MS = { Scalp: 12 * 3600 * 1000, Intraday: 24 * 3600 * 1000 };

const q = (value) => JSON.stringify(String(value ?? ""));
// value == null catches both null and undefined - Number(null) coerces to 0
// and Number.isFinite(0) is true, so without this check every intentionally
// blank field (no TP3, no SL yet, etc.) would silently render as the literal
// price 0 instead of Pine's na.
const n = (value) => (value != null && Number.isFinite(Number(value)) ? String(Number(value)) : "na");
const matchExpr = (setup) =>
  `(syminfo.prefix == ${q(setup.exchange || "BYBIT")} and syminfo.ticker == ${q(setup.coin)})`;

const chain = (fallback, transform) =>
  setups.reduceRight(
    (acc, setup) => `${matchExpr(setup)} ? ${transform(setup)} : ${acc}`,
    fallback
  );

const stringChain = (field, fallback = '""') => chain(fallback, (setup) => q(setup[field]));
const numberChain = (field, fallback = "na") => chain(fallback, (setup) => n(setup[field]));
const entryChain = (side) => chain("na", (setup) => n(setup.entry?.[side]));
const watchZoneChain = (side) => chain("na", (setup) => n(setup.watch_zone?.[side]));
const watchLabelChain = chain('""', (setup) => q(setup.watch_zone?.label || "REANALYZE ZONE"));
const tpChain = (index) => chain("na", (setup) => n(setup.tp?.[index]));

const shortDir = (proposed) => {
  const s = String(proposed || "");
  if (/no trade/i.test(s)) return "No Trade";
  if (/conditional long/i.test(s)) return "Cond. Long";
  if (/conditional short/i.test(s)) return "Cond. Short";
  if (/short/i.test(s)) return "Short";
  if (/long/i.test(s)) return "Long";
  return s.replace(/^Proposed\s*/i, "") || "Wait";
};

const derived = new Map();
for (const setup of setups) {
  const isShort = String(setup.direction || "").toLowerCase().includes("short");
  // Conservative fill: confirmation entries fill at the zone edge nearest to
  // price (entry high for longs, entry low for shorts), not the midpoint.
  const edge = isShort ? Number(setup.entry?.low) : Number(setup.entry?.high);
  const risk = Math.abs(edge - Number(setup.sl));
  // tp may be null/undefined for a genuinely undefined target (e.g. only
  // one TP defined) - Number(null) coerces to 0, which would silently
  // compute a fake R:R against price zero, so guard on the raw value first.
  const rr = (rawTp) => {
    const tp = Number(rawTp);
    return risk > 0 && rawTp != null && Number.isFinite(tp)
      ? (isShort ? edge - tp : tp - edge) / risk
      : NaN;
  };
  const rr1 = rr(setup.tp?.[0]);
  const rr2 = rr(setup.tp?.[1]);
  const floors = FLOORS[setup.trade_type] || FLOORS.Intraday;
  const rawEntry = isShort ? setup.entry?.low : setup.entry?.high;
  const hasEntry = rawEntry != null && setup.sl != null && Number.isFinite(edge) && Number.isFinite(Number(setup.sl));

  const failTp1 = !(rr1 >= floors.tp1 - 1e-9);
  // TP2 being undefined is a valid single-target setup, not a band violation.
  const warnTp2 = Number.isFinite(rr2) && !(rr2 >= floors.band[0] - 1e-9 && rr2 <= floors.band[1] + 1e-9);
  const suffix = failTp1
    ? ` · FAILS TP1 >= ${floors.tp1}`
    : warnTp2
      ? " · TP2 OUT OF BAND"
      : "";
  // No entry/SL defined yet (e.g. post-spike, waiting for a base) is a real,
  // valid state - show it plainly instead of formatting NaN into the card.
  // TP2 is allowed to be genuinely undefined (single-target setups) - show
  // that plainly too rather than a formatted NaN.
  const rr2Text = Number.isFinite(rr2) ? `${rr2.toFixed(1)}R` : "no TP2";
  const rrText = hasEntry ? `${rr1.toFixed(1)}R / ${rr2Text}${suffix}` : "N/A - no entry yet";
  const rrColor = !hasEntry ? "gray" : failTp1 ? "red" : warnTp2 ? "orange" : "green";

  const rating = String(setup.setup_rating || "");
  const effRating = failTp1 && !/skip/i.test(rating) ? "Watch Only" : rating;
  if (!hasEntry) {
    // No entry/SL defined yet is expected (e.g. post-spike, waiting for a
    // base) - skip the R:R floor warnings entirely rather than log NaN.
  } else if (failTp1) {
    console.warn(
      `[R:R] ${setup.coin}: TP1 ${rr1.toFixed(2)}R is below the ${setup.trade_type} floor ` +
        `${floors.tp1}R — rating capped at Watch Only.`
    );
  } else if (warnTp2) {
    console.warn(
      `[R:R] ${setup.coin}: TP2 ${rr2.toFixed(2)}R is outside the ${setup.trade_type} band ` +
        `${floors.band[0]}-${floors.band[1]}R — re-place TP2 at structure inside the band.`
    );
  }
  for (const [field, computed] of [["rr_tp1", rr1], ["rr_tp2", rr2]]) {
    const stored = Number(setup[field]);
    if (Number.isFinite(stored) && Math.abs(stored - computed) > 0.05) {
      console.warn(
        `[R:R] ${setup.coin}: ledger ${field}=${stored} drifted from computed ` +
          `${computed.toFixed(2)} — update the ledger record.`
      );
    }
  }

  const analyzedMs = Date.parse(setup.analyzed_at ?? "");
  if (!Number.isFinite(analyzedMs)) {
    console.warn(`[STALE] ${setup.coin}: missing/invalid analyzed_at — card will show UNKNOWN.`);
  }

  const planColor = /no trade/i.test(String(setup.proposed_type || ""))
    ? "gray"
    : effRating === "Clean Trade"
      ? "green"
      : "blue";

  derived.set(setup.coin, {
    planText: `${shortDir(setup.proposed_type)} · ${effRating}`,
    planColor,
    rrText,
    rrColor,
    analyzedMs: Number.isFinite(analyzedMs) ? String(analyzedMs) : "na",
    needsReclaim: setup.activation_basis === "reclaim-entry" ? "true" : "false",
    // Rejection-candle and break-and-retest bases require a close-confirmed
    // rejection of the entry zone, not a bare wick touch - same protection
    // the reclaim line already gets. Entry-zone basis stays touch-only: it
    // represents a plain limit sitting in the zone with no candle gate.
    needsRejection: /^(rejection-candle|break-and-retest)$/.test(String(setup.activation_basis || ""))
      ? "true"
      : "false",
  });
}

const d = (key, fallback) => chain(fallback, (setup) => {
  const value = derived.get(setup.coin)?.[key];
  return key === "analyzedMs" || key === "needsReclaim" || key === "needsRejection" ? value : q(value);
});

const isLongChain = chain("true", (setup) =>
  String(setup.direction || "").toLowerCase().includes("short") ? "false" : "true"
);
const actualEntryChain = chain("0.0", (setup) => n(setup.entry?.actual ?? 0));
const showMap = setups.map((setup) => matchExpr(setup)).join(" or ") || "false";
const labelOffset = 80;

const pine = `//@version=5
indicator("AutoTrader Trade Map", overlay=true, max_lines_count=80, max_labels_count=80)

// Generated from SETUP_LEDGER.json. Do not hand-edit coin levels here.
// Reanalyze updates one ledger record, then rebuilds this multi-symbol map.
// Card shows ledger state; the Live row reports level tags since analyzed_at
// and always means "reanalyze", never "the ledger changed by itself".

showMap = ${showMap}

coin = ${stringChain("coin")}
tradeType = ${stringChain("trade_type")}
planText = ${d("planText", '""')}
planColorName = ${d("planColor", '"blue"')}
setupState = ${stringChain("setup_state")}
positionState = ${stringChain("position_status")}
rrText = ${d("rrText", '""')}
rrColorName = ${d("rrColor", '"green"')}
isLong = ${isLongChain}
needsReclaim = ${d("needsReclaim", "false")}
needsRejection = ${d("needsRejection", "false")}

entryLow = ${entryChain("low")}
entryHigh = ${entryChain("high")}
watchLow = ${watchZoneChain("low")}
watchHigh = ${watchZoneChain("high")}
watchLabel = ${watchLabelChain}
reclaim = ${numberChain("reclaim")}
sl = ${numberChain("sl")}
tp1 = ${tpChain(0)}
tp2 = ${tpChain(1)}
tp3 = ${tpChain(2)}
actualEntry = ${actualEntryChain}
activeFrom = ${numberChain("active_from_unix")}
analyzedAt = ${d("analyzedMs", "na")}

green = color.rgb(34, 197, 94)
red = color.rgb(255, 82, 82)
blue = color.rgb(47, 128, 237)
grey = color.rgb(140, 140, 140)
orange = color.rgb(245, 158, 11)
neutral = color.rgb(107, 114, 128)

colorOf(string name) =>
    name == "red" ? red : name == "orange" ? orange : name == "green" ? green : name == "gray" ? neutral : blue

enteredLong = positionState == "ENTERED LONG" and actualEntry > 0
enteredShort = positionState == "ENTERED SHORT" and actualEntry > 0

entryEdge = isLong ? math.max(entryLow, entryHigh) : math.min(entryLow, entryHigh)
riskSize = math.abs(entryEdge - sl)
rr1v = riskSize > 0 and not na(tp1) ? (isLong ? tp1 - entryEdge : entryEdge - tp1) / riskSize : na
rr2v = riskSize > 0 and not na(tp2) ? (isLong ? tp2 - entryEdge : entryEdge - tp2) / riskSize : na
rr3v = riskSize > 0 and not na(tp3) ? (isLong ? tp3 - entryEdge : entryEdge - tp3) / riskSize : na

anchorTime = na(activeFrom) or activeFrom <= 0 ? analyzedAt : activeFrom
activeBar = showMap and not na(anchorTime) and time >= anchorTime
// The reclaim lifecycle is decided only by completed candles. A forming bar
// can wick across the level, but must not change the Live row.
reclaimSideOk = activeBar and barstate.isconfirmed and not na(reclaim) and (isLong ? close >= reclaim : close <= reclaim)
reclaimSideLost = activeBar and barstate.isconfirmed and not na(reclaim) and (isLong ? close < reclaim : close > reclaim)
entryTouchedNow = activeBar and not na(entryLow) and not na(entryHigh) and high >= math.min(entryLow, entryHigh) and low <= math.max(entryLow, entryHigh)
tp1TouchedNow = activeBar and not na(tp1) and (isLong ? high >= tp1 : low <= tp1)
tp2TouchedNow = activeBar and not na(tp2) and (isLong ? high >= tp2 : low <= tp2)
tp3TouchedNow = activeBar and not na(tp3) and (isLong ? high >= tp3 : low <= tp3)
slTouchedNow = activeBar and not na(sl) and (isLong ? low <= sl : high >= sl)

var bool reclaimSeen = false
var bool zoneTouchedSeen = false
var bool holdLostSeen = false
var bool closedRightSeen = false
var bool closedWrongSeen = false
var bool entrySeen = false
var bool tp1Seen = false
var bool tp2Seen = false
var bool tp3Seen = false
var bool invalidSeen = false
var int reclaimTime = na
var int holdLostTime = na
var int reclaimStatus = 0
var int reclaimStatusTime = na
var int entryTime = na
var int tp1Time = na
var int tp2Time = na
var int tp3Time = na
var int slTime = na

// Reclaim events are close-confirmed crossings, never wick touches, and only
// count when price was on the other side of the line since the anchor.
// Flat (non-nested) ternary form on purpose: Pine's indentation is
// significant, and deeply nested if-blocks here have repeatedly been
// corrupted by editor auto-indent during automated paste. Keep this section
// free of nested if statements.
reclaimJustCrossed = showMap and reclaimSideOk and closedWrongSeen and not reclaimSideOk[1]
reclaimTime := reclaimJustCrossed ? time : reclaimTime
reclaimSeen := showMap and (reclaimSeen or reclaimJustCrossed)
closedRightSeen := showMap and (closedRightSeen or reclaimSideOk)

holdLostJustCrossed = showMap and reclaimSideLost and closedRightSeen and not reclaimSideLost[1]
holdLostTime := holdLostJustCrossed ? time : holdLostTime
holdLostSeen := showMap and (holdLostSeen or holdLostJustCrossed)
closedWrongSeen := showMap and (closedWrongSeen or reclaimSideLost)
reclaimStatus := reclaimJustCrossed ? 1 : holdLostJustCrossed ? -1 : reclaimStatus
reclaimStatusTime := reclaimJustCrossed or holdLostJustCrossed ? time : reclaimStatusTime

// Rejection/break-and-retest bases must not tag "ENTRY TAGGED" off a bare
// wick touch - a live limit fill is not the same as a confirmed reaction.
// zoneTouchedSeen accumulates so the confirming close can land on the same
// bar as the touch (a one-candle sweep-and-reject) or a later bar. Flat
// ternary form on purpose, same reasoning as the reclaim block above.
zoneTouchedSeen := showMap and (zoneTouchedSeen or entryTouchedNow)
entryRejectionOk = showMap and activeBar and barstate.isconfirmed and zoneTouchedSeen and (isLong ? close > entryHigh : close < entryLow)
entryOk = showMap and (needsReclaim ? (entryTouchedNow and reclaimSeen) : needsRejection ? entryRejectionOk : entryTouchedNow)
entryJustSeen = entryOk and not entrySeen
entryTime := entryJustSeen ? time : entryTime
entrySeen := showMap and (entrySeen or entryOk)

tp1JustSeen = showMap and tp1TouchedNow and not tp1Seen
tp1Time := tp1JustSeen ? time : tp1Time
tp1Seen := showMap and (tp1Seen or tp1TouchedNow)

tp2JustSeen = showMap and tp2TouchedNow and not tp2Seen
tp2Time := tp2JustSeen ? time : tp2Time
tp2Seen := showMap and (tp2Seen or tp2TouchedNow)

tp3JustSeen = showMap and tp3TouchedNow and not tp3Seen
tp3Time := tp3JustSeen ? time : tp3Time
tp3Seen := showMap and (tp3Seen or tp3TouchedNow)

slJustSeen = showMap and slTouchedNow and not invalidSeen
slTime := slJustSeen ? time : slTime
invalidSeen := showMap and (invalidSeen or slTouchedNow)

liveEvent = invalidSeen ? "SL TAGGED" : tp3Seen ? "TP3 TAGGED" : tp2Seen ? "TP2 TAGGED" : tp1Seen ? "TP1 TAGGED" : entrySeen ? "ENTRY TAGGED" : reclaimStatus == -1 ? "RECLAIM LOST" : reclaimStatus == 1 ? "RECLAIMED" : ""
liveTime = invalidSeen ? slTime : tp3Seen ? tp3Time : tp2Seen ? tp2Time : tp1Seen ? tp1Time : entrySeen ? entryTime : reclaimStatusTime

plState = enteredLong ? (close >= actualEntry ? "UR PROFIT" : "UR LOSS") : enteredShort ? (close <= actualEntry ? "UR PROFIT" : "UR LOSS") : positionState
statusText = setupState + " / " + plState

plot(showMap ? entryLow : na, "Entry Bottom", color=green, linewidth=2, display=display.all - display.status_line)
plot(showMap ? entryHigh : na, "Entry Top", color=green, linewidth=2, display=display.all - display.status_line)
plot(showMap ? watchLow : na, "Watch Zone Bottom", color=blue, linewidth=1, display=display.all - display.status_line)
plot(showMap ? watchHigh : na, "Watch Zone Top", color=blue, linewidth=1, display=display.all - display.status_line)
plot(showMap ? reclaim : na, "Reclaim", color=blue, linewidth=2, display=display.all - display.status_line)
plot(showMap ? sl : na, "Invalid / SL", color=red, linewidth=2, display=display.all - display.status_line)
plot(showMap ? tp1 : na, "TP1", color=isLong ? green : red, linewidth=2, display=display.all - display.status_line)
plot(showMap ? tp2 : na, "TP2", color=isLong ? green : red, linewidth=2, display=display.all - display.status_line)
plot(showMap and not na(tp3) ? tp3 : na, "TP3", color=grey, linewidth=2, display=display.all - display.status_line)

var label lEntry = na
var label lWatch = na
var label lReclaim = na
var label lSL = na
var label lTP1 = na
var label lTP2 = na
var label lTP3 = na
var label lState = na
var line gEntryLow = na
var line gEntryHigh = na
var line gWatchLow = na
var line gWatchHigh = na
var line gReclaim = na
var line gSL = na
var line gTP1 = na
var line gTP2 = na
var line gTP3 = na

makeLabel(label old, float y, string txt, color bg) =>
    if not na(old)
        label.delete(old)
    label.new(bar_index + ${labelOffset}, y, txt, xloc=xloc.bar_index, yloc=yloc.price, style=label.style_label_left, color=bg, textcolor=color.white, size=size.small)

makeGuide(line old, float y, color c) =>
    if not na(old)
        line.delete(old)
    line.new(bar_index, y, bar_index + ${labelOffset}, y, xloc=xloc.bar_index, extend=extend.none, color=c, width=2)

makeWatchGuide(line old, float y) =>
    if not na(old)
        line.delete(old)
    line.new(bar_index, y, bar_index + ${labelOffset}, y, xloc=xloc.bar_index, extend=extend.none, color=blue, style=line.style_dashed, width=1)

if barstate.islast
    if showMap
        gEntryLow := makeGuide(gEntryLow, entryLow, green)
        gEntryHigh := makeGuide(gEntryHigh, entryHigh, green)
        if not na(watchLow) and not na(watchHigh)
            gWatchLow := makeWatchGuide(gWatchLow, watchLow)
            gWatchHigh := makeWatchGuide(gWatchHigh, watchHigh)
        gReclaim := makeGuide(gReclaim, reclaim, blue)
        gSL := makeGuide(gSL, sl, red)
        gTP1 := makeGuide(gTP1, tp1, isLong ? green : red)
        gTP2 := makeGuide(gTP2, tp2, isLong ? green : red)
        if not na(tp3)
            gTP3 := makeGuide(gTP3, tp3, grey)
        lEntry := makeLabel(lEntry, (entryLow + entryHigh) / 2.0, "ENTRY " + str.tostring(entryLow) + "-" + str.tostring(entryHigh), green)
        if not na(watchLow) and not na(watchHigh)
            lWatch := makeLabel(lWatch, (watchLow + watchHigh) / 2.0, watchLabel + " " + str.tostring(watchLow) + "-" + str.tostring(watchHigh), blue)
        lReclaim := makeLabel(lReclaim, reclaim, "RECLAIM " + str.tostring(reclaim), blue)
        lSL := makeLabel(lSL, sl, "SL " + str.tostring(sl), red)
        lTP1 := makeLabel(lTP1, tp1, "TP1 " + str.tostring(tp1) + " · " + str.tostring(rr1v, "#.#") + "R", isLong ? green : red)
        lTP2 := makeLabel(lTP2, tp2, "TP2 " + str.tostring(tp2) + " · " + str.tostring(rr2v, "#.#") + "R", isLong ? green : red)
        if not na(tp3)
            lTP3 := makeLabel(lTP3, tp3, "TP3 " + str.tostring(tp3) + " · " + str.tostring(rr3v, "#.#") + "R", grey)
        lState := makeLabel(lState, close, statusText, plState == "UR PROFIT" ? green : plState == "UR LOSS" ? red : orange)
    else
        if not na(lEntry)
            label.delete(lEntry)
            label.delete(lWatch)
            label.delete(lReclaim)
            label.delete(lSL)
            label.delete(lTP1)
            label.delete(lTP2)
            label.delete(lTP3)
            label.delete(lState)
            line.delete(gEntryLow)
            line.delete(gEntryHigh)
            line.delete(gWatchLow)
            line.delete(gWatchHigh)
            line.delete(gReclaim)
            line.delete(gSL)
            line.delete(gTP1)
            line.delete(gTP2)
            line.delete(gTP3)

var table t = table.new(position.top_right, 2, 6, border_width=1)

cell(int row, string leftTxt, string rightTxt, color bg) =>
    table.cell(t, 0, row, leftTxt, text_color=color.white, bgcolor=color.rgb(55, 65, 81))
    table.cell(t, 1, row, rightTxt, text_color=color.white, bgcolor=bg)

if barstate.islast
    table.clear(t, 0, 0, 1, 5)
    if showMap
        staleMs = tradeType == "Scalp" ? ${STALE_MS.Scalp} : ${STALE_MS.Intraday}
        ageMs = na(analyzedAt) ? staleMs * 2.0 : timenow - analyzedAt
        updatedTxt = na(analyzedAt) ? "UNKNOWN" : str.format_time(int(analyzedAt), "MMM d · HH:mm", "GMT+1")
        updatedColor = ageMs >= staleMs ? red : ageMs >= staleMs / 2 ? orange : neutral
        stateColor = str.contains(setupState, "INVALID") or plState == "UR LOSS" ? red : plState == "UR PROFIT" or str.contains(setupState, "ACTIVE") ? green : orange
        cell(0, "Coin", coin + " · " + tradeType, neutral)
        cell(1, "Plan", planText, colorOf(planColorName))
        cell(2, "State", setupState + " · " + plState, stateColor)
        cell(3, "R:R", rrText, colorOf(rrColorName))
        cell(4, "Updated", updatedTxt, updatedColor)
        if liveEvent != "" and not na(liveTime)
            cell(5, "Live", liveEvent + " · " + str.format_time(liveTime, "MMM d HH:mm", "GMT+1") + " · REANALYZE", liveEvent == "SL TAGGED" ? red : orange)
`;

fs.writeFileSync(outputPath, pine);
console.log(`Wrote ${setups.length} setup slots to ${outputPath.pathname}`);
