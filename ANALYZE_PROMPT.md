# Analyze Prompt: TradingView Crypto Perpetual Futures

Use this prompt to analyze crypto perpetual futures on Bybit using TradingView.

This is Step 1 of the roadmap: make the analysis trade like the user, then better. Treat all output as educational chart analysis, not financial advice. Do not automate alerts or auto-trade from this prompt.

## Non-Negotiable Execution Rule

The final answer is not complete unless one of these is true:

- The TradingView chart has been cleaned, marked, verified, and left on the chart view.
- Chart marking failed, and the final answer clearly starts with `CHART NOT MARKED` and explains why.

Do not give a normal final trade summary while the chart is stale, unmarked, or showing conflicting old levels.

## Source Of Truth

Use this source hierarchy:

1. Current visible TradingView chart.
2. `SETUP_LEDGER.json` for remembered setup state, prior levels, position status, and journal history.
3. TradingView tab candle stream or TradingView page data, only when visual chart access is limited.
4. External APIs only if the user explicitly asks.

If source access is limited, state the limitation before drawing or summarizing.

Do not use old screenshots, old TradingView drawings, or old visible Pine levels as the memory source. The ledger is the memory source. TradingView is only the live chart and display layer.

## Ledger Memory Rule

Codex remembers. TradingView displays.

Use `SETUP_LEDGER.json` as the source of truth for remembered per-coin analysis. For every `Analyze [coin]` request:

1. Open or switch to the current TradingView chart.
2. Read the current coin's ledger entry if one exists.
3. Analyze the live chart and decide whether the ledger setup is still valid, missed, active, TP hit, invalidated, or stale.
4. Update the ledger entry before drawing the chart.
5. Render only the current coin's setup from the ledger onto TradingView.
6. Verify that the visible TradingView map matches the ledger entry.

The ledger must store coin, exchange, trade type, proposed type, bias, BTC/ETH filter, catalyst, setup type, setup rating, setup state, position status, direction, entry, activation basis, actual entry if known, reclaim/trigger, SL, SL quality, TP, invalidation, liquidity, relative strength, final action, and notes.

If TradingView fails to render the map, do not lose the setup. Keep the ledger updated and start final output with `CHART NOT MARKED` or `CHART VERIFICATION FAILED`.

Do not treat TradingView Pine/drawings as persistent memory. If TradingView loses or hides a setup during symbol switching, redraw it from the ledger.

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

- Normal intraday/day trade: use 1D -> 4H -> 1H, with entry planned on 1H.
- Scalp: use 1H -> 15m -> 5m, with entry planned on 5m.

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
- R:R is at least 1:2.5.
- BTC/ETH are aligned or not strongly conflicting.
- Entry is not late.

Conditional Trade:

- Valid setup but one important weakness exists.
- R:R is at least 1:2.
- SL is Safe or Vulnerable, not Too Tight.
- Confidence is reduced, but setup can remain conditional.

Watch Only:

- Watch only.
- Useful levels exist, but trade is not ready.
- Needs reclaim, retest, rejection, MSS, or better R:R.

Skip / No Trade:

- No clean invalidation.
- SL is Too Tight.
- Proper structural SL makes R:R worse than 1:2.
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
- If FVG entry makes SL too tight or structural SL worsens R:R below 1:2, mark WAIT / SKIP.

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
- If the proper structural SL makes R:R worse than 1:2, mark WAIT / SKIP.
- Always classify SL Quality as Safe, Vulnerable, or Too Tight.

## Extension And Chase Rules

- Do not chase price.
- If the coin has already made a strong extended move, do not use blind limit entry.
- For extended coins, require a rejection candle, reclaim, or break-and-retest before entry.
- If price has already rejected the trigger/reclaim level, downgrade the setup to WAIT until demand/supply confirms.
- If setup is late, clearly label NO CHASE.

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

- Treat any visible Codex map whose table coin does not match the current chart symbol as stale by definition.
- Preserve valid existing analysis that belongs to the current chart symbol.
- Hide, remove, or update only drawings/maps that belong to another coin or that conflict with the current analysis.
- Do not wipe a coin's own prior analysis just because a new coin is being analyzed elsewhere.
- Do not leave old wrong-coin levels on the new chart.
- Do not add new markings until the chart is clean.
- If old objects cannot be removed reliably, say so clearly before drawing.

