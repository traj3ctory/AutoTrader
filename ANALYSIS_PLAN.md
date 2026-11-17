# Analysis Plan: Step 1 Airtight Workflow

This plan controls every `Analyze [coin]` request. It is the operating procedure for the prompt in `ANALYZE_PROMPT.md`.

## Objective

Make discretionary AutoTrader-assisted TradingView analysis consistent, clean, and reviewable before moving to alerts or auto-trading.

If switching devices or threads, read `HANDOVER_TRADING_WORKFLOW.md` before running any new analysis.

Step 1 is complete only when:

- The analysis reliably separates Fresh Setup, Active Trade, Missed Setup, TP Hit, Invalidated Setup, and Stale Map.
- The chart map is cleaned, marked, and verified before final output.
- Reclaim and entry activation are not confused.
- Each setup has Setup Type, Setup Rating, SL Quality, R:R, BTC/ETH Filter, Catalyst, Relative Strength, and Final Action.
- Failed chart operations are reported clearly instead of silently skipped.
- `SETUP_LEDGER.json` is the remembered source of truth, and TradingView is treated as the display layer.

## Gate 0: Significance Pre-Check

Before running the full Analyze Command Contract below, check whether a fresh Analyze is actually warranted:

- If the coin already has an active ledger entry with a stated trigger/confirmation level and an invalidation level, compare the current price against both before doing anything else.
- If the price sits between those two levels without clearing either one (a marginal tick, a small wick, noise around a line already flagged as unconfirmed), say so plainly and do not run the full 19-step contract on it - a full Analyze pass spent on noise is wasted effort and clutters the ledger's `analyzed_at` history with reads that changed nothing.
- Only proceed with the full contract when price has actually cleared the stated trigger or invalidation level, or when the user explicitly asks for a fresh read regardless of significance.
- Reference: 2026-07-28, DOGE ticked from 0.06993 to 0.07001 - technically "crossing" the 0.07 flip level already in the ledger, but nowhere near the stated 0.0715 confirmation threshold or the 0.0693 invalidation level from the prior pass. Correctly held off running a full Analyze on it.
- As of 2026-07-30, `level-alert-check`'s RECLAIM/ZONE/ENTRY crossings are close-confirmed with hysteresis (see `scripts/checkAlerts.mjs`), so most marginal-tick noise is already filtered before it reaches chat - a reported crossing is stronger evidence than it used to be. This gate still matters most for: SL/TP instant-ticker crossings, and multi-coin batches where several alerts land at once - check each coin's own trigger/invalidation state independently rather than defaulting to a full Analyze on every coin just because several fired together. A coin whose chart-verified state genuinely hasn't changed since the last pass gets a one-line "Still Valid" note, not a full 19-step re-derivation - full re-analysis is for when the state actually flips (reclaimed vs failed, invalidated vs active), not to re-confirm an unchanged read.

## Analyze Command Contract

When the user says `Analyze [coin]`, execute this flow:

1. Run `python3 scripts/apiAnalyze.py SYMBOL --trade-type both` for the coin (primary read since 2026-08-03; TradingView is opened only for the news check and the final Pine display).
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
16. Run `node scripts/buildTradeMap.mjs` to regenerate the Pine map, and heed its R:R warnings. If an outcome was journaled or a scorecard record added, also run `node scripts/buildScorecard.mjs`. Copy the regenerated file to the user's clipboard (`pbcopy < AUTOTRADER_TRADE_MAP_TEMPLATE.pine`) and hand it off for the user to paste themselves (manual paste is the default - see Chart Drawing Method in `ANALYZE_PROMPT.md`), do not drive the Pine Editor via browser automation.
17. After the user confirms they pasted it, verify chart map against the ledger and written levels.
18. Close Pine Editor/panels and leave chart visible.
19. Give final output in the required format, including the required Plain-English Setup Summary and image (see `ANALYZE_PROMPT.md`).

**Light Pass Mode is disabled.** Every `Analyze [coin]` request runs all 19 steps in full, every time, regardless of how recently the coin was last analyzed - see `ANALYZE_PROMPT.md`'s "Light Pass Mode - DISABLED" note. Do not skip the timeframe stack, the Pine regenerate/clipboard step, or the summary/image based on an assumption that nothing changed.

The 1D read specifically is not optional or skippable just because the ledger already has a `watch_zone` for the coin - a coin can have real daily-timeframe structure (an origin base, an old support/resistance cluster) that predates and is completely absent from the current ledger entry. Re-verifying the ledger's existing level is not the same as doing the daily read; both are required, and the daily read is what catches structure the ledger has never seen at all.

## Gate 1: Source Check

Allowed source order:

CHANGED 2026-11-16 to match the Source Of Truth section of `ANALYZE_PROMPT.md` (flipped 2026-08-03; this gate was never updated and still said chart-first):

