# Trading Workflow Handover

This handover explains how to continue the TradingView analysis system on a new device or in a new AutoTrader thread.

## Core Principle

AutoTrader remembers. TradingView displays.

TradingView/Pine is not the source of truth because it can lose, hide, duplicate, or cache old maps when switching symbols. The source of truth is the local ledger file.

## Files To Move Together

Move these files as a set:

- `ANALYZE_PROMPT.md`
- `ANALYSIS_PLAN.md`
- `SETUP_LEDGER.json`
- `SCORECARD.json`
- `scripts/buildTradeMap.mjs`
- `scripts/buildScorecard.mjs`
- `scripts/scanMovers.mjs`
- `AUTOTRADER_TRADE_MAP_TEMPLATE.pine`
- `HANDOVER_TRADING_WORKFLOW.md`

Recommended folder:

```text
AutoTrader/
```

## What Each File Does

`ANALYZE_PROMPT.md`

- The main behavior prompt.
- Defines the trading framework, output format, chart cleanup rules, entry activation rules, and ledger-first process.

`ANALYSIS_PLAN.md`

- The operating checklist for every `Analyze COIN` request.
- Controls execution order: read chart, read ledger, analyze, update ledger, render chart, verify, summarize.

`SETUP_LEDGER.json`

- The trade memory file.
- Stores current setup state per coin.
- Keeps entries, SL, TP, reclaim, setup state, position status, catalyst state, and notes.
- This replaces TradingView/Pine as memory.

`AUTOTRADER_TRADE_MAP_TEMPLATE.pine`

- The reusable TradingView renderer.
- It should display only the current coin setup.
- Update its inputs/script from `SETUP_LEDGER.json`.
- It is not the memory layer.

`HANDOVER_TRADING_WORKFLOW.md`

- This file.
- Read it first when moving device/thread.

## Current Ledger Entries

Do not trust this file for coin lists or setup states; it goes stale. The current coin list, per-setup state, and `analyzed_at` timestamps live only in `SETUP_LEDGER.json` — read it directly.

## Morning Scan (Scheduled Task)

A scheduled task `daily-mover-scan` runs weekdays ~10:30 AM local (task file: `~/.claude/scheduled-tasks/daily-mover-scan/SKILL.md`, not part of this repo). It produces a pre-market triage report in chat - report only, no ledger writes, no Pine redraw.

- `scripts/scanMovers.mjs` is the data source for the "outside movers" half of the scan: pulls Bybit's public perpetuals ticker feed (no auth), excludes BTC/ETH and thin-volume symbols (<$3M 24h turnover), ranks top 10 gainers/losers, flags anything already in `SETUP_LEDGER.json`, writes `MOVER_SCAN.md`.
- The scheduled task itself does more than run that script: it also reads the active ledger/watchlist, applies the full `ANALYZE_PROMPT.md` ruleset (validity gate, no-chase, entry activation, SL quality, catalyst gate, R:R floors, Parabolic Spike Rule) to watchlist coins, and TradingView-verifies any outside mover before it's allowed into the ranked candidate list. Movers that can't be chart-verified go in a separate "Unverified Outside Movers" bucket, never the ranked list.
- If TradingView/Chrome is inaccessible during a run, the task states that limitation and falls back to a source-limited scan from the ledger and Bybit data alone - it does not pretend chart verification happened.
- To change the schedule or prompt, use the scheduled-tasks tools (`list_scheduled_tasks` / `update_scheduled_task`), not a manual edit of the SKILL.md file.

## Ledger Size

Keep active `setups` lean, target roughly 10-15 coins max. This is a scannable watchlist, not an archive. The moment a setup goes dead (SL tagged, TP tagged, missed, invalidated), journal it with a mistake tag and delete it from `setups` in the same pass — do not let dead entries accumulate. A bloated `setups` object makes every priority check slower and defeats the point of the ledger being glanceable. `Pine` script size scales with active-setup count (~2.3KB per coin in the ternary chains); this is not a near-term technical limit, but ledger hygiene matters well before script size would.

## Timeframe Stacks

- Intraday: 1D -> 4H -> 1H, entry planned on 1H, trigger confirmation on 15m or 1H closes.
- Scalp: 4H veto -> 1H -> 15m -> 5m, entry planned on 5m.
- Scalps must check 4H supply/demand before mapping any levels. See the Timeframe Rules and R:R floors in `ANALYZE_PROMPT.md`.
- R:R floors: Scalp TP1 >= 1.5R with TP2 in the 2.5-3.5R band; Intraday TP1 >= 2R with TP2 in the 3-4R band.
- R:R is measured from the conservative entry-zone edge (entry high for longs, entry low for shorts), not the midpoint.

## Required Analyze Workflow

When the user says:

```text
Analyze COIN
```

Do this:

1. Open/switch TradingView to the requested Bybit perpetual symbol.
2. Read `SETUP_LEDGER.json`.
3. Find the coin entry if it exists.
4. Inspect the live TradingView chart.
5. Decide if the old ledger setup is still valid, missed, invalidated, active, or needs refresh.
6. Update `SETUP_LEDGER.json` before drawing.
7. Render the current coin only using `AUTOTRADER_TRADE_MAP_TEMPLATE.pine` or a TradingView map.
8. Verify chart map matches the ledger.
9. Close Pine Editor/panels.
10. Final answer uses the required output format.

## Current Pine Handoff Process

The active operating process is:

```text
AutoTrader analyzes -> AutoTrader updates SETUP_LEDGER.json -> AutoTrader rebuilds AUTOTRADER_TRADE_MAP_TEMPLATE.pine -> user pastes Pine into TradingView -> user says "confirm" -> AutoTrader verifies the rendered TradingView chart
```

