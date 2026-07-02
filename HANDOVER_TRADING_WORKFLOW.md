# Trading Workflow Handover

This handover explains how to continue the TradingView analysis system on a new device or in a new Codex thread.

## Core Principle

Codex remembers. TradingView displays.

TradingView/Pine is not the source of truth because it can lose, hide, duplicate, or cache old maps when switching symbols. The source of truth is the local ledger file.

## Files To Move Together

Move these files as a set:

- `ANALYZE_PROMPT.md`
- `ANALYSIS_PLAN.md`
- `SETUP_LEDGER.json`
- `CODEX_TRADE_MAP_TEMPLATE.pine`
- `HANDOVER_TRADING_WORKFLOW.md`

Recommended folder:

```text
chrome-analyze-epic-on-the-current/
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

`CODEX_TRADE_MAP_TEMPLATE.pine`

- The reusable TradingView renderer.
- It should display only the current coin setup.
- Update its inputs/script from `SETUP_LEDGER.json`.
- It is not the memory layer.

`HANDOVER_TRADING_WORKFLOW.md`

- This file.
- Read it first when moving device/thread.

## Current Ledger Entries

The current ledger contains:

- `XRPUSDT.P`
- `AVAXUSDT.P`
- `SPORTFUNUSDT.P`
- `FARTCOINUSDT.P`

Current status pattern:

- XRP: `WAIT RETEST`, `NO POSITION`
- AVAX: `WAIT RECLAIM`, `NO POSITION`
- SPORTFUN: `WAIT RETEST`, `NO POSITION`
- FARTCOIN: `WAIT REACTION`, `NO POSITION`, legacy setup needing fresh review

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
7. Render the current coin only using `CODEX_TRADE_MAP_TEMPLATE.pine` or a TradingView map.
8. Verify chart map matches the ledger.
9. Close Pine Editor/panels.
10. Final answer uses the required output format.

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

Avoid duplicate Codex maps. Prefer one reusable multi-symbol map rendered from the ledger.

The current display model is:

```text
SETUP_LEDGER.json -> scripts/buildTradeMap.mjs -> CODEX_TRADE_MAP_TEMPLATE.pine -> TradingView
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
7. Clean duplicate/old Codex maps if visible.
8. Install or update `CODEX_TRADE_MAP_TEMPLATE.pine`.
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

This is why the ledger exists. Pine is not the memory source; it is only a generated renderer. The fix is:

```text
Ledger memory -> validity gate -> generated multi-symbol renderer -> verification
```

## Future Step 2 Readiness

Do not move to alerts or auto-trading until:

- At least 30 reviewed setups are journaled.
- No repeated confusion between entry, reclaim, and active trade.
- Setup outcomes are tracked as Win, Loss, Missed, No Trade, or Invalidated.
- Alerts can be expressed as strict pass/fail rules.
