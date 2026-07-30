| Command               | What it does                                                                                                               |
| --------------------- | -------------------------------------------------------------------------------------------------------------------------- |
| `watchlist scan`      | Scans the core 6 (`SETUP_LEDGER.json`) and `WATCHLIST_TIER2.md`, plus verified outside movers. Produces ranked candidates only; no ledger or Pine changes. Runs a significance pre-check first (see `ANALYSIS_PLAN.md` Gate 0) - a coin that hasn't cleared its own stated trigger/invalidation isn't re-analyzed just because it was touched. |
| `simple-analyze KMNO` | Fresh live-chart analysis with the result in chat only. Does not update the ledger or Pine - narrower than `analyze [coin]`, which always runs the full contract in `ANALYZE_PROMPT.md`/`ANALYSIS_PLAN.md` (chart first, full 1D->4H->1H, ledger write, Pine regen). Use `simple-analyze` for a quick look you don't want persisted. |
| `analyze KMNO`        | Full workflow: fresh TradingView analysis (chart read first, API data only as a stated fallback), validity check, ledger/scorecard update, and Pine regeneration. Only applies to the core 6 in `SETUP_LEDGER.json` - a tier2 or outside coin gets logged in `WATCHLIST_TIER2.md` instead, not a Pine slot. |
| `analyze watchlist`   | Fully analyzes every viable core-6 coin and rebuilds the combined Pine map.                                             |
| `scorecard update`    | Records whether a thesis was correct or invalidated and whether a confirmed trade won or lost.                             |
| `confirm`             | After you paste the Pine script, verifies the visible TradingView card, zones, levels, state and timestamp.                |

Background (all scheduled tasks, see matching sections in `HANDOVER_TRADING_WORKFLOW.md`):
- `level-alert-check` (every 30 min) — polls Bybit prices against every level in `SETUP_LEDGER.json`, including the `context_watch` block (currently BTC's key S/R levels, flagged separately as `(context)` - never a trade candidate, no Pine slot). Silent unless a level actually crosses.
- `daily-mover-scan` (weekdays at 10:05) — three jobs in one run: light re-verify of the core 6, outside-mover discovery (including an intraday-range-mover pass alongside the 24h% scan, so a coin with a real intraday sweep/bounce isn't missed just because its net 24h% is small), and `WATCHLIST_TIER2.md` maintenance (incl. suggesting core-6 swaps when warranted).
- `monthly-scalp-review` (1st, 09:00) — re-checks HYPE/XRP/DOGE against fresh liquidity/spread data.

```
- watchlist scan
- simple-analyze XRP
- analyze APE
- analyze KMNO again
- analyze watchlist
- scorecard update: JTO correct thesis, trade taken, closed 0.6051, +2R
- confirm
```



----- 
 —— New Chat Get up to speed on the AutoTrader project before doing anything else.

Read these files in this exact order:
1. HANDOVER_TRADING_WORKFLOW.md
2. ANALYZE_PROMPT.md
3. ANALYSIS_PLAN.md
4. SETUP_LEDGER.json
5. WATCHLIST_TIER2.md

Treat SETUP_LEDGER.json as lifecycle/history context only, never as a
substitute for a fresh TradingView chart read.

Do not analyze coins, modify the ledger, regenerate Pine, or interact
with TradingView yet.

When finished, summarize:
- the analysis workflow you understand;
- the current ledger and watchlist state;
- any missing, conflicting, or ambiguous instructions.   —— New PC/ENV setup

git clone https://traj3ctory@github.com/traj3ctory/AutoTrader.git && cd AutoTrader

Get up to speed on the AutoTrader project before doing anything else.

Read these files in this exact order:
1. HANDOVER_TRADING_WORKFLOW.md
2. ANALYZE_PROMPT.md
3. ANALYSIS_PLAN.md
4. SETUP_LEDGER.json
5. WATCHLIST_TIER2.md

Treat SETUP_LEDGER.json as lifecycle/history context only, never as a
substitute for a fresh TradingView chart read.

Then inspect every scheduled-tasks/*/SKILL.md file and inspect whatever
scheduled-task/automation mechanism is available in this environment
(list existing ones first). For each of daily-mover-scan, level-alert-check,
and monthly-scalp-review: if it's missing, register it using that file's
frontmatter for the schedule and its body as the task's instructions,
verbatim. If it's already registered, compare the live version against
the repo file and update it only if they differ, using the repo file as
the source of truth. Do not create a duplicate if one already exists.
Preserve each task's specified schedule, timezone, workspace, workflow
order, and output format exactly as written - do not paraphrase or shorten.

Do not analyze coins, modify the ledger, regenerate Pine, or interact
with TradingView yet.

When finished, summarize:
- the analysis workflow you understand;
- the current ledger and watchlist state;
- every scheduled task found in scheduled-tasks/*/SKILL.md;
- whether each automation was created, updated, or already correct;
- its schedule, timezone, and task/automation ID;
- any missing, conflicting, or ambiguous instructions.