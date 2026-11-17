# Trading Workflow Handover

This handover explains how to continue the TradingView analysis system on a new device or in a new AutoTrader thread.

## Core Principle

AutoTrader remembers. TradingView displays.

TradingView/Pine is not the memory layer because it can lose, hide, duplicate, or cache old maps when switching symbols. The local ledger file is the memory layer.

As of 2026-08-03, TradingView is also no longer the primary *analysis* input. `scripts/apiAnalyze.py` (Bybit API - zones, structure, signal, R:R) is now primary; TradingView is used only for a catalyst/news check and the final Pine paste-and-verify display. See "Source Of Truth" in `ANALYZE_PROMPT.md` for the full rule and why it changed (repeated render failures vs. a Bybit pipeline that never once failed across a 3-month backtest).

## Files To Move Together

Move these files as a set:

- `ANALYZE_PROMPT.md`
- `ANALYSIS_PLAN.md`
- `SETUP_LEDGER.json`
- `SCORECARD.json`
- `scripts/buildTradeMap.mjs`
- `scripts/buildScorecard.mjs`
- `scripts/scanMovers.mjs`
- `scripts/checkAlerts.mjs`
- `scripts/scalpScreen.mjs`
- `scripts/strategyBacktest.py` and `scripts/scalpBacktestV3.py` (backtest engines behind the current Scalp Entry Rule in `ANALYZE_PROMPT.md` - re-run before changing scalp rules again)
- `scripts/signalScan.py` (2026-11-16 - signal scanner run as Part 2 of the `level-alert-check` scheduled task every 30 minutes; same engines as `apiAnalyze.py`, prints only signals new since the last run, state in the gitignored `.signal_state.json`; `--notify` raises a macOS notification so it can also run from cron/launchd without a Claude session)
- `scripts/apiAnalyze.py` (2026-08-03 - the primary live analysis engine; rewritten 2026-11-16 after the first version was found to apply different rules from the backtest (+0.117 avgR replayed vs +0.455 tested). It now replays `run_scalp_v3`/`run_intraday` themselves over 150 days of closed 5m candles cached in `backtests/live/data/`. Flags: several symbols, `--ledger`, `--summary`, `--trade-type scalp|intraday|both`. Only a `VALID` verdict is a tested entry. TradingView is display/news only - see Source Of Truth in `ANALYZE_PROMPT.md`)
- `backtests/` (results only - raw candle cache under `backtests/*/data/` is gitignored and rebuilds from Bybit on demand)
- `WATCHLIST_TIER2.md`
- `AUTOTRADER_TRADE_MAP_TEMPLATE.pine`
- `HANDOVER_TRADING_WORKFLOW.md`
- `Readme.md`
- `scheduled-tasks/` (the repo-tracked source of truth for `daily-mover-scan`, `level-alert-check`, `monthly-scalp-review` - see "Scheduled Tasks Are Now Repo-Tracked" below)

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

`WATCHLIST_TIER2.md`

- A lighter-weight tier below the ledger: coins worth watching that aren't in the core 6 and aren't polled by `level-alert-check`.
- Maintained entirely by `daily-mover-scan` (Job 3). Promotion into the core 6, or removal, always goes through the user.

`AUTOTRADER_TRADE_MAP_TEMPLATE.pine`

- The reusable TradingView renderer.
- It should display only the current coin setup.
- Update its inputs/script from `SETUP_LEDGER.json`.
- It is not the memory layer.

`HANDOVER_TRADING_WORKFLOW.md`

- This file.
- Read it first when moving device/thread.

`scripts/apiAnalyze.py`

- The primary live analysis engine (2026-08-03). Imports `strategyBacktest.py`'s zone/structure/signal functions directly (not reimplemented), so a live read can never drift from what the 3-month backtest actually validated.
- Computes 4H/1D structure, 1H->15m (Intraday) or 1H->15m->5m (Scalp) zones with an `has_fvg` quality flag, the 5m EMA/VWAP/slope signal, and entry/SL/TP/R:R.
- TradingView is now the fallback for structural reads, used only if this can't run for a coin.

