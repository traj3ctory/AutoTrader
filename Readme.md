| Command               | What it does                                                                                                               |
| --------------------- | -------------------------------------------------------------------------------------------------------------------------- |
| `watchlist scan`      | Scans your TradingView watchlist plus verified outside movers. Produces ranked candidates only; no ledger or Pine changes. |
| `simple-analyze KMNO` | Fresh live-chart analysis with the result in chat only. Does not update the ledger or Pine.                                |
| `analyze KMNO`        | Full workflow: fresh TradingView analysis, validity check, ledger/scorecard update, and Pine regeneration.                 |
| `analyze watchlist`   | Fully analyzes every viable watchlist coin and rebuilds the combined Pine map.                                             |
| `scorecard update`    | Records whether a thesis was correct or invalidated and whether a confirmed trade won or lost.                             |
| `confirm`             | After you paste the Pine script, verifies the visible TradingView card, zones, levels, state and timestamp.                |

Background (all scheduled tasks, see matching sections in `HANDOVER_TRADING_WORKFLOW.md`):
- `level-alert-check` (every 30 min) — polls Bybit prices against every level in `SETUP_LEDGER.json`, silent unless one crosses.
- `daily-mover-scan` (weekdays ~10:12) — three jobs in one run: light re-verify of the core 6, outside-mover discovery, and `WATCHLIST_TIER2.md` maintenance (incl. suggesting core-6 swaps when warranted).
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
