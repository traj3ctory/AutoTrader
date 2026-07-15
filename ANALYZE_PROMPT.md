# Analyze Prompt: TradingView Crypto Perpetual Futures

Use this prompt to analyze crypto perpetual futures on Bybit using TradingView.

This is Step 1 of the roadmap: make the analysis trade like the user, then better. Treat all output as educational chart analysis, not financial advice. Do not automate alerts or auto-trade from this prompt.

## Non-Negotiable Execution Rule

The final answer is not complete unless one of these is true:

- The TradingView chart has been cleaned, marked, verified, and left on the chart view.
- The Pine script was regenerated and handed off for manual paste per the Chart Drawing Method rule below, and the final answer clearly starts with `SCRIPT READY - MANUAL PASTE REQUIRED`.
- Chart marking failed, and the final answer clearly starts with `CHART NOT MARKED` and explains why.

Do not give a normal final trade summary while the chart is stale, unmarked, or showing conflicting old levels.

The normal output format is allowed only after TradingView chart marking and verification succeed, or after a manual-paste handoff per the rule below. If the chart is not marked or cannot be verified and no handoff was offered, do not present the setup as completed. You may still provide the setup, but it must be clearly labeled `SETUP ONLY - NOT DRAWN ON TRADINGVIEW`, include the drawing/verification issue, and offer to redraw from the ledger.

## Analyze Always Means A Fresh Read

`Analyze [coin]` is never satisfied by reciting the ledger's last saved entry, no matter how recent it looks. Every request requires reading the live chart across the required timeframe stack this turn and re-deciding the setup from what is actually happening right now.

- The ledger is a write-target and history/context source, not an answer. Read it first for prior setup state, journal history, and mistake tags - then perform the actual chart read before writing or reporting anything as the analysis.
- If the chart genuinely cannot be read this turn (render failure, retry cap hit, no screenshot available), that is a `CHART NOT MARKED`-class limitation - say so explicitly. Do not paper over it by returning the last saved ledger values as if they were produced by this turn's analysis.
- Record the reasoning, not just the numbers: for every entry/retest zone, state what structural evidence produced it (which swing high/low, which liquidity pool, which relative-strength signal, which candle behavior) directly in the ledger's `bias`/`notes`/`nearest_liquidity` fields, and repeat the key reasoning in the chat output. The "why" must survive without needing to be reconstructed later.
- Always give TradingView a short pause to paint before reading it: after opening a chart, switching symbols, or changing timeframe/interval, wait a few seconds before the first screenshot or read. Do not screenshot immediately on navigation - the canvas is frequently still blank or showing the prior symbol's stale data at that instant, not a real render failure yet. Only treat it as a genuine render failure (subject to the one-retry-cap) if it is still blank/stale after that pause.

## Chart Drawing Method

Attempt automated drawing first, every time, using this exact method - not the fragile methods from earlier sessions.

Session setup:

- Use one persistent browser tab for the whole session. Do not close and reopen a fresh tab per coin; fresh navigations are the main trigger for the TradingView blank-canvas render bug. Switch symbols within the same tab (watchlist click or symbol search) instead of renavigating.

Paste method - OS-level clipboard only, never a page-JS clipboard write:

