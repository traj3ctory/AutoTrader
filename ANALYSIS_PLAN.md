# Analysis Plan: Step 1 Airtight Workflow

This plan controls every `Analyze [coin]` request. It is the operating procedure for the prompt in `ANALYZE_PROMPT.md`.

## Objective

Make discretionary Codex-assisted TradingView analysis consistent, clean, and reviewable before moving to alerts or auto-trading.

If switching devices or threads, read `HANDOVER_TRADING_WORKFLOW.md` before running any new analysis.

Step 1 is complete only when:

- The analysis reliably separates Fresh Setup, Active Trade, Missed Setup, TP Hit, Invalidated Setup, and Stale Map.
- The chart map is cleaned, marked, and verified before final output.
- Reclaim and entry activation are not confused.
- Each setup has Setup Type, Setup Rating, SL Quality, R:R, BTC/ETH Filter, Catalyst, Relative Strength, and Final Action.
- Failed chart operations are reported clearly instead of silently skipped.
- `SETUP_LEDGER.json` is the remembered source of truth, and TradingView is treated as the display layer.

## Analyze Command Contract

When the user says `Analyze [coin]`, execute this flow:

1. Open or switch to the TradingView chart for the coin.
2. Read the coin's existing entry from `SETUP_LEDGER.json`, if any.
3. Clean or inspect existing drawings and Pine maps.
4. If stale/conflicting objects exist, classify the chart as `Stale Map / Needs Cleanup`.
5. Check BTCUSDT and ETHUSDT as filters.
6. Check the catalyst/news gate; if a high-impact event or breaking headline is imminent, cap the action at Wait or No Chase.
7. Choose trade type: Scalp, Intraday, or No Trade.
8. Read required timeframes:
   - Intraday: 1D -> 4H -> 1H, entry planned on 1H, trigger confirmation on 15m or 1H closes.
   - Scalp: 4H (supply/demand veto only) -> 1H -> 15m -> 5m, entry planned on 5m.
   - Scalps must mark 4H supply/demand before mapping any levels; a scalp into an opposing 4H zone is capped at Watch Only.
9. Classify setup lifecycle.
10. Select one primary setup type.
11. Define entry activation basis.
12. Define entry, SL, TP, liquidity, invalidation, R:R, and SL quality.
13. Rate the setup.
14. Decide final action.
15. Update `SETUP_LEDGER.json`, including `analyzed_at` (ISO timestamp), `activation_basis`, `rr_tp1`, and `rr_tp2`.
16. Run `node scripts/buildTradeMap.mjs` to regenerate the Pine map, and heed its R:R warnings. If an outcome was journaled or a scorecard record added, also run `node scripts/buildScorecard.mjs`. Then draw or update the current TradingView map from the regenerated template.
17. Verify chart map against the ledger and written levels.
18. Close Pine Editor/panels and leave chart visible.
19. Give final output in the required format.

## Gate 1: Source Check

Allowed source order:

1. Visible TradingView chart.
2. `SETUP_LEDGER.json` for remembered per-coin setup state.
3. TradingView tab candle stream/page data.
4. External APIs only if the user explicitly requests.

If source access is limited, state the limitation.

## Gate 1A: Ledger Check

Codex remembers. TradingView displays.

Before drawing or summarizing:

- Read `SETUP_LEDGER.json`.
- Locate the requested coin entry if it exists.
- Use the ledger to understand the prior setup state, position state, entry, SL, TP, reclaim, and notes.
- Compare that prior setup to the current TradingView chart before drawing.
- After live chart analysis, update the ledger before rendering the chart.
- If TradingView fails to render, the ledger still remains the saved setup state.

Never treat TradingView Pine/drawings as the memory source. They are only the display layer.

Ledger hygiene:

- Keep one active setup record per coin.
- Update the existing coin record in place instead of appending duplicates.
- Keep only the latest active/watch setup in `setups`.
- Move completed, invalidated, stale, TP/SL-hit, or useful review items into `journal` only when they are worth learning from.
- Keep journal entries short: coin, date, setup type, result, mistake tag, and one note.
- Replace stale levels with the fresh chart setup instead of preserving old narrative.

Ledger validity gate:

