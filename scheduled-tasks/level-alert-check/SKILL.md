---
name: level-alert-check
description: Free workaround for TradingView's paid alert limit — polls Bybit's public ticker feed every 30 min and reports only ledger trigger levels that were crossed since the last check.
schedule_human: Every 30 minutes, between 08:00 AM and 10:59 PM, every day
schedule_cron: "*/30 8-22 * * *"
---

Run `node scripts/checkAlerts.mjs` from the repo root (wherever this repo was cloned/copied to on the current machine - do not hardcode a path).

This script polls Bybit's free public ticker API and compares current prices against the trigger levels (reclaim lines, watch-zone edges, SL, TP, entry zone) already stored in SETUP_LEDGER.json for every coin currently in the ledger's `setups` object, plus the `context_watch` block (currently BTC's key S/R levels - context only, never a trade candidate, reported separately as `(context)`). It reports only levels that were CROSSED since the last check (previous price and current price on opposite sides of the level) — this is a genuine crossing detector, not a proximity alert.

Behavior:
- If the script output is "First run..." or "No triggers crossed since last check." — do NOT message the user. Stay silent. This is the expected common case; the whole point of this task is to avoid noise.
- If the script reports one or more crossed triggers, message the user with a short, direct summary: which coin(s), which level(s), and current price vs the level. Do not add speculative analysis or a full Analyze — just report the fact that a mapped level was crossed and suggest running `Analyze [coin]` for a fresh read now that something moved.
- Before suggesting `Analyze [coin]`, apply the Gate 0 significance pre-check from `ANALYSIS_PLAN.md`: if the crossing is marginal relative to the coin's own stated confirmation/invalidation thresholds (e.g. a few ticks past a flip level that already requires a full 1H close-and-hold to count), say so plainly rather than implying a full Analyze is automatically warranted.
- For an open position's TP/SL crossing specifically, treat it as "manage the position" (check if it filled, journal the outcome, update the scorecard) rather than suggesting a fresh full analysis.
- If the script errors (e.g. Bybit API unreachable), do not message the user for a single transient failure — only flag it if it fails multiple runs in a row (you won't have memory of prior runs, so just let a single failure pass silently this run).
- State any timestamp in UTC+1 (the user's timezone), or give both UTC and UTC+1.

Do not modify SETUP_LEDGER.json or any other file in this task — this is a read-only price-crossing check, not an analysis or ledger-write task.