`scripts/strategyBacktest.py` / `scripts/scalpBacktestV3.py`

- The backtest engines behind every current rule in `ANALYZE_PROMPT.md`'s Scalp Entry Rule and Timeframe Rules sections (zone construction, FVG detection, the short-side gates, the tuned time-stop, the rejected session filter). Re-run before changing any scalp/zone rule again - multiple rules this project tried and shipped without testing turned out to be actively harmful once actually backtested.

## Current Ledger Entries

Do not trust this file for coin lists or setup states; it goes stale. The current coin list, per-setup state, and `analyzed_at` timestamps live only in `SETUP_LEDGER.json` — read it directly.

## Morning Scan (Scheduled Task)

A scheduled task `daily-mover-scan` runs weekdays at 10:05 AM local. Source of truth is `scheduled-tasks/daily-mover-scan/SKILL.md` in this repo (registered locally at `~/.claude/scheduled-tasks/daily-mover-scan/SKILL.md` - see "Scheduled Tasks Are Now Repo-Tracked" below for how the two stay in sync). It produces a pre-market triage report in chat - report only except for the two explicit write paths noted below.

As of 2026-07-24 this task does three jobs in one run (it previously had a separate `weekly-deep-review` task for jobs 1/3, which was deleted once the overlap became clear - both tasks were independently running mover discovery, which was pure duplicated work; only the re-verification piece was actually distinct, so it moved here instead):

1. **Light-touch check on the core 6** (HYPE, XRP, DOGE, JTO, AVAX, ZEC): one timeframe only per coin (not a full 1D->4H->1H re-derivation), checking current price against already-mapped levels. Classifies each Still Valid / Needs Update (in which case the ledger IS updated and `buildTradeMap.mjs` IS run, same as a normal Analyze) / Stale-Dead. Never touches HYPE/XRP/DOGE's scalp-pair membership - that's `monthly-scalp-review`'s call on different criteria.
2. **Outside-mover discovery** (unchanged from the original design): `scripts/scanMovers.mjs` pulls Bybit's public perpetuals feed (no auth), excludes BTC/ETH and thin-volume symbols (<$3M 24h turnover), flags anything already tracked, writes `MOVER_SCAN.md`. Survivors get chart-verified before being reported as Trade-Worthy/Conditional/Watch.
3. **`WATCHLIST_TIER2.md` maintenance**: a lighter-weight list, below the ledger, for promising coins that don't yet deserve full ledger depth or poller coverage. Adds/drops rows based on Job 2 findings, and if Job 1 flagged a core-6 coin Stale/Dead while Job 2 (or an existing tier-2 entry) shows real chart-verified structure, this is where a swap gets suggested - never applied automatically.

Finding a good candidate here does not add it to the ledger automatically, and a suggested swap is never auto-applied - the user decides both. To change the schedule or prompt, use the scheduled-tasks tools (`list_scheduled_tasks` / `update_scheduled_task`), not a manual edit of the SKILL.md file.

## Monthly Scalp Review (Scheduled Task)

`monthly-scalp-review` runs the 1st of each month at 09:00 local. Source of truth is `scheduled-tasks/monthly-scalp-review/SKILL.md` in this repo. Confirms ZEC (primary), XRP (primary), and SOL (fallback) are still the best scalp picks.

- Pulls fresh Bybit ticker data (spread, 24h range, turnover, per-unit price) for the current picks plus a comparison set of other liquid coins.
- Deliberately NOT sourced from mover-scan hits - momentum-driven candidates tend to be thin/volatile, which is close to the opposite of good scalp microstructure (tight spread, deep liquidity). BTC/ETH are included for reference only and are not re-litigated as candidates each month - they were already ruled out for insufficient volatility relative to smaller-account position sizing, a settled decision.
- Reports only; never modifies the ledger or the scalp designation without the user acting on it.

## Level-Crossing Alerts (Scheduled Task, Free TradingView Alert Workaround)