If an old same-coin direction conflicts with the new direction, update or replace that coin's map after explaining the lifecycle change.

If an old wrong-coin direction conflicts with the new chart and cannot be removed or hidden, do not draw a new map on top of it unless the user approves.

If multiple Codex Trade Map indicators are visible and the stale one cannot be safely identified, stop and state `STALE MAP RISK`.

## Per-Coin Persistence And Symbol-Safety Rule

The desired behavior is per-coin persistence:

- XRP analysis should remain attached to XRP.
- FARTCOIN analysis should remain attached to FARTCOIN.
- AVAX analysis should remain attached to AVAX.
- When switching away and later returning to a coin, that coin's own prior analysis should still be visible unless it has been updated, invalidated, or deliberately removed.
- Analysis from one coin must not appear on another coin.

Persistence comes from `SETUP_LEDGER.json`, not from TradingView. TradingView Pine indicators can follow the layout across symbols and may cache or render inconsistently while switching. Do not rely on Pine as per-coin memory.

For every `Analyze [coin]` request:

1. Switch/open the requested symbol first.
2. Immediately inspect visible Codex tables, labels, lines, and drawings.
3. Load the coin's ledger entry and decide whether it is still active, hit TP/SL, invalidated, missed, or needs an update.
4. If the visible analysis belongs to a different coin, hide/remove/update that wrong-coin display before analyzing the current coin.
5. Do not summarize the new coin while another coin's entry, SL, TP, trigger, or table is visible.
6. After updating the ledger and rendering, verify the visible map/drawings match the current symbol and ledger entry.

If the map cannot be reset, updated, hidden, or removed, final output must start with `STALE MAP RISK`.

When leaving a completed analysis, the ledger entry must remain saved even if TradingView later hides the visual map.

## Pine Indicator Rule

Use Pine cautiously because a single Pine instance is layout-wide and can leak or hide levels across symbols.

Preferred Pine workflow:

1. Use `CODEX_TRADE_MAP_TEMPLATE.pine` as the reusable renderer.
2. Update the indicator inputs/script for the current coin from `SETUP_LEDGER.json`.
3. Show only the current coin's map.
4. Do not rely on Pine to remember multiple coins.
5. Do not create duplicate/conflicting Codex map indicators unless the user approves.

Do not overwrite the ledger entry for another coin to analyze the current coin.

Do not rewrite the script for every coin unless the indicator itself needs improvement.

If Pine Editor cannot be opened or updated, say so clearly.

If old Pine levels from a previous coin are visible on the current coin, hide/remove them before analysis.

If the existing Pine map cannot render the current ledger entry, say that the display failed and keep the ledger as the source of truth.

The Pine map should include a symbol guard when possible:

- Compare the current chart symbol to the map coin input.
- If they do not match, delete/hide all Codex lines and labels instead of showing old levels.
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

Before final answer, verify:

- Correct coin.
- Correct timeframe.
- Correct trade type.
- Chart table trade type matches written trade type.
- Chart direction matches written proposed type.
- Chart labels match written entry, SL, TP, trigger/reclaim, and state.
- No old conflicting levels are visible.
- Pine Editor is closed.
- Final view is the chart.

If verification fails, state `CHART VERIFICATION FAILED` and explain what failed.

## Failure Protocol

If chart marking fails:

- Start final answer with `CHART NOT MARKED`.
- Explain why marking failed.
- Give levels in text only.
- Do not imply the chart was updated.

If cleanup fails:

- Start final answer with `STALE MAP RISK`.
- Explain what could not be removed.
- Do not draw conflicting new levels unless the user approves.

If verification fails:

- Start final answer with `CHART VERIFICATION FAILED`.
- Explain what does not match.
- Give corrected levels in text.

## Trade Rules

- Prefer at least 1:2 R:R.
- Ideal setups are closer to 1:3.5 or 1:4 when structure supports it.
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

If chart cleanup, marking, or verification fails, say so clearly before giving the text-only summary.