1. Update the ledger and run `node scripts/buildTradeMap.mjs` to regenerate `AUTOTRADER_TRADE_MAP_TEMPLATE.pine`.
2. Load the script into the real OS clipboard via `pbcopy < AUTOTRADER_TRADE_MAP_TEMPLATE.pine` (Bash, outside the browser entirely). Never use `navigator.clipboard.writeText()` from page JS - it silently no-ops without document focus, which was the root cause of nearly every paste failure in prior sessions.
3. In the Pine Editor: click into the editor, Cmd+A, Cmd+V (a real native paste, never a synthetic ClipboardEvent or `execCommand insertText` - both of those let Monaco's auto-indent corrupt nested indentation-sensitive blocks).
4. Cmd+S to save, then use "Add to chart" if the script is not already attached to this chart.
5. Run the observed Post-Drawing Verification Gate (fresh screenshot, read the rendered card, confirm every field against the ledger).

One retry cap: if the paste or verification fails, retry the exact same method once. If it fails twice, stop automation and fall back to the manual handoff below - do not improvise a third method or debug-loop.

Manual handoff (fallback only, after the retry cap is hit):

1. Tell the user plainly the automated paste failed after retry, and point to the exact file path (reveal in Finder if useful).
2. Start the final answer with `SCRIPT READY - MANUAL PASTE REQUIRED`.
3. Give a compact analysis: Coin / Trade Type / Direction / Entry / SL / TP / R:R / Trigger-Reclaim / Setup State / Final Action / one-line bias - not the full field list.
4. Render a visual trade-map (entry zone, SL, TP1-3, reclaim line, state) from the same ledger data as a fallback the user can look at immediately, independent of whether the live chart ever renders.
5. When the user confirms they pasted it, run the observed Post-Drawing Verification Gate before calling the chart verified.

The journal and scorecard update every time regardless of paste outcome - the record of what was analyzed does not depend on whether the chart shows it yet.

## Source Of Truth

Use this source hierarchy:

1. Current visible TradingView chart.
2. `SETUP_LEDGER.json` for remembered setup state, prior levels, position status, and journal history.
3. TradingView tab candle stream or TradingView page data, only when visual chart access is limited.
4. External APIs only if the user explicitly asks.

If source access is limited, state the limitation before drawing or summarizing.

Do not use old screenshots, old TradingView drawings, or old visible Pine levels as the memory source. The ledger is the memory source. TradingView is only the live chart and display layer.

## Ledger Memory Rule

AutoTrader remembers. TradingView displays.

Use `SETUP_LEDGER.json` as the source of truth for remembered per-coin analysis. For every `Analyze [coin]` request:

1. Open or switch to the current TradingView chart.
2. Read the current coin's ledger entry if one exists.
3. Analyze the live chart and decide whether the ledger setup is still valid, missed, active, TP hit, invalidated, or stale.
4. Update the ledger entry before drawing the chart.
5. Render only the current coin's setup from the ledger onto TradingView.
6. Verify that the visible TradingView map matches the ledger entry.

The ledger must store coin, exchange, trade type, proposed type, bias, BTC/ETH filter, catalyst, setup type, setup rating, setup state, position status, direction, entry, activation basis (`activation_basis`: entry-zone or reclaim-entry), actual entry if known, reclaim/trigger, SL, SL quality, TP, rr_tp1, rr_tp2, invalidation, liquidity, relative strength, final action, analyzed_at (ISO timestamp of the analysis), and notes.

If TradingView fails to render the map, do not lose the setup. Keep the ledger updated and start final output with `CHART NOT MARKED` or `CHART VERIFICATION FAILED`.

Do not treat TradingView Pine/drawings as persistent memory. If TradingView loses or hides a setup during symbol switching, redraw it from the ledger.

## Ledger Validity Gate

Before drawing any saved setup, compare the current TradingView chart to the coin's ledger record.

Classify the setup lifecycle:

- Valid / Waiting
- Triggered But Not Entered
- Active / Manage
- TP Hit / Manage
- SL Hit / Invalidated
- Missed / No Chase
- Failed Reclaim
- Stale / Reanalyze
- No Clean Setup

Rules:

- If the saved setup is still valid, draw or keep that coin's Pine slot.
- If price has hit TP, update the ledger state to `TP HIT / MANAGE` before drawing.
- If price has hit SL or invalidation, update the ledger state to `INVALIDATED`, remove/hide the setup, and journal only if useful.
- If price moved too far without entry, update to `MISSED / NO CHASE`.
- If reclaim failed, update to `FAILED RECLAIM` or `WAIT RECLAIM`.
- If structure changed enough that old levels are no longer useful, reanalyze fresh and overwrite that coin's ledger record.
- If no clean setup remains, update to `WAIT / NO TRADE` and keep the chart mostly clean.

Never draw a ledger setup just because it exists. Draw it only after it passes this validity gate.

## Ledger Hygiene Rule

Keep `SETUP_LEDGER.json` compact and current:

- Maintain one active setup record per coin symbol.
- Update that coin's existing record in place when levels, state, or position status change.
- Do not append duplicate records for repeated analyses of the same coin.
- Keep only the latest active/watch setup in `setups`.
- Move completed, invalidated, stale, TP/SL-hit, or learning-review items into `journal` only when they are worth reviewing.
- Keep journal entries concise: coin, date, setup type, result, mistake tag, and one short note.
- Do not store long narrative analysis inside the ledger.
- If the ledger entry is older than the current chart structure, classify it as stale and overwrite it with the fresh setup.
- If a setup is no longer useful and not worth journaling, replace it rather than preserving old levels.

## Pre-Analysis State Check

Before choosing a trade, classify the chart state:

- Fresh Setup
- Existing Active Trade
- Missed Setup
- TP Hit / Manage
- Invalidated Setup
- Stale Map / Needs Cleanup

If the chart has stale or conflicting drawings, mark the state as `Stale Map / Needs Cleanup` before analysis.

## Timeframe Rules

First decide the trade type:

- Normal intraday/day trade: use 1D -> 4H -> 1H, with entry planned on 1H and trigger confirmation on 15m or 1H closes.
- Scalp: use 4H -> 1H -> 15m -> 5m, with entry planned on 5m.

Mandatory scalp HTF veto:

- Before mapping any scalp, mark 4H supply/demand first.
- A scalp long into overhead 4H supply, or a scalp short into 4H demand, is capped at Watch Only unless the setup is explicitly a reaction trade at that 4H zone.
- Reclaims, retests, and confirmations are judged by candle closes on the entry timeframe, not wicks.

If the user gives only a coin name, choose the trade type based on chart structure, volatility, distance to target, and setup quality.

The chart table and final written output must use the exact same trade type.

## Market Filter

Use BTCUSDT and ETHUSDT as confidence filters:

- If BTC/ETH align with the setup, confidence increases.
- If BTC/ETH conflict strongly, reduce confidence or skip the trade.
- BTC/ETH are confidence filters only, not mandatory confirmation.

Always state the BTC/ETH filter as:

- Aligned
- Mixed
- Conflicting

## Catalyst / News Gate

Before finalizing a call, check whether scheduled or breaking catalysts/news can override structure:

- Macro: CPI, FOMC, jobs/NFP, major rate decisions.
- Coin-specific news: token unlock, exchange listing/delisting, hack/exploit, live headline, major partnership, legal/regulatory update, chain outage, governance vote, or large ecosystem event.

Classify the catalyst as:

- Clear
- News Risk
- Unverified

Rules:

- Catalyst includes news, but the source hierarchy still applies.
- If the user has not explicitly asked for external news/API checks and TradingView does not show enough news context, classify as Unverified.
- If a high-impact event is imminent or unfolding, mark News Risk and cap Final Action at Wait or No Chase, unless the user explicitly says to trade the event.
- If the catalyst cannot be verified, mark Unverified and say "catalyst unverified - check manually." Do not assume Clear.

## Method

Use supply/demand, trendlines, liquidity, reclaim levels, invalidation, relative strength, and R:R.

## Rules Engine Checklist

Analyze every setup with this checklist before giving a final call.

Setup Type:

- Liquidity Sweep + MSS
- Failed Reclaim / Deviation
- FVG / Imbalance Retest
- Breaker / Failed Supply-Demand Flip
- Compression-to-Expansion Breakout
- Standard Supply/Demand Retest
- No Clean Setup

Direction:

- Long
- Short
- Wait / No Trade

Entry Basis:

- Entry-zone activation
- Reclaim-entry activation
- Rejection candle
- Break-and-retest
- No entry yet

Reclaim Status:

- Not reclaimed
- Reclaimed and holding
- Reclaimed but no entry
- Failed reclaim / deviation

SL Quality:

- Safe
- Vulnerable
- Too Tight

BTC/ETH Filter:

- Aligned
- Mixed
- Conflicting

Catalyst:

- Clear
- News Risk
- Unverified

Final Action:

- Trade
- Wait
- Skip
- No Chase

## Setup Rating Model

Always assign a plain-language setup rating.

Clean Trade:

- Clean HTF zone.
- Clear liquidity sweep or clean reclaim/retest structure.
- SL is Safe.
- TP1 meets the trade-type floor and TP2 sits inside the trade-type band.
- BTC/ETH are aligned or not strongly conflicting.
- Entry is not late.

Conditional Trade:

- Valid setup but one important weakness exists.
- TP1 meets the trade-type floor.
- SL is Safe or Vulnerable, not Too Tight.
- Confidence is reduced, but setup can remain conditional.

Watch Only:

- Watch only.
- Useful levels exist, but trade is not ready.
- Needs reclaim, retest, rejection, MSS, or better R:R.

Skip / No Trade:

- No clean invalidation.
- SL is Too Tight.
- Proper structural SL puts TP1 below the trade-type floor.
- Price is late or chasing.
- BTC/ETH strongly conflict and the coin has no clear relative strength.

Final action by rating:

- Clean Trade = Trade candidate if entry condition is met.
- Conditional Trade = Conditional trade or reduced confidence.
- Watch Only = Wait / monitor only.
- Skip / No Trade = No trade.

## Pattern Priority

Prioritize these patterns first:

1. Liquidity Sweep + MSS.
2. Failed Reclaim / Deviation.
3. FVG / Imbalance Retest.
4. Relative Strength Filter.

Use these as secondary patterns:

- Breaker / Failed Supply-Demand Flip.
- Compression-to-Expansion Breakout.
- Standard Supply/Demand Retest.

Delay or avoid these for now:

- Harmonics.
- Elliott Wave.
- RSI divergence-heavy systems.
- Too many indicators.
- Fully automated execution logic.

## Pattern Rules

Liquidity Sweep + MSS:

- Identify obvious buy-side or sell-side liquidity.
- Confirm price sweeps the liquidity with a wick or displacement.
- Require a market structure shift after the sweep before treating it as reversal-ready.
- Entry is usually a retest, FVG fill, or demand/supply reaction after MSS.
- If MSS is absent, mark WAIT REACTION or WAIT RECLAIM.

Failed Reclaim / Deviation:

- Identify a key reclaim/resistance/support level.
- If price reclaims but cannot hold, treat it as a potential trap.
- For longs, failed reclaim under resistance is not active long management.
- For shorts, failed reclaim can become a short setup only after rejection and breakdown/retest.
- If price reclaims but no entry was taken, use RECLAIMED / WAIT RETEST or NO CHASE.

FVG / Imbalance Retest:

- Use only after an impulsive displacement candle or clear imbalance.
- FVG is an entry refinement tool, not a standalone reason to trade.
- Entry must still respect supply/demand, liquidity, invalidation, and R:R.
- If FVG entry makes SL too tight or structural SL puts TP1 below the trade-type floor, mark WAIT / SKIP.

Breaker / Failed Supply-Demand Flip:

- Use when price breaks through a prior supply/demand zone, then retests it from the other side.
- The old zone must act as the opposite side on retest.
- Entry requires rejection/acceptance at the retested zone.
- Invalidation goes beyond the breaker zone wick/base, not inside it.

Compression-to-Expansion Breakout:

- Use when price coils under resistance or above support with tightening volatility.
- Prefer break-and-retest, not a blind breakout chase.
- If expansion happens directly into HTF supply/resistance, mark NO CHASE or WAIT RETEST.
- BTC/ETH alignment materially affects confidence.

Relative Strength Filter:

- For longs, prefer coins holding structure better than BTC and ETH.
- For shorts, prefer coins breaking structure weaker than BTC and ETH.
- Weak BTC/ETH + coin bouncing into resistance = reduce confidence or skip.
- Weak BTC/ETH + coin cleanly reclaiming with strong relative strength = moderate confidence, not automatic trade.

## Trendline Rules

- Wick-to-wick.
- 3 touches = valid trendline.
- 2 touches = tentative trendline.
- If no clean trendline exists, skip it.

## Supply And Demand Rules

- Use full candle wick range or base before impulsive move.
- Mark HTF supply/demand first.
- Do not force zones if unclear.
- Prefer clear labeled horizontal lines over large boxes.

## Liquidity And SL Quality Rules

Before giving an entry:

- Identify the nearest obvious liquidity above and below the setup.
- For longs, check the nearest sell-side liquidity below the entry zone.
- For shorts, check the nearest buy-side liquidity above the entry zone.
- SL must be beyond both the obvious liquidity and the full demand/supply wick/base.
- Do not place SL on the first obvious local low/high if that level is likely to be swept.
- If the proper structural SL puts TP1 below the trade-type floor, mark WAIT / SKIP.
- Always classify SL Quality as Safe, Vulnerable, or Too Tight.
- SL earns Safe only when it sits beyond both the nearest obvious liquidity and the full zone wick/base, with buffer for a sweep.
- If the properly placed SL is still Vulnerable, widen the zone or skip; Vulnerable is a warning state, not an acceptable default rating.

## TP Zone Validity Rule

- Every TP in the ladder sits at the NEAR edge (the entry) of its zone - the zone top for a short, the zone bottom for a long - never inside it, never past its far edge. The near edge is the only level guaranteed reachable if the move works at all, because defenders react at the edge, not the middle.
- TP1 = near edge of the first opposing zone. No precondition.
- TP2 = near edge of the second zone, but only counts as a real (non-conditional) target once the first zone is confirmed broken (a close through it, holding). Until then it is a stretch target, not something to size the trade around.
- TP3 (and beyond) = near edge of each subsequent zone, same conditional rule chained one zone deeper each time.
- No TP may span more than one zone. This was the original form of the rule and still holds - it falls directly out of the near-edge rule above, since the near edge of zone N is always before zone N+1 begins.
- If a TP's placement (round number, old note, arbitrary R multiple) turns out to land inside or beyond a second zone once real zone boundaries are mapped, correct it back to just outside the first zone - do not keep the deeper number for a better-looking R:R.
- Deeper TPs (TP2, TP3) may target beyond further zones, but only as conditional/stretch targets: valid to display, not valid to lean on for the R:R floor check, unless the zone(s) between the current TP and that deeper one are confirmed broken (a close through, holding) as the trade develops.
- Re-check this whenever new zone boundaries are drawn or the chart reveals structure that wasn't visible at initial analysis - it is as easy to violate silently as the SL-too-tight mistake, and gets caught the same way: go back and look at what is actually between entry and the target.

## Extension And Chase Rules

- Do not chase price.
- If the coin has already made a strong extended move, do not use blind limit entry.
- For extended coins, require a rejection candle, reclaim, or break-and-retest before entry.
- If price has already rejected the trigger/reclaim level, downgrade the setup to WAIT until demand/supply confirms.
- If setup is late, clearly label NO CHASE.

Parabolic Spike Rule:

After a single-candle (or near-single-candle) extension of roughly 20%+ with an Unverified catalyst:

- Do not map pullback longs inside the impulse candle's own range. There is no demand mid-candle; entry zones must sit at a visible base/consolidation or at the impulse origin.
- The valid patterns are: (a) liquidity sweep + failed reclaim SHORT per Pattern Priority, or (b) wait for the retest of the impulse origin base.
- Any TP/supply level wick-swept during the spike is no longer virgin liquidity; treat first-touch magnets as consumed and take partials faster.
- Reference: USUSDT.P 2026-07-07 journal entry, mistake tag SWEEP_FAIL_MISREAD.

## Setup State Lifecycle Rules

Before updating or summarizing an existing chart setup:

- Check whether the previous setup is still active, already hit TP, hit SL, or changed into a new decision zone.
- If TP1/TP2 has already been hit, do not leave the old entry/SL/TP labels as the active setup.
- If price reaches the old TP and enters demand/supply, refresh the map to the new decision state before summarizing.
- If the setup direction changes, remove or reset the old direction labels first.

Use a clear setup state:

- READY
- ACTIVE / MANAGE
- TP1 HIT / MANAGE
- TP2 HIT / MANAGE
- RECLAIMED / WAIT RETEST
- WAIT REACTION
- WAIT RECLAIM
- WAIT RETEST
- WAIT / SKIP
- NO CHASE
- INVALID

## Entry Activation Rules

State which one controls activation before drawing the map:

- Entry-zone activation.
- Reclaim-entry activation.
- Rejection candle activation.
- Break-and-retest activation.
- No entry yet.

Reclaim alone never equals active unless reclaim-entry activation is explicitly chosen.

Entry zone = where the trade can become active.

Reclaim / trigger = confirmation or permission level unless the entry style is explicitly break-and-retest.

Do not mark ACTIVE / MANAGE from reclaim alone when the planned entry is a limit/pullback zone.

If price reclaims the trigger but never trades into the planned entry zone, use RECLAIMED / WAIT RETEST or NO CHASE.

Mark ACTIVE / MANAGE only when price has traded through the planned entry zone after the setup start, or when the analysis explicitly says the reclaim/break-and-retest is the entry.

If both a pullback entry and reclaim entry are possible, state which one controls activation before drawing the map.

If the coin is in active expansion/momentum, map BOTH a deep pullback zone and a break-and-retest activation at the reclaim level, and state which one is primary. Do not map only a deep limit zone in momentum conditions; that is how valid theses become missed entries.

If price is above reclaim but entry was missed, do not convert the missed trade into active management. Refresh the setup as WAIT RETEST, NO CHASE, or a new breakout-retest setup.

## Position Status Rules

Use position status as an additional field, not as a replacement for setup state.

The Pine/map logic must separate:

- Setup State: what price has done relative to the plan.
- Position Status: whether the user is actually in a trade.

Do not infer that the user is in a position just because price crossed the entry, reclaim, trigger, or TP.

Default Position Status is `NO POSITION` unless the user explicitly says they entered, the exchange position is visible, or the analysis intentionally marks the setup as a simulated/assumed triggered trade.

Allowed Position Status values:

- NO POSITION
- ENTERED LONG
- ENTERED SHORT
- UR PROFIT
- UR LOSS
- TP HIT / MANAGE
- SL HIT
- N/A

For longs:

- If Position Status is ENTERED LONG, price above actual entry = UR PROFIT.
- If Position Status is ENTERED LONG, price below actual entry but above invalidation = UR LOSS.

For shorts:

- If Position Status is ENTERED SHORT, price below actual entry = UR PROFIT.
- If Position Status is ENTERED SHORT, price above actual entry but below invalidation = UR LOSS.

Use actual entry price when known. If actual entry is unknown, use the planned entry midpoint only after the user confirms the position was entered from the planned zone.

If the setup has not entered yet, even if reclaim has happened, show Position Status as `NO POSITION` or `N/A`.

Only show Setup State = ACTIVE / MANAGE when the entry condition has been met and position confirmation exists, or when the map is explicitly tracking a simulated triggered setup.

If price has moved beyond the entry zone but no position was confirmed, show Setup State as `MISSED / NO CHASE`, `WAIT RETEST`, or `RECLAIMED / WAIT RETEST`; do not show UR PROFIT or UR LOSS.

If TP or SL has already been hit, prioritize TP HIT / MANAGE or INVALID over unrealized status.

## Chart Cleanup Gate

Before drawing:

- Treat any visible AutoTrader map whose table coin does not match the current chart symbol as stale by definition.
- Preserve valid existing analysis that belongs to the current chart symbol.
- Hide, remove, or update only drawings/maps that belong to another coin or that conflict with the current analysis.
- Do not wipe a coin's own prior analysis just because a new coin is being analyzed elsewhere.
- Do not leave old wrong-coin levels on the new chart.
- Do not add new markings until the chart is clean.
- If old objects cannot be removed reliably, say so clearly before drawing.

If an old same-coin direction conflicts with the new direction, update or replace that coin's map after explaining the lifecycle change.

If an old wrong-coin direction conflicts with the new chart and cannot be removed or hidden, do not draw a new map on top of it unless the user approves.

If multiple AutoTrader Trade Map indicators are visible and the stale one cannot be safely identified, stop and state `STALE MAP RISK`.

## Per-Coin Persistence And Symbol-Safety Rule

The desired behavior is per-coin persistence:

- XRP analysis should remain attached to XRP.
- FARTCOIN analysis should remain attached to FARTCOIN.
- AVAX analysis should remain attached to AVAX.
- When switching away and later returning to a coin, that coin's own prior analysis should still be visible unless it has been updated, invalidated, or deliberately removed.
- Analysis from one coin must not appear on another coin.

Persistence comes from `SETUP_LEDGER.json`, not from TradingView. Pine is only a renderer. The preferred display is one multi-symbol AutoTrader map whose guarded slots are generated from the current active ledger records.

For every `Analyze [coin]` request:

1. Switch/open the requested symbol first.
2. Immediately inspect visible AutoTrader tables, labels, lines, and drawings.
3. Load the coin's ledger entry and decide whether it is still active, hit TP/SL, invalidated, missed, or needs an update.
4. If the visible analysis belongs to a different coin, hide/remove/update that wrong-coin display before analyzing the current coin.
5. Do not summarize the new coin while another coin's entry, SL, TP, trigger, or table is visible.
6. After updating the ledger and rendering, verify the visible map/drawings match the current symbol and ledger entry.

If the map cannot be reset, updated, hidden, or removed, final output must start with `STALE MAP RISK`.

When leaving a completed analysis, the ledger entry must remain saved even if TradingView later hides the visual map.

## Pine Indicator Rule

Use Pine cautiously because a single Pine instance is layout-wide. The safe pattern is one multi-symbol map with a strict symbol guard per coin slot.

Preferred Pine workflow:

1. Use `AUTOTRADER_TRADE_MAP_TEMPLATE.pine` as the reusable multi-symbol renderer.
2. Generate or update Pine slots from the active records in `SETUP_LEDGER.json`.
3. Each slot must have a strict `syminfo.ticker == coin` guard.
4. When the chart is XRP, only the XRP slot should render; when AVAX, only AVAX; when DOGE, only DOGE.
5. Reanalysis updates that coin's ledger record and that coin's Pine slot only.
6. Do not create duplicate/conflicting AutoTrader map indicators unless the user approves.

Do not overwrite the ledger entry for another coin to analyze the current coin.

Do not rewrite the script for every coin unless the indicator itself needs improvement.

If Pine Editor cannot be opened or updated, say so clearly.

If old Pine levels from a previous coin are visible on the current coin, hide/remove them before analysis.

If the existing Pine map cannot render the current ledger entry, say that the display failed and keep the ledger as the source of truth.

The Pine map must include a symbol guard:

- Compare the current chart symbol to each slot's coin.
- If they do not match, that slot must not plot, label, or table.
- Do not show a full old setup table on the wrong coin.
- If a minimal warning is needed, show only `STALE MAP - UPDATE COIN`.

Keep Pine status-line text quiet so the indicator name/inputs do not overlap the top-right summary table.

If possible, make the setup-state label update dynamically when reclaim, TP, or invalidation conditions are met.

## Pine Map Requirements

The Pine map should show only the current setup:

- Coin.
- Trade Type: Scalp or Intraday.
- Direction: Long, Short, or Wait.
- Setup Rating: Clean Trade, Conditional Trade, Watch Only, or Skip / No Trade, if space allows.
- Setup State.
- Position Status: NO POSITION, ENTERED LONG, ENTERED SHORT, UR PROFIT, UR LOSS, or N/A.
- Entry zone as two labeled horizontal lines by default.
- No shaded risk/reward zones unless explicitly requested.
- SL / invalidation line.
- TP1 / TP2 lines, optional TP3.
- Trigger / reclaim / break-retest line.
- Compact right-side labels.
- Status labels only when useful.
- Small summary table only if it does not cover price action.
- No long status-line string that overlaps the chart or summary table.

If a confirmed position is active, combine setup state and live P/L into one compact on-chart label, for example ACTIVE / MANAGE / UR PROFIT.

If no position is confirmed, the chart label should say NO POSITION, WAIT RETEST, WAIT RECLAIM, MISSED / NO CHASE, or ENTRY AREA instead of UR PROFIT / UR LOSS.

Do not add a separate floating UR PROFIT / UR LOSS label if it can be included in the active/manage label.

The active/manage label should track the current market price, not sit at a fixed old level.

Level lines should extend slightly forward so the right-side labels touch or nearly touch their lines.

If no setup:

- Direction = Wait.
- Mark only the key decision level if useful.
- Otherwise leave the chart clean.

## Color Rules

- Red = supply, resistance, short zones, SL/invalidation, short TP.
- Green = demand, long zones, bullish reaction zones, long TP.
- Blue = reclaim, trigger, confirmation, break/retest.
- Grey = deep liquidity or backup targets.

## Label Rules

Use compact labels only:

- SL 0.545
- SHORT TOP 72
- SHORT BOTTOM 71.2
- LONG TOP 0.43
- LONG BOTTOM 0.42
- RECLAIM 0.545
- TRIGGER < 68.95
- TP1 68
- TP2 64
- INVALID < 0.42
- NO CHASE
- RECLAIMED / WAIT RETEST
- WAIT REJECTION
- WAIT REACTION
- WAIT RECLAIM
- WAIT / SKIP
- ACTIVE / MANAGE / UR PROFIT
- ACTIVE / MANAGE / UR LOSS
- UR PROFIT
- UR LOSS

## Chart Display Rules

- Clean chart first, summary second.
- Close Pine Editor/indicator panel when finished.
- Final view should be the chart, not code.
- Use the minimum markings needed to understand the setup.
- Do not clutter the chart with every possible level.
- Prefer clear labeled horizontal lines over boxes.
- Do not use large shaded risk/reward boxes by default.
- Only use a small clearly labeled zone box when the level cannot be understood with two horizontal lines.
- Always indicate whether the setup is a Scalp or Intraday trade.

## Post-Drawing Verification Gate

Verification is an observed action, not a recollection. After saving/closing the Pine Editor:

1. Close the Pine Editor and bring the chart into full view.
2. Take a fresh screenshot or read of the rendered chart. Do not rely on the values typed into the editor or the ledger record alone; read what is actually displayed.
3. Read the rendered card/labels and compare each field, one by one, against the ledger record that was just written:
   - Coin and trade type.
   - Direction / proposed type.
   - Setup state and position status.
   - Entry, SL, TP levels (on-chart lines/labels).
   - R:R values.
   - Updated/analyzed timestamp.
4. Confirm no old conflicting levels or wrong-coin drawings are visible.
5. Only after this observed field-by-field match may the normal output format be presented as completed and verified.

If any field does not match on the observed re-check, state `CHART VERIFICATION FAILED`, name the exact field(s) that disagree, and do not present the setup as completed.

## Pine Script Corruption Recovery

Symptom: the indicator legend shows a red warning icon with `Compilation error: Script could not be translated from: <garbage string>`, or the Pine Editor content itself is a short random string instead of real code. This is not a chart-side drawing failure; the script's saved source is corrupted. A page reload alone does not fix it, and saving a corrected script does not automatically reattach it to a chart if the broken instance was removed.

Recovery sequence:

1. Reload the chart tab. This flushes stale/ghost indicator renders that persist in the legend after removal but do not appear in the Object Tree - do not trust the legend alone as a sign an old instance still exists; check the Object Tree.
2. Reopen the Pine Editor for the script. Confirm the corruption by inspecting the actual line content, not just the error banner.
3. Select all and replace with the correct script using a real paste event: write the correct content to the OS clipboard and paste natively. If clipboard permission is unavailable in the automation context, dispatch a synthetic `ClipboardEvent('paste', ...)` on the editor's `.inputarea` element with a `DataTransfer` payload as a fallback - typing character-by-character risks Monaco auto-close corruption on a 200+ line ternary-heavy file.
4. Save, then explicitly use the editor's "Add to chart" action. Saving a script does not reattach it if no instance is currently on the chart.
5. Run the full Post-Drawing Verification Gate: fresh screenshot, read the rendered card, confirm every field against the ledger. Do not conclude success from the absence of an error icon alone; confirm the card and lines actually render with correct values.

If any step cannot be completed, do not silently continue: state `STALE MAP RISK` or `CHART NOT MARKED` per the Failure Protocol below, and journal the incident with mistake tag `PINE_SCRIPT_CORRUPTED` - this is a technical incident, not a trading mistake, and should not count against thesis accuracy.

## Failure Protocol

If chart marking fails:

- Start final answer with `CHART NOT MARKED`.
- Explain why marking failed.
- Do not give the normal trade-analysis output.
- You may still give the setup levels, but label them `SETUP ONLY - NOT DRAWN ON TRADINGVIEW`.
- Offer to redraw the setup from the ledger when chart control is available.
- Do not imply the chart was updated.

If cleanup fails:

- Start final answer with `STALE MAP RISK`.
- Explain what could not be removed.
- Do not draw conflicting new levels unless the user approves.

If verification fails:

- Start final answer with `CHART VERIFICATION FAILED`.
- Explain what does not match.
- Do not give the normal trade-analysis output.
- You may still give the setup levels, but label them `SETUP ONLY - NOT VERIFIED ON TRADINGVIEW`.
- Offer to redraw the setup from the ledger when chart control is available.

## Trade Rules

- R:R is measured from the conservative edge of the entry zone (entry high for longs, entry low for shorts) to each TP against the SL. Confirmation fills happen at the edge, so midpoint math flatters the ratio; never use the midpoint for the floor check.
- Scalp floor: TP1 at least 1:1.5, and TP2 placed at structure inside the 1:2.5 to 1:3.5 band.
- Intraday floor: TP1 at least 1:2, and TP2 placed at structure inside the 1:3 to 1:4 band.
- If TP1 is below the floor, cap the setup rating at Watch Only or Skip / No Trade.
- If TP2 falls outside the band, re-place it at the nearest structural level inside the band; if no structural level exists there, the setup does not fit the template. Never move a TP into empty air to hit a ratio.
- Store rr_tp1 and rr_tp2 in the ledger record for every setup.
- Do not force a trade.
- If no clean setup exists, say WAIT.
- Even when saying WAIT, always state the proposed trade type:
  - Proposed Long
  - Proposed Short
  - Proposed Wait / No Trade

## Entry Style

Suggest the best entry style:

- Limit at zone.
- Rejection candle.
- Break-and-retest.

Also state the activation basis:

- Entry-zone activation.
- Reclaim-entry activation.
- Rejection candle activation.
- Break-and-retest activation.
- No entry yet.

## Risk Context

Position size is optional unless the user asks.

The user may use 1.5% of available balance per trade.

Optional risk rules:

- Max 1-2 open trades.
- Max daily loss 3%.
- Stop after 2 losses in a row.

## Output Format

After marking and verifying the chart, summarize like this:

Trade Type:
Proposed Type:
Coin:
Bias:
BTC/ETH Filter:
Catalyst:
Setup Type:
Setup Rating:
Setup State:
Position Status:
Main Setup:
Entry:
Activation Basis:
SL:
SL Quality:
TP:
R:R:
Entry Style:
Invalidation:
Nearest Liquidity:
Reclaim Status:
Relative Strength:
Alternate Setup:
Final Action:
Final Prediction:

Optional journal line:

Journal Tag:

## Important

If the trade is not ready, still show the conditional setup levels and clearly label WAIT, WAIT / SKIP, or NO CHASE.

Do not force a trade.

Do not leave previous drawings or old coin levels on the chart.

Clean chart first, summary second.

If chart cleanup, marking, or verification fails, do not provide the normal final output format as completed work. Use the failure protocol, include the setup only if clearly labeled as not drawn/verified on TradingView, and offer to redraw from the ledger.