TradingView's free plan caps active alerts too low to cover a full watchlist. `level-alert-check` (source of truth: `scheduled-tasks/level-alert-check/SKILL.md` in this repo) runs every 30 minutes, 08:00-22:59 local, and is a free substitute built entirely from data already in this repo:

- `scripts/checkAlerts.mjs` reads current prices from Bybit's free public ticker feed (same endpoint `scanMovers.mjs` uses) and compares against the previous run's prices (stored in `.alert_state.json`, gitignored - not part of the handover file set, it's a local cache that rebuilds itself).
- Which levels it watches depends on `position_status`: for a coin with **no confirmed position**, it watches `reclaim`, `watch_zone.low/high`, `sl`, `tp[]`, and `entry.low/high` - all the levels relevant to finding an entry. For a coin with a **confirmed open position** (`position_status` is `ENTERED LONG`, `ENTERED SHORT`, `UR PROFIT`, or `UR LOSS`), it only watches `sl` and `tp[]` - entry/reclaim/zone crossings are no longer useful once you're already in the trade (2026-07-27: this was a real gap - "price crossed the entry zone" alerts kept firing on a coin the user had already entered, which is just noise once the entry already happened).
- It reports a level only when price actually CROSSED it since the last check (previous price and current price on opposite sides) - not merely "close to" a level. This avoids repeat-noise from price chopping right at a line.
- The scheduled task stays silent when nothing crossed. It only messages when a real crossing fires, then suggests running `Analyze [coin]` for a fresh read - except for an open position's TP/SL crossing, which should be treated as "manage the position" (check if it filled, journal the outcome, update the scorecard) rather than a fresh full analysis.
- Resolution is 30 minutes, not instant - fine for Intraday setups, coarse for fast scalp triggers. For time-sensitive scalp levels, use Bybit's own native price alerts (free, unlimited, no TradingView subscription needed) as the faster-reacting complement to this poller.
- If `.alert_state.json` is deleted or this runs on a new device, the next run is a fresh baseline (no crossings reported that run) - expected, not a bug.
- Also watches `SETUP_LEDGER.json`'s `context_watch` block (currently just BTC) - key S/R levels for coins that are never trade candidates in this ledger, added 2026-07-27 so a market-wide move gets flagged once, early, instead of reactively through five separate alt-coin crossings after the fact. Reported crossings are labeled `(context)` and explicitly say to check the tradeable coins - `context_watch` entries never get a Pine trade slot (`buildTradeMap.mjs` only reads `setups`) and are never part of the `Analyze [coin]` trade workflow. This does not change the "BTC/ETH never trade candidates" rule below - it's the same confidence-filter role, just proactive instead of only checked when analyzing something else.

## Operating Cadence

Three scheduled tasks now run the routine layer of this workflow (a fourth, `weekly-deep-review`, was tried and deleted 2026-07-24 once it became clear it was independently re-running mover discovery that `daily-mover-scan` already does daily - the one genuinely distinct piece, core-6 re-verification, was folded into daily-mover-scan's Job 1 instead of kept as a separate task). Daily activity for the user is meant to be alert-response only: react to pings, run `Analyze [coin]` on whatever actually fired, manage anything open.

| Task | Schedule | Watches | Job |
|---|---|---|---|
| `level-alert-check` | Every 30 min, 08:00-22:59 daily | Live Bybit price vs. levels already in `SETUP_LEDGER.json` | Silent unless a level actually crosses, then flags it and suggests `Analyze [coin]` |
| `daily-mover-scan` | Weekdays 10:05 | Core 6 (light touch) + Bybit-wide movers + `WATCHLIST_TIER2.md` | Three jobs: (1) light re-verify the core 6, updating the ledger only if something actually changed, (2) find new outside candidates, (3) maintain the tier-2 watchlist and suggest core-6 swaps when a core coin is stale AND a real replacement exists |
| `monthly-scalp-review` | 1st of month, 09:00 | ZEC/XRP/SOL vs. fresh Bybit spread/turnover/range data | Confirms the scalp picks still lead on liquidity/execution criteria - deliberately NOT sourced from mover-scan, since momentum and good scalp microstructure tend to pull in opposite directions |

Adding or removing a coin from the ledger is never automatic from any of these tasks - they recommend; the user (or a live `Analyze` session) makes the actual ledger write. If a coin is added, the one-in-one-out discipline from the original prune (18 coins down to a 5-6 target) should be applied again rather than letting the list creep back up.

## Ledger Size

Keep active `setups` lean, target roughly 5-6 coins for real day-to-day attention, with a hard ceiling of 10-15 before hygiene is overdue regardless. This is a scannable watchlist, not an archive. The moment a setup goes dead (SL tagged, TP tagged, missed, invalidated), journal it with a mistake tag and delete it from `setups` in the same pass — do not let dead entries accumulate. A bloated `setups` object makes every priority check slower and defeats the point of the ledger being glanceable. `Pine` script size scales with active-setup count (~2.3KB per coin in the ternary chains); this is not a near-term technical limit, but ledger hygiene matters well before script size would.

Structural picks that don't drift (unlike the actual coin list/states - see "Current Ledger Entries" above, read `SETUP_LEDGER.json` directly rather than trusting a snapshot here):

- **ZEC, XRP** — designated scalp pair (changed 2026-10-04 from HYPE/XRP after a live-data review: HYPE's spread widened to 0.0111% and turnover fell to $69.4M, while ZEC showed a 0.0007% spread, $230.6M turnover, 4.76% range). Picked from live Bybit ticker data (spread, 24h range, turnover), not guesswork - see the scalp comparison in journal/chat history if the reasoning needs revisiting. BTC/ETH were considered but ruled out for scalping specifically due to low % volatility relative to the account size being sized against, not because they're untradeable in general. Note: a core-6 *slot* being empty (e.g. HYPE's, open since a 2026-07-27 stop-out) does not remove a coin's scalp-pair designation - those are separate concepts, checked via `monthly-scalp-review`, not the ledger's `setups` list.
- **SOL** — scalp fallback (changed 2026-10-04 from DOGE: $403.6M turnover and 0.0082% spread beat DOGE's $61.7M / 0.0105%), used only if ZEC/XRP setups go cold. HYPE and DOGE stay on watch as backups (DOGE for its low per-unit price / fine position-size granularity). SOL is not in the ledger `setups`; it needs a full Analyze pass before any entry.
- **BTC, ETH** — never trade candidates in this ledger. Used only as the `btc_eth_filter` confidence check on every other coin's analysis. BTC also has a `context_watch` entry (see Level-Crossing Alerts above) - key S/R levels only, no trade fields, so the poller can flag a market-wide move early. This does not change BTC's never-trade status.
- The remaining core-6 Intraday slots (currently JTO, AVAX, ZEC, LIT per the ledger as of early August - check `SETUP_LEDGER.json` for the live list, this drifts) rotate based on which coin is closest to a live trigger, per `daily-mover-scan`'s swap-suggestion logic.

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

Do this (order CORRECTED 2026-08-03 to match the Source Of Truth flip - API first, TradingView for news + display only):

1. Read `SETUP_LEDGER.json` for the coin's prior state.
2. Run `python3 scripts/apiAnalyze.py SYMBOL --trade-type both` - this is the primary structural read: it replays the backtest engines and prints the engine verdict (`VALID` / `ENGINE IN TRADE` / `ENGINE ORDER STILL RESTING` / `NO SIGNAL` with the blocking gates), 4H/1D structure, and the engine's entry/SL/TP/R:R. Fall back to a TradingView chart read only if this can't run for the coin.
3. Check TradingView's news panel for a catalyst read - the API has no news feed.
4. Decide if the old ledger setup is still valid, missed, invalidated, active, or needs refresh.
5. Update `SETUP_LEDGER.json` before drawing.
6. Render the current coin only using `AUTOTRADER_TRADE_MAP_TEMPLATE.pine`.
7. On the user's "confirm," verify the rendered TradingView chart matches the ledger (Post-Drawing Verification Gate) - this is the one TradingView step that's still mandatory, since it's the user's own display, not an analysis input.
8. Close Pine Editor/panels.
9. Final answer uses the required output format.

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

## Scheduled Tasks Are Now Repo-Tracked

As of 2026-07-28, `scheduled-tasks/daily-mover-scan/SKILL.md`, `scheduled-tasks/level-alert-check/SKILL.md`, and `scheduled-tasks/monthly-scalp-review/SKILL.md` live in this repo and are the source of truth for what each task should say and do - `git pull` on any machine now brings the full task definitions with it, not just the scripts they call.

What still does NOT move automatically: the actual registered, firing scheduled task on a given machine. A scheduled task only runs because the Claude Code harness on that specific machine has it registered (visible via `list_scheduled_tasks`, stored locally outside this repo at `~/.claude/scheduled-tasks/<name>/SKILL.md`). Cloning the repo does not register anything - it only gets you the content to register.

To bootstrap on a new device:

1. `git pull` (or copy the files) so `scheduled-tasks/*/SKILL.md` is present.
2. For each of the three tasks, read its repo copy - the frontmatter carries `schedule_human` and `schedule_cron` alongside the prompt body.
3. Use the scheduled-tasks tools (`create_scheduled_task`) to register each one on the new machine, passing the prompt body as the task content and the `schedule_cron` value as the schedule.
4. Confirm with `list_scheduled_tasks` that all three show up, enabled, with the expected `nextRunAt`.

To change a task's schedule or prompt on an already-set-up machine: edit the repo copy in `scheduled-tasks/`, then use `update_scheduled_task` to push that change into the live registration - don't edit `~/.claude/scheduled-tasks/*/SKILL.md` directly, since that copy is not version-controlled and the next repo pull won't know about a change made only there. Keeping the repo copy as the edit target is what makes this whole thing portable rather than another local-only file.

## New Device Setup

On a new device:

1. Copy the files listed under "Files To Move Together" above into the workspace.
2. Open `HANDOVER_TRADING_WORKFLOW.md`.
3. Open `ANALYZE_PROMPT.md` and `ANALYSIS_PLAN.md`.
4. Confirm `SETUP_LEDGER.json` parses as valid JSON.
5. Open TradingView and sign in.
6. Open the Bybit perpetual chart.
7. Clean duplicate/old AutoTrader maps if visible.
8. Install or update `AUTOTRADER_TRADE_MAP_TEMPLATE.pine`.
9. Test one coin from the ledger, preferably XRP.
10. Verify map levels match the ledger.
11. Register the three scheduled tasks from `scheduled-tasks/*/SKILL.md` per "Scheduled Tasks Are Now Repo-Tracked" above, then confirm with `list_scheduled_tasks`.

## Quick Validation

To validate the JSON ledger locally:

```bash
node -e "JSON.parse(require('fs').readFileSync('SETUP_LEDGER.json','utf8')); console.log('SETUP_LEDGER.json OK')"
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

Do not move to auto-trading (orders placed without a human confirming each one) until:

- At least 30 setups counted toward the gate: correct-thesis analyses plus user-confirmed taken trades (one record counts once). Check `SCORECARD.json`'s `summary.reviewed_setups`/`correct_thesis`/`trades_taken` for the current count directly - this drifts every session, do not trust a number written here (raw fields as of 2026-08-03: 11 reviewed, 3 correct-thesis, 3 trades-taken; still well short of 30 either way).
- No repeated confusion between entry, reclaim, and active trade.
- Setup outcomes are tracked as Win, Loss, Missed, No Trade, or Invalidated.
- Alerts can be expressed as strict pass/fail rules.

Note: `level-alert-check` (see Level-Crossing Alerts above) is NOT the "alerts" this gate refers to. It's a free price-crossing notifier that tells a human when to look at a chart - it never places an order or skips human judgment. The Step 2 gate is specifically about moving to unattended auto-trading, which is a different and much bigger step than the notification poller already built.