1. `scripts/apiAnalyze.py` - replays the backtest engines on live Bybit data; its verdict (`VALID` / `ENGINE IN TRADE` / `ENGINE ORDER STILL RESTING` / `NO SIGNAL`) is the signal read, and only `VALID` is a tested entry.
2. `SETUP_LEDGER.json` for remembered per-coin setup state.
3. TradingView for the catalyst/news check and the final Pine paste-and-verify display only.
4. TradingView chart reading as a structural input only as a stated fallback when `apiAnalyze.py` cannot run for the coin.

If source access is limited, state the limitation.

SUPERSEDED 2026-08-03 (kept for history; the lesson that still applies is that higher-timeframe zones must be read, which the engine's 1D/4H/1H pass now does): Do not default to external API/kline pulls as the working source for an Analyze, even when TradingView is technically reachable - this is exactly the judgment call that caused the 2026-07-28 incident: a round of re-Analyzes on DOGE/AVAX/ZEC/JTO leaned on Bybit API kline data instead of opening the actual chart, and as a direct result JTO's real 10-day-old daily support zone (0.538-0.556, three prior touches) never got read and was missing from the ledger until the user caught it. API data is a supplement for a source-access gap the user has been told about, or something the user explicitly asks for - never the default move for a fresh Analyze.

## Gate 1A: Ledger Check

AutoTrader remembers. TradingView displays.

Before drawing or summarizing:

- Read `SETUP_LEDGER.json`.
- Locate the requested coin entry if it exists.
- Use the ledger to understand the prior setup state, position state, entry, SL, TP, reclaim, and notes - as context for what changed, never as the answer itself.
- Compare that prior setup to the current TradingView chart before drawing. This comparison requires an actual chart read this turn, not a recollection of the ledger's last values.
- After live chart analysis, update the ledger before rendering the chart.
- If TradingView fails to render, the ledger still remains the saved setup state, but say so explicitly - do not report old ledger values as if they were this turn's analysis.

Never treat TradingView Pine/drawings as the memory source. They are only the display layer. Likewise, never treat the ledger's last saved entry as a substitute for actually reading the chart on this turn's `Analyze [coin]` request, however recent that entry looks.

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

This validity gate is also the lifecycle classification - there is only one state list, not two. If the prior map has already hit TP/SL or changed direction, refresh the map before final output.

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

## Gate 3: Cleanup Check

Before drawing:

- Treat any visible AutoTrader map whose table coin does not match the current chart symbol as stale by definition.
- Preserve valid existing analysis that belongs to the current chart symbol.
- Remove, hide, or update only wrong-coin maps or same-coin maps that are stale, invalidated, or conflicting.
- Do not wipe another coin's valid analysis while analyzing the current coin.
- Do not leave wrong-coin levels on the chart.
- Do not add a new map over a conflicting old map.

If cleanup cannot be completed:

- Stop and state `STALE MAP RISK`.
- Explain what could not be removed.
- Ask for approval before adding a duplicate/conflicting map.

## Gate 3A: Per-Coin Persistence And Symbol-Safety Check

The desired behavior is per-coin persistence:

- XRP analysis remains on XRP.
- FARTCOIN analysis remains on FARTCOIN.
- AVAX analysis remains on AVAX.
- Returning to a coin should show that coin's own prior analysis unless it has been updated, invalidated, or deliberately removed.
- One coin's analysis must not appear on another coin.

Persistent coin-specific analysis comes from `SETUP_LEDGER.json`, not from Pine. Pine is only the display renderer. The preferred display is one multi-symbol AutoTrader map generated from the active ledger records.

For every new `Analyze [coin]` request:

1. Switch/open the requested symbol first.
2. Inspect visible AutoTrader tables, labels, lines, and drawings.
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

## Gate 4: Trade Type Check

Choose one:

- Scalp
- Intraday
- No Trade

The chart table must match the written trade type exactly.

## Gate 5: Setup Check

Choose one primary setup:

- Liquidity Sweep + MSS
- Failed Reclaim / Deviation
- FVG / Imbalance Retest
- Breaker / Failed Supply-Demand Flip
- Compression-to-Expansion Breakout
- Standard Supply/Demand Retest
- No Clean Setup

Optional secondary setup is allowed, but the primary setup controls entry.

## Gate 6: Activation Check

Choose one PRIMARY activation basis:

- Entry-zone activation
- Reclaim-entry activation
- Rejection candle activation
- Break-and-retest activation
- No entry yet

Reclaim alone never equals ACTIVE / MANAGE unless reclaim-entry activation is explicitly chosen.

Dual-Activation requirement: if the setup has any defined reclaim or trigger level, this gate is not satisfied by naming a primary basis alone - a secondary break-and-retest activation at that level must also be mapped, stated explicitly in the entry basis field, even when the primary basis is a deep pullback zone. Skipping this because the coin "doesn't look like it's in momentum" is exactly the judgment call that produced this rule; do not re-introduce that judgment call here.

Separate setup activation from user position confirmation:

- Price reaching a planned entry zone means `ENTRY AREA` or `TRIGGERED`, not automatically `UR PROFIT`.
- Price reclaiming a level means `WAIT RETEST` or `RECLAIMED / WAIT RETEST` unless reclaim itself is the chosen entry.
- `ACTIVE / MANAGE` requires confirmed user entry, visible exchange position, or an explicitly stated simulated/assumed entry.
- If no position is confirmed, Position Status must be `NO POSITION` or `N/A`, never `UR PROFIT` or `UR LOSS`.
- If price moves away without confirmed entry, classify as `MISSED / NO CHASE` or define a new retest setup.

## Gate 7: Risk Check

Before finalizing levels:

- Identify nearest buy-side liquidity.
- Identify nearest sell-side liquidity.
- Set SL beyond liquidity and full wick/base.
- Classify SL as Safe, Vulnerable, or Too Tight.
- Check every TP against the TP Zone Validity Rule in `ANALYZE_PROMPT.md`: no TP may span more than one demand/supply zone. Fix TP1 first if it's wrong - a TP that skips through an untested zone and lands in a second one is not a real target, no matter how good the resulting R:R looks.
- Calculate R:R from the conservative entry-zone edge (entry high for longs, entry low for shorts), never the midpoint.

Tested exit (noted 2026-11-16): both engines exit the full position at a fixed 2R, or 1.5R when that is all the room before the next opposing zone; TP2 bands and the reduced-size tier below are untested discretion and must be labelled so. Floors: Scalp TP1 >= 1.5R with TP2 in the 2.5-3.5R band; Intraday TP1 >= 2R with TP2 in the 3-4R band. If proper SL puts TP1 below the floor, mark WAIT / SKIP. If TP2 has no structural level inside the band, the setup does not fit the template.

## Gate 8: Setup Rating Check

Assign one:

- Clean Trade
- Conditional Trade
- Conditional Trade - Reduced Size
- Watch Only
- Skip / No Trade

Conditional Trade - Reduced Size applies only when TP1 is sub-floor but inside the reduced-size band (1.5-2R Intraday / 1.2-1.5R Scalp), every other gate (SL quality, confirmed trigger, catalyst, BTC/ETH filter) passes cleanly, and the activation basis has actually confirmed - see the Conditional (Reduced-Size) Tier in ANALYZE_PROMPT.md. State the half-risk sizing (0.75% instead of 1.5%) explicitly in the final output.

Rating must match action:

- Clean Trade -> Trade candidate if trigger is met.
- Conditional Trade -> Conditional trade.
- Conditional Trade - Reduced Size -> Trade candidate at half risk if trigger is met.
- Watch Only -> Wait / monitor.
- Skip / No Trade -> No trade.

## Gate 9: Pine Map Check

Preferred order:

1. Use `AUTOTRADER_TRADE_MAP_TEMPLATE.pine` as the renderer.
2. Populate it from the current coin's `SETUP_LEDGER.json` entry via `node scripts/buildTradeMap.mjs`.
3. Attempt automated drawing first, in the one persistent session tab, using the OS-level `pbcopy` + native paste method in `ANALYZE_PROMPT.md`'s Chart Drawing Method section. One retry cap on failure, then fall back to the manual handoff (`SCRIPT READY - MANUAL PASTE REQUIRED` + compact analysis + visual).
4. Update one visible current-coin map only.
5. Add a new map only if no editable map exists and it will not create duplicate/conflicting levels.

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

## Gate 10: Verification Check

Verification requires an observed re-check of the rendered chart, not a restatement of what was intended. After closing the Pine Editor:

1. Take a fresh screenshot or read of the chart as it now renders.
2. Compare, field by field, against the ledger record just written: coin, trade type, direction, entry, SL, TP, trigger/reclaim, setup state, position status, R:R, analyzed timestamp.
3. Confirm no old conflicting levels or wrong-coin drawings are visible.
4. Confirm Pine Editor is closed and the final view is the chart.

Do not mark this gate passed from memory of what was typed. If any observed field disagrees with the ledger, the gate fails.

If verification fails, state `CHART VERIFICATION FAILED`.

## Gate 10A: Pine Script Corruption Check

If the indicator legend shows a compilation error referencing a short garbage string, the saved script source is corrupted, not just the chart drawing. See "Pine Script Corruption Recovery" in `ANALYZE_PROMPT.md` for the full recovery sequence: reload, verify corruption in the editor, replace via a real paste event (or synthetic ClipboardEvent fallback), save, explicitly Add to chart, then re-run Gate 10 in full. Journal the incident with mistake tag `PINE_SCRIPT_CORRUPTED` - technical, not a trading mistake.

## Gate 11: Failure Protocol

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