- Valid / Waiting: draw or keep the coin's slot.
- Triggered But Not Entered: update state and draw conditional management levels.
- Active / Manage: draw only if an actual entry is known or user confirms position.
- TP Hit / Manage: update state before drawing.
- SL Hit / Invalidated: update state, hide/remove setup, and journal only if useful.
- Missed / No Chase: update state and redraw as wait/no-chase or clear it.
- Failed Reclaim: update to `FAILED RECLAIM` or `WAIT RECLAIM`.
- Stale / Reanalyze: overwrite the coin's ledger record with a fresh setup.
- No Clean Setup: update to `WAIT / NO TRADE` and keep chart mostly clean.

Never draw a ledger setup just because it exists. It must pass this validity gate first.

## Gate 2: Catalyst / News Check

Before analysis, check for scheduled or breaking catalysts that can override structure:

- Macro: CPI, FOMC, jobs/NFP, major rate news.
- Coin-specific news: token unlock, exchange listing/delisting, hack/exploit, live headline, major partnership, legal/regulatory update, chain outage, governance vote, or large ecosystem event.

Classify the catalyst as:

- Clear
- News Risk
- Unverified

Rules:

- Catalyst includes news, but the source hierarchy still applies.
- If the user has not explicitly asked for external news/API checks and TradingView does not show enough news context, classify as `Unverified`.
- If a high-impact event is imminent or unfolding, mark `News Risk` and cap Final Action at Wait or No Chase, unless the user explicitly says to trade the event.
- If the catalyst cannot be verified, mark `Unverified` and say "catalyst unverified - check manually." Do not assume Clear.

## Gate 3: Lifecycle Check

Classify before analysis:

- Fresh Setup
- Existing Active Trade
- Missed Setup
- TP Hit / Manage
- Invalidated Setup
- Stale Map / Needs Cleanup

If the prior map has already hit TP/SL or changed direction, refresh the map before final output.

## Gate 4: Cleanup Check

Before drawing:

- Treat any visible Codex map whose table coin does not match the current chart symbol as stale by definition.
- Preserve valid existing analysis that belongs to the current chart symbol.
- Remove, hide, or update only wrong-coin maps or same-coin maps that are stale, invalidated, or conflicting.
- Do not wipe another coin's valid analysis while analyzing the current coin.
- Do not leave wrong-coin levels on the chart.
- Do not add a new map over a conflicting old map.

If cleanup cannot be completed:

- Stop and state `STALE MAP RISK`.
- Explain what could not be removed.
- Ask for approval before adding a duplicate/conflicting map.

## Gate 4A: Per-Coin Persistence And Symbol-Safety Check

The desired behavior is per-coin persistence:

- XRP analysis remains on XRP.
- FARTCOIN analysis remains on FARTCOIN.
- AVAX analysis remains on AVAX.
- Returning to a coin should show that coin's own prior analysis unless it has been updated, invalidated, or deliberately removed.
- One coin's analysis must not appear on another coin.

Persistent coin-specific analysis comes from `SETUP_LEDGER.json`, not from Pine. Pine is only the display renderer. The preferred display is one multi-symbol Codex map generated from the active ledger records.

For every new `Analyze [coin]` request:

1. Switch/open the requested symbol first.
2. Inspect visible Codex tables, labels, lines, and drawings.
3. Read the coin's ledger entry and classify its lifecycle.
4. If the visible analysis belongs to another coin, hide/remove/update that wrong-coin display before analysis.
5. Never summarize a new coin while another coin's map is visible.
6. After drawing, verify the visible map/drawings match the current chart symbol and ledger entry.

If the map cannot be reset, updated, hidden, or removed, stop with `STALE MAP RISK`.

When using Pine, use guarded slots:

- Compare the current chart symbol to each slot's coin.
- If a slot does not match, it must not plot, label, or table.
- Do not show a full old setup table on the wrong coin.
- If a warning is needed, show only `STALE MAP - UPDATE COIN`.

Use one multi-symbol Pine instance for display, with one guarded slot per active ledger coin. Reanalysis updates the requested coin's ledger record and that coin's Pine slot only.

## Gate 5: Trade Type Check

Choose one:

- Scalp
- Intraday
- No Trade

The chart table must match the written trade type exactly.

## Gate 6: Setup Check

Choose one primary setup:

- Liquidity Sweep + MSS
- Failed Reclaim / Deviation
- FVG / Imbalance Retest
- Breaker / Failed Supply-Demand Flip
- Compression-to-Expansion Breakout
- Standard Supply/Demand Retest
- No Clean Setup

Optional secondary setup is allowed, but the primary setup controls entry.

