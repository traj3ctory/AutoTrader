---
name: level-alert-check
description: Every 30 min - reports ledger trigger levels crossed since the last check, and any new backtest-engine signal on a ledger coin. Silent otherwise.
schedule_human: Every 30 minutes, between 08:00 AM and 10:59 PM, every day
schedule_cron: "*/30 8-22 * * *"
---

This task runs two scripts from the repo root (wherever this repo was cloned/copied to on the current machine - do not hardcode a path): first `node scripts/checkAlerts.mjs` (Part 1, level crossings), then `python3 scripts/signalScan.py` (Part 2, engine signals, added 2026-11-17). Run both every time, each exactly once. Stay silent only if BOTH have nothing to report.

## Part 1: level crossings

This script polls Bybit's free public ticker/kline API and compares price against the trigger levels (reclaim lines, watch-zone edges, SL, TP, entry zone) already stored in SETUP_LEDGER.json for every coin currently in the ledger's `setups` object, plus the `context_watch` block (currently BTC's key S/R levels - context only, never a trade candidate, reported separately as `(context)`). It reports only levels that were CROSSED since the last check — this is a genuine crossing detector, not a proximity alert. As of 2026-07-30 it has two noise-reduction layers on top of the original instant-ticker check:

1. **Hysteresis band** (±0.25% of the level price): a level only re-arms for the opposite direction once price has actually cleared the buffer past it. Chop oscillating right at a line no longer fires a crossing every 30 minutes.
2. **Close-based confirmation for RECLAIM/ZONE/ENTRY levels**: these are judged by candle closes per `ANALYZE_PROMPT.md` ("judged by candle closes on the entry timeframe, not wicks"), so the poller checks the last CLOSED candle on the coin's own trade-timeframe (1H Intraday / 5m Scalp) for these, not the instantaneous ticker. SL/TP and `context_watch` levels stay on instant ticker - a stop or a market-wide BTC level is worth knowing the instant it's touched.

A crossing report for a RECLAIM/ZONE/ENTRY level now means "closed through, hysteresis-confirmed" - meaningfully stronger evidence than the old instant-price version, and should be treated accordingly (less need to hedge with "might just be a wick" in the message to the user).

Behavior:
- If the script output is "First run..." or "No triggers crossed since last check." — do NOT message the user. Stay silent. This is the expected common case; the whole point of this task is to avoid noise.
- If the script reports one or more crossed triggers, message the user with a short, direct summary: which coin(s), which level(s), and current price vs the level. Do not add speculative analysis or a full Analyze — just report the fact that a mapped level was crossed and suggest running `Analyze [coin]` for a fresh read now that something moved.
- Before suggesting `Analyze [coin]`, apply the Gate 0 significance pre-check from `ANALYSIS_PLAN.md`: if the crossing is marginal relative to the coin's own stated confirmation/invalidation thresholds, say so plainly rather than implying a full Analyze is automatically warranted. This is less often needed now that RECLAIM/ZONE/ENTRY crossings are close-confirmed, but still applies to SL/TP instant-ticker crossings.
- For an open position's TP/SL crossing specifically, treat it as "manage the position" (check if it filled, journal the outcome, update the scorecard) rather than suggesting a fresh full analysis.
- If the script errors (e.g. Bybit API unreachable), do not message the user for a single transient failure — only flag it if it fails multiple runs in a row (you won't have memory of prior runs, so just let a single failure pass silently this run).
- State any timestamp in UTC+1 (the user's timezone), or give both UTC and UTC+1.
- `.alert_state.json` now stores per-level armed side (`levelSides`), not flat per-coin prices. If it's ever deleted, missing, or in the old flat-price format, the next run treats it as a fresh baseline (no crossings that run) and rebuilds it - expected, not a bug, same as before.

## Part 2: engine signals (added 2026-11-17)

`python3 scripts/signalScan.py` replays the two backtested engines (scalp v4 and intraday, the same ones `scripts/apiAnalyze.py` uses) for every coin in `SETUP_LEDGER.json` and prints only signals that are new since the last run (its memory is `.signal_state.json`). A scalp signal is reported while it is at most 12 closed 5m candles (60 minutes) old; an intraday limit while it is at most 4 closed 15m candles old. The 30-minute cadence is deliberate: a backtest (`backtests/2026-11-17-live-fit/`) showed that entering up to 60 minutes late with the engine's original SL and TP performs the same as entering at the signal close, so a faster scan buys nothing.

- If the output is exactly `No new signals.` - nothing to report from Part 2.
- If the output starts with `NEW ENGINE SIGNALS`, message the user with each signal line as printed: coin, engine, side, when the candle closed, entry, SL, TP, R:R, and how far price has moved from the entry in R. Give times in UTC and UTC+1.
- State the signal's age. For a scalp signal: the SL and TP stay exactly as printed whatever the fill price - never widen the stop or move the target for a late entry. If price has already traded through the SL or TP, say the signal is dead.
- Add one line of expectancy context, unchanged each time: out-of-sample (Aug 1-Nov 15 2026) the scalp engine averaged +0.14R per trade at a 36% win rate and the intraday engine +0.28R at 47%, net of 0.14% round-trip cost - most signals lose.
- Do not add a discretionary opinion on whether to take the trade, do not run `Analyze [coin]`, do not open TradingView. The user decides and places any order themselves; never place, modify or cancel an order.
- If the output includes `Scan failed for ...`, stay silent about it unless the failure line covers every coin.

Do not modify SETUP_LEDGER.json or any other tracked file in this task — it is a read-only check. The only files it writes are `.alert_state.json` and `.signal_state.json`, and only through the two scripts.
