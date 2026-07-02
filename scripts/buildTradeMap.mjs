import fs from "node:fs";

const ledgerPath = new URL("../SETUP_LEDGER.json", import.meta.url);
const outputPath = new URL("../CODEX_TRADE_MAP_TEMPLATE.pine", import.meta.url);

const ledger = JSON.parse(fs.readFileSync(ledgerPath, "utf8"));
const setups = Object.values(ledger.setups || {});

const q = (value) => JSON.stringify(String(value ?? ""));
const n = (value) => (Number.isFinite(Number(value)) ? String(Number(value)) : "na");
const matchExpr = (setup) =>
  `(syminfo.prefix == ${q(setup.exchange || "BYBIT")} and syminfo.ticker == ${q(setup.coin)})`;

const chain = (field, fallback, transform = (setup) => setup[field]) =>
  setups.reduceRight((acc, setup) => {
    const value = transform(setup);
    return `${matchExpr(setup)} ? ${value} : ${acc}`;
  }, fallback);

const stringChain = (field, fallback = '""') =>
  chain(field, fallback, (setup) => q(setup[field]));

const numberChain = (field, fallback = "na") =>
  chain(field, fallback, (setup) => n(setup[field]));

const entryChain = (side) =>
  chain("entry", "na", (setup) => n(setup.entry?.[side]));

const tpChain = (index) =>
  chain("tp", "na", (setup) => n(setup.tp?.[index]));

const isLongChain = setups.reduceRight((acc, setup) => {
  const value = String(setup.direction || "").toLowerCase().includes("short") ? "false" : "true";
  return `${matchExpr(setup)} ? ${value} : ${acc}`;
}, "true");

const actualEntryChain = chain("entry", "0.0", (setup) => n(setup.entry?.actual ?? 0));
const showMap = setups.map((setup) => matchExpr(setup)).join(" or ") || "false";
const labelOffset = 5;

