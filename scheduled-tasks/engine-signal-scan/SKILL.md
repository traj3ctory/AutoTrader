---
name: engine-signal-scan
description: Every 5 minutes - replays the backtest engines on live Bybit data for every ledger coin and reports only brand-new tested signals. Silent otherwise.
schedule_human: Every 5 minutes, between 08:00 AM and 10:59 PM, every day
schedule_cron: "*/5 8-22 * * *"
---

Run `python3 scripts/signalScan.py` from the AutoTrader repo root (wherever this repo was cloned/copied to on the current machine - do not hardcode a path). Run it exactly once and do nothing else first - speed matters, because a signal is only the tested trade at the close of its own 5m candle.

What the script does: for every coin in `SETUP_LEDGER.json` it replays the two backtested engines (scalp v4 and intraday, the same ones `scripts/apiAnalyze.py` uses) over 150 days of closed candles and prints only signals that are new since the last run. It keeps its own memory in `.signal_state.json`, so a signal is reported once. A scalp signal is reported only while it is at most 3 closed 5m candles old; an intraday limit only while it is at most 4 closed 15m candles old.

Behavior:
- If the output is exactly `No new signals.` - do NOT message the user. Stay silent. This is the expected result on almost every run.
- If the output starts with `NEW ENGINE SIGNALS`, message the user immediately with each signal line as printed: coin, engine (scalp/intraday), side, when the candle closed, entry, SL, TP, R:R, and how far price has already moved from the entry in R. Give times in UTC and UTC+1.
- Say plainly how old each signal is. The tested scalp trade is the market entry at the close of the signal candle; if the line says the signal is 1-3 candles old, state that a late entry is not the tested trade and quote the `R from entry` drift so the user can judge. Never describe an older signal as fresh.
- Add one line of expectancy context, unchanged each time: out-of-sample (Aug 1-Nov 15 2026) the scalp engine averaged +0.14R per trade at a 36% win rate and the intraday engine +0.28R at 47%, net of 0.14% round-trip cost - most signals lose.
- Do not add a discretionary opinion on whether to take the trade, do not run `Analyze [coin]`, do not open TradingView. This task reports the engine's signal and nothing more. The user decides and places any order themselves; never place, modify or cancel an order.
- If the output includes `Scan failed for ...`, stay silent for a single run (Bybit errors are usually transient and the script already retries). Only mention it if the failure line covers every coin.
- Do not modify `SETUP_LEDGER.json` or any other tracked file. The only file this task writes is `.signal_state.json`, and only through the script.