Do not call the job complete just because the Pine file was regenerated. Completion requires either chart verification or a clear manual-paste handoff.

For manual paste handoff:

1. Run `node scripts/buildTradeMap.mjs`.
2. Confirm the generated Pine contains the expected setup state/timestamp using `rg`.
3. Tell the user to paste `AUTOTRADER_TRADE_MAP_TEMPLATE.pine`.
4. After the user says `confirm`, inspect the visible TradingView card and compare it to `SETUP_LEDGER.json`.

If the TradingView card still shows old values after paste, the file may be correct while the old indicator instance is still cached. In that case, tell the user to remove the existing `AutoTrader Trade Map` indicator, save the Pine script, and add it back to the chart.

As of the 2026-07-13 watchlist refresh:

- `JTOUSDT.P` should show `Cond. Long · Watch Only`, `WAIT REACTION · NO POSITION`, `2.0R / 3.0R`, updated `Jul 13 · 12:18`.
- `XRPUSDT.P` should show `Cond. Long · Watch Only`, `WAIT RECLAIM · NO POSITION`, `2.3R / 3.7R`, updated `Jul 13 · 12:18`.
- If XRP shows `RECLAIMED / WAIT RETEST`, `Jul 10 · 09:25`, or `SL TAGGED · Jul 13 04:00`, TradingView is still running the stale indicator instance.

## Important State Rules

Setup state and position state are separate.

Setup State examples:

- `WAIT RECLAIM`
- `WAIT RETEST`
- `ENTRY AREA`
- `TRIGGERED`
- `MISSED / NO CHASE`
- `ACTIVE / MANAGE`
- `TP HIT / MANAGE`
- `INVALID`

Position State examples:

- `NO POSITION`
- `ENTERED LONG`
- `ENTERED SHORT`
- `UR PROFIT`
- `UR LOSS`
- `CLOSED`

Never show `UR PROFIT` or `UR LOSS` unless there is a confirmed entry.

Confirmed entry means one of:

- User says they entered.
- Exchange position is visible.
- The analysis explicitly marks a simulated/assumed entry.

If price moves past the entry zone but no entry was confirmed, use:

- `MISSED / NO CHASE`
- `WAIT RETEST`
- `RECLAIMED / WAIT RETEST`
- `NO POSITION`

## TradingView Rendering Rules

TradingView is display only.

If TradingView fails to show the setup:

- Do not invent memory from the chart.
- Do not overwrite unrelated coin ledger entries.
- Keep the ledger updated.
- Final answer starts with `CHART NOT MARKED` or `CHART VERIFICATION FAILED`.

If TradingView shows old/wrong coin levels:

- Treat it as stale display.
- Clean or hide it if possible.
- Redraw from `SETUP_LEDGER.json`.
- If cleanup is unsafe, final answer starts with `STALE MAP RISK`.

Avoid duplicate AutoTrader maps. Prefer one reusable multi-symbol map rendered from the ledger.

The current display model is:

```text
SETUP_LEDGER.json -> scripts/buildTradeMap.mjs -> AUTOTRADER_TRADE_MAP_TEMPLATE.pine -> TradingView
```

Each active ledger coin gets one guarded Pine slot. Reanalyzing a coin updates that coin's ledger record, then rebuilds the Pine map. Switching charts should show only the matching symbol's slot.

## New Device Setup

On a new device:

1. Copy the five files listed above into the workspace.
2. Open `HANDOVER_TRADING_WORKFLOW.md`.
3. Open `ANALYZE_PROMPT.md` and `ANALYSIS_PLAN.md`.
4. Confirm `SETUP_LEDGER.json` parses as valid JSON.
5. Open TradingView and sign in.
6. Open the Bybit perpetual chart.
7. Clean duplicate/old AutoTrader maps if visible.
8. Install or update `AUTOTRADER_TRADE_MAP_TEMPLATE.pine`.
9. Test one coin from the ledger, preferably XRP.
10. Verify map levels match the ledger.

## Quick Validation

To validate the JSON ledger locally:

```bash
ruby -rjson -e 'JSON.parse(File.read("SETUP_LEDGER.json")); puts "SETUP_LEDGER.json OK"'
```

Expected:

```text
SETUP_LEDGER.json OK
```

## Failure Flags

Use these exact final-answer flags:

- `CHART NOT MARKED`: TradingView marking failed.
- `STALE MAP RISK`: old/conflicting maps cannot be safely removed.
- `CHART VERIFICATION FAILED`: visible chart does not match the ledger/written setup.

Do not silently continue when any of these are true.

## Current Known Issue

TradingView has been inconsistent with Pine rendering when switching symbols:

- AVAX sometimes appears only after refresh.
- SPORTFUN did not persist visually.
- XRP/AVAX old maps can remain visible.
- XRP specifically cached an old `RECLAIMED / WAIT RETEST` card after the Pine file had already been rebuilt to `WAIT RECLAIM`.

This is why the ledger exists. Pine is not the memory source; it is only a generated renderer. The fix is:

```text
Ledger memory -> validity gate -> generated multi-symbol renderer -> verification
```

## Future Step 2 Readiness

Do not move to alerts or auto-trading until:

- At least 30 setups counted toward the gate: correct-thesis analyses plus user-confirmed taken trades (one record counts once).
- No repeated confusion between entry, reclaim, and active trade.
- Setup outcomes are tracked as Win, Loss, Missed, No Trade, or Invalidated.
- Alerts can be expressed as strict pass/fail rules.
