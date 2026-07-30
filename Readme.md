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