const pine = `//@version=5
indicator("Codex Trade Map", overlay=true, max_lines_count=80, max_labels_count=80)

// Generated from SETUP_LEDGER.json. Do not hand-edit coin levels here.
// Reanalyze updates one ledger record, then rebuilds this multi-symbol map.

showMap = ${showMap}

coin = ${stringChain("coin")}
tradeType = ${stringChain("trade_type")}
direction = ${stringChain("proposed_type")}
rating = ${stringChain("setup_rating")}
setupState = ${stringChain("setup_state")}
positionState = ${stringChain("position_status")}
mode = ${chain("reclaim", '""', (setup) => q(`RECLAIM ${setup.reclaim ?? ""}`))}
isLong = ${isLongChain}

entryLow = ${entryChain("low")}
entryHigh = ${entryChain("high")}
reclaim = ${numberChain("reclaim")}
sl = ${numberChain("sl")}
tp1 = ${tpChain(0)}
tp2 = ${tpChain(1)}
tp3 = ${tpChain(2)}
actualEntry = ${actualEntryChain}

green = color.rgb(34, 197, 94)
red = color.rgb(255, 82, 82)
blue = color.rgb(47, 128, 237)
grey = color.rgb(140, 140, 140)
orange = color.rgb(245, 158, 11)
neutral = color.rgb(107, 114, 128)

enteredLong = positionState == "ENTERED LONG" and actualEntry > 0
enteredShort = positionState == "ENTERED SHORT" and actualEntry > 0
plState = enteredLong ? (close >= actualEntry ? "UR PROFIT" : "UR LOSS") : enteredShort ? (close <= actualEntry ? "UR PROFIT" : "UR LOSS") : positionState
statusText = setupState + " / " + plState

plot(showMap ? entryLow : na, "Entry Bottom", color=green, linewidth=2, display=display.all - display.status_line)
plot(showMap ? entryHigh : na, "Entry Top", color=green, linewidth=2, display=display.all - display.status_line)
plot(showMap ? reclaim : na, "Reclaim", color=blue, linewidth=2, display=display.all - display.status_line)
plot(showMap ? sl : na, "Invalid / SL", color=red, linewidth=2, display=display.all - display.status_line)
plot(showMap ? tp1 : na, "TP1", color=isLong ? green : red, linewidth=2, display=display.all - display.status_line)
plot(showMap ? tp2 : na, "TP2", color=isLong ? green : red, linewidth=2, display=display.all - display.status_line)
plot(showMap and not na(tp3) ? tp3 : na, "TP3", color=grey, linewidth=2, display=display.all - display.status_line)

var label lEntry = na
var label lReclaim = na
var label lSL = na
var label lTP1 = na
var label lTP2 = na
var label lTP3 = na
var label lState = na
var line gEntryLow = na
var line gEntryHigh = na
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

if barstate.islast
    if showMap
        gEntryLow := makeGuide(gEntryLow, entryLow, green)
        gEntryHigh := makeGuide(gEntryHigh, entryHigh, green)
        gReclaim := makeGuide(gReclaim, reclaim, blue)
        gSL := makeGuide(gSL, sl, red)
        gTP1 := makeGuide(gTP1, tp1, isLong ? green : red)
        gTP2 := makeGuide(gTP2, tp2, isLong ? green : red)
        if not na(tp3)
            gTP3 := makeGuide(gTP3, tp3, grey)
        lEntry := makeLabel(lEntry, (entryLow + entryHigh) / 2.0, "ENTRY " + str.tostring(entryLow) + "-" + str.tostring(entryHigh), green)
        lReclaim := makeLabel(lReclaim, reclaim, "RECLAIM " + str.tostring(reclaim), blue)
        lSL := makeLabel(lSL, sl, "INVALID " + str.tostring(sl), red)
        lTP1 := makeLabel(lTP1, tp1, "TP1 " + str.tostring(tp1), isLong ? green : red)
        lTP2 := makeLabel(lTP2, tp2, "TP2 " + str.tostring(tp2), isLong ? green : red)
        if not na(tp3)
            lTP3 := makeLabel(lTP3, tp3, "TP3 " + str.tostring(tp3), grey)
        lState := makeLabel(lState, close, statusText, plState == "UR PROFIT" ? green : plState == "UR LOSS" ? red : orange)
    else
        if not na(lEntry)
            label.delete(lEntry)
            label.delete(lReclaim)
            label.delete(lSL)
            label.delete(lTP1)
            label.delete(lTP2)
            label.delete(lTP3)
            label.delete(lState)
            line.delete(gEntryLow)
            line.delete(gEntryHigh)
            line.delete(gReclaim)
            line.delete(gSL)
            line.delete(gTP1)
            line.delete(gTP2)
            line.delete(gTP3)

var table t = table.new(position.top_right, 2, 9, border_width=1)

cell(int row, string left, string right, color bg) =>
    table.cell(t, 0, row, left, text_color=color.white, bgcolor=color.rgb(55, 65, 81))
    table.cell(t, 1, row, right, text_color=color.white, bgcolor=bg)

if barstate.islast
    table.clear(t, 0, 0, 1, 8)
    if showMap
        cell(0, "Coin", coin, neutral)
        cell(1, "Trade Type", tradeType, blue)
        cell(2, "Direction", direction, str.contains(direction, "WAIT") ? orange : blue)
        cell(3, "Rating", rating, rating == "Clean Trade" ? green : rating == "Conditional Trade" ? orange : neutral)
        cell(4, "State", setupState, str.contains(setupState, "WAIT") ? orange : green)
        cell(5, "Position", plState, plState == "UR PROFIT" ? green : plState == "UR LOSS" ? red : neutral)
        cell(6, "Entry", str.tostring(entryLow) + "-" + str.tostring(entryHigh), green)
        cell(7, "SL / TP", str.tostring(sl) + " / " + str.tostring(tp1) + " / " + str.tostring(tp2) + (na(tp3) ? "" : " / " + str.tostring(tp3)), isLong ? green : red)
        cell(8, "Mode", mode, blue)
`;

fs.writeFileSync(outputPath, pine);
console.log(`Wrote ${setups.length} setup slots to ${outputPath.pathname}`);