## Gate 7: Activation Check

Choose one activation basis:

- Entry-zone activation
- Reclaim-entry activation
- Rejection candle activation
- Break-and-retest activation
- No entry yet

Reclaim alone never equals ACTIVE / MANAGE unless reclaim-entry activation is explicitly chosen.

Separate setup activation from user position confirmation:

- Price reaching a planned entry zone means `ENTRY AREA` or `TRIGGERED`, not automatically `UR PROFIT`.
- Price reclaiming a level means `WAIT RETEST` or `RECLAIMED / WAIT RETEST` unless reclaim itself is the chosen entry.
- `ACTIVE / MANAGE` requires confirmed user entry, visible exchange position, or an explicitly stated simulated/assumed entry.
- If no position is confirmed, Position Status must be `NO POSITION` or `N/A`, never `UR PROFIT` or `UR LOSS`.
- If price moves away without confirmed entry, classify as `MISSED / NO CHASE` or define a new retest setup.

## Gate 8: Risk Check

Before finalizing levels:

- Identify nearest buy-side liquidity.
- Identify nearest sell-side liquidity.
- Set SL beyond liquidity and full wick/base.
- Classify SL as Safe, Vulnerable, or Too Tight.
- Calculate R:R from the conservative entry-zone edge (entry high for longs, entry low for shorts), never the midpoint.

Floors: Scalp TP1 >= 1.5R with TP2 in the 2.5-3.5R band; Intraday TP1 >= 2R with TP2 in the 3-4R band. If proper SL puts TP1 below the floor, mark WAIT / SKIP. If TP2 has no structural level inside the band, the setup does not fit the template.

## Gate 9: Setup Rating Check

Assign one:

- Clean Trade
- Conditional Trade
- Watch Only
- Skip / No Trade

Rating must match action:

- Clean Trade -> Trade candidate if trigger is met.
- Conditional Trade -> Conditional trade.
- Watch Only -> Wait / monitor.
- Skip / No Trade -> No trade.

## Gate 10: Pine Map Check

Preferred order:

1. Use `CODEX_TRADE_MAP_TEMPLATE.pine` as the renderer.
2. Populate it from the current coin's `SETUP_LEDGER.json` entry.
3. Update one visible current-coin map only.
4. Add a new map only if no editable map exists and it will not create duplicate/conflicting levels.

The map must include:

- Coin.
- Trade Type.
- Direction.
- Setup Rating if space allows.
- Setup State.
- Position Status.
- Entry zone.
- SL / invalidation.
- TP1 / TP2, optional TP3.
- Trigger / reclaim / break-retest.
- Compact right-side labels.
- Summary table.

Avoid shaded boxes unless explicitly requested.

## Gate 11: Verification Check

Verification requires an observed re-check of the rendered chart, not a restatement of what was intended. After closing the Pine Editor:

1. Take a fresh screenshot or read of the chart as it now renders.
2. Compare, field by field, against the ledger record just written: coin, trade type, direction, entry, SL, TP, trigger/reclaim, setup state, position status, R:R, analyzed timestamp.
3. Confirm no old conflicting levels or wrong-coin drawings are visible.
4. Confirm Pine Editor is closed and the final view is the chart.

Do not mark this gate passed from memory of what was typed. If any observed field disagrees with the ledger, the gate fails.

If verification fails, state `CHART VERIFICATION FAILED`.

## Gate 12: Failure Protocol

Use these exact flags:

- `CHART NOT MARKED`: marking failed.
- `STALE MAP RISK`: old/conflicting map could not be safely removed.
- `CHART VERIFICATION FAILED`: chart map does not match the written summary.

Never silently continue as if the chart is clean when one of these is true.

## Required Final Output

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

Optional:

Journal Tag:

## Step 1 Acceptance Criteria

Before Step 2 automated alerts:

- At least 30 setups counted toward the gate: correct-thesis analyses plus user-confirmed taken trades (one record counts once). Track progress in `SCORECARD_DASHBOARD.html` via `node scripts/buildScorecard.mjs`.
- No repeated confusion between reclaim and entry.
- No repeated stale-map mistakes.
- The catalyst/news gate was applied on each review.
- Each setup has rating and final action.
- Each setup has a clear activation basis.
- Alerts can be expressed as strict pass/fail rules.
- Outcomes are reviewed as Win, Loss, Missed, No Trade, or Invalidated.
