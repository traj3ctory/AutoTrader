# Analyzer app review: pending only (2026-11-25)

Baseline: rules at commit `ec02711` plus the 2026-11-25 decisions in `SCALP_STRATEGY.md`. The engine verdict is the only source of a trade. EMA, VWAP and Scalp Zone are context, not gates. Nothing here is committed.

## Closed 2026-11-25
- Counter-trend scalps allowed as a lower tier (badge, ranked below, no sound). Scalp Zone demoted to context only.
- 4H zone veto enforced as Watch Only; BTC/ETH shown as ALIGNED / MIXED / CONFLICTING (advisory).
- Ledger sync tested on XRPUSDT; fixed `rr_tp2` storing a price instead of R; ledger writes follow the tier rules.

## Open
| # | Gap | Note |
|---|---|---|
| 1 | Not verified live | A real fresh signal through the tier badges and Watch Only cap (only mocked; none was live at test time); risk lock on a real locked scan; the chart box visually. |
| 2 | Conditional tier | The docs mention a reduced-size band below 1.5R; the engine floor is 1.5R, so it never triggers. Untested, not implemented. |
| 3 | No-zone exit | With no opposing zone the card shows TP1 1.5R but the backtest books the full exit at 2R. |
| 4 | Level-crossing alerts | Done by the `level-alert-check` task every 30 minutes, not by the app. |
| 5 | BTWUSDT | An extra symbol in the scan universe fails Bybit lookup on every scan; remove it from the watchlist source. |
