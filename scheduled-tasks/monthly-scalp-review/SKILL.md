---
name: monthly-scalp-review
description: Monthly (1st, morning): re-checks HYPE/XRP/DOGE against fresh Bybit spread/turnover/volatility data to confirm they're still the best scalp picks.
schedule_human: At 09:00 AM, on day 1 of the month
schedule_cron: 0 9 1 * *
---

Run the monthly scalp-coin review for the AutoTrader trading workflow, in the repo root (wherever this repo was cloned/copied to on the current machine - do not hardcode a path).

Purpose: re-verify HYPE (primary), XRP (primary), and DOGE (fallback) are still the best scalp picks based on market microstructure - NOT based on which coin moved the most recently. Scalp coin selection criteria are liquidity, spread tightness, and realistic volatility relative to account size, not momentum. This is a slower, separate cadence from `daily-mover-scan` (which handles Intraday coin swaps from mover candidates) precisely because a good scalp coin's profile doesn't change week to week the way price structure does, and mover-driven candidates tend to be thin/volatile - the opposite of a good scalp profile.

Steps:

1. Fetch live data from Bybit's public ticker endpoint (`https://api.bybit.com/v5/market/tickers?category=linear`, no auth needed) for: the current picks (HYPEUSDT, XRPUSDT, DOGEUSDT), the majors (BTCUSDT, ETHUSDT) for reference only (never actual candidates - already ruled out for insufficient volatility relative to smaller account sizes, this is a settled decision not open for re-litigation each month), and a comparison set of other liquid alts (SOLUSDT, AVAXUSDT, ZECUSDT, JTOUSDT, plus whatever else is currently in SETUP_LEDGER.json's `setups`, plus the top 5-10 by 24h turnover from the full ticker list that aren't already covered).

2. For every symbol, compute: 24h range as % of price ((high-low)/last * 100), bid-ask spread as % of price ((ask-bid)/last * 100), 24h turnover in USD, and note the per-unit price (relevant for position-sizing granularity on a smaller account).

3. Rank candidates by a combined "scalp fitness" read: tight spread and high turnover are the primary filters (these directly affect execution cost and slippage), 24h range should be meaningfully non-trivial (a coin can have great liquidity but too little movement to be worth scalping - this is why BTC was ruled out despite the tightest spread of all), and lower per-unit price is a secondary tiebreaker (finer position-size granularity on a smaller account).

4. Compare HYPE/XRP/DOGE's current rank against the full comparison set. If they still lead or are competitive within the set, say so plainly and change nothing. If something in the comparison set now clearly beats one of the three on the combined criteria (not just on 24h range/momentum alone), name it and explain specifically why (cite the actual spread/turnover/range numbers, not a vague impression).

5. Produce a short chat report: a data table (symbol, range%, spread%, turnover, price) for every symbol checked, then one line stating whether HYPE/XRP/DOGE remain the picks or whether a swap is worth considering and why. This task does not modify SETUP_LEDGER.json or execute any swap - it only reports; the user decides whether to act on a suggested change.
