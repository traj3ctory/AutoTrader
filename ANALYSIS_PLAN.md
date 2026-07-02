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
   - Intraday: 1D -> 4H -> 1H.
   - Scalp: 1H -> 15m -> 5m.
9. Classify setup lifecycle.
10. Select one primary setup type.
11. Define entry activation basis.
12. Define entry, SL, TP, liquidity, invalidation, R:R, and SL quality.
13. Rate the setup.
14. Decide final action.
15. Update `SETUP_LEDGER.json`.
16. Draw or update the current TradingView map from the ledger.
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
- After live chart analysis, update the ledger before rendering the chart.
- If TradingView fails to render, the ledger still remains the saved setup state.

Never treat TradingView Pine/drawings as the memory source. They are only the display layer.

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

TradingView Pine indicators can follow the layout across symbols and may cache or hide levels when switching. Persistent coin-specific analysis comes from `SETUP_LEDGER.json`, not from Pine.

For every new `Analyze [coin]` request:

1. Switch/open the requested symbol first.
2. Inspect visible Codex tables, labels, lines, and drawings.
3. Read the coin's ledger entry and classify its lifecycle.
4. If the visible analysis belongs to another coin, hide/remove/update that wrong-coin display before analysis.
5. Never summarize a new coin while another coin's map is visible.
6. After drawing, verify the visible map/drawings match the current chart symbol and ledger entry.

If the map cannot be reset, updated, hidden, or removed, stop with `STALE MAP RISK`.

When using Pine, include a symbol guard when possible:

- Compare the current chart symbol to the map coin input.
- If they do not match, delete/hide all Codex lines and labels.
- Do not show a full old setup table on the wrong coin.
- If a warning is needed, show only `STALE MAP - UPDATE COIN`.

Do not rely on one layout-wide Pine instance for persistent multi-coin analysis. Use the ledger for persistence and redraw the current symbol as needed.

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
- Calculate R:R.

If proper SL makes R:R worse than 1:2, mark WAIT / SKIP.

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

Before final answer, verify:

- Coin is correct.
- Timeframe is correct.
- Trade type is correct.
- Direction matches output.
- Entry matches output.
- SL matches output.
- TP matches output.
- Trigger/reclaim matches output.
- Setup state matches output.
- No old conflicting levels are visible.
- Pine Editor is closed.
- Final view is the chart.

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

- At least 30 reviewed setups are journaled.
- No repeated confusion between reclaim and entry.
- No repeated stale-map mistakes.
- The catalyst/news gate was applied on each review.
- Each setup has rating and final action.
- Each setup has a clear activation basis.
- Alerts can be expressed as strict pass/fail rules.
- Outcomes are reviewed as Win, Loss, Missed, No Trade, or Invalidated.
