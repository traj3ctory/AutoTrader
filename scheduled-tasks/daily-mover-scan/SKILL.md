---
name: daily-mover-scan
description: Daily (weekdays ~10:05): light-touch check on the core 6, outside-mover discovery, and tier-2 watchlist maintenance - all in one run, replaces the old separate weekly review.
schedule_human: At 10:05 AM, Monday through Friday
schedule_cron: 5 10 * * 1-5
---

Run the daily crypto scan for the AutoTrader trading workflow, in the repo root (wherever this repo was cloned/copied to on the current machine - do not hardcode a path).

This is a Monday-Friday pre-market run with THREE tradeable-coin jobs plus a BTC context check (Job 0, added 2026-07-27) in one pass (as of 2026-07-24, this replaces both the old full-watchlist daily scan AND the separate `weekly-deep-review` task, which has been deleted - everything below now happens daily, but Job 1 is intentionally light so it doesn't reintroduce the old daily-treadmill problem this consolidation is meant to avoid). It produces analysis in chat only - it never writes to SETUP_LEDGER.json except via the explicit "Needs Update" path in Job 1, never draws on TradingView, never rewrites AUTOTRADER_TRADE_MAP_TEMPLATE.pine except after an explicit ledger update in Job 1 (run `node scripts/buildTradeMap.mjs` afterward if you did update a coin).

Apply the current rules in ANALYZE_PROMPT.md and ANALYSIS_PLAN.md throughout, including: the R:R floors (Scalp TP1 >= 1.5R, TP2 in 2.5-3.5R band; Intraday TP1 >= 2R, TP2 in 3-4R band, both measured from the entry-zone edge not midpoint), the Conditional (Reduced-Size) Tier (1.5-2R Intraday / 1.2-1.5R Scalp qualifies for half-size if every other gate passes), the mandatory 4H veto before any scalp map, the Dual-Activation Rule, the Parabolic Spike Rule (including the short-side zone-mismap incident, 2026-07-28), the TP Zone Validity Rule, the SL Buffer Calibration Rule, the Candle-Shape Judgment Rule (orderly trend vs spike-and-reverse noise - judge shape, not just %/range, for every mover surfaced), and Gate 0's significance pre-check (don't spend a full Analyze on a coin that hasn't actually cleared its own stated trigger/invalidation level).

Source order (CHANGED 2026-08-03, per ANALYZE_PROMPT.md's Source Of Truth flip): `scripts/apiAnalyze.py SYMBOL` is primary for every coin's structural read (4H/1D structure, 1H->15m zones, 5m signal, computed entry/SL/TP/R:R) - it reuses the exact validated backtest logic, live. Ledger is second. TradingView is used for exactly two things: a quick catalyst/news check, and (only if a coin's ledger entry got a real update this run) the final Pine paste-and-verify display step. Chart-based structural reading via TradingView is now the FALLBACK only, used if `apiAnalyze.py` can't run for a coin (missing from Bybit, data gap) - not the default path.

Browser tool (fallback/news-check use only): the `claude-in-chrome` MCP tools (the user's real Chrome, already logged into TradingView), not a sandboxed browser preview pane. Start with `tabs_context_mcp{createIfEmpty:true}`, navigate to TradingView once, reuse that same tab for the whole session.

News-check visits are read-only - do not clear, hide, remove, or otherwise touch any existing AutoTrader Trade Map drawings/Pine indicators while just checking the news panel for a coin. The Chart Cleanup Gate in ANALYZE_PROMPT.md only applies when actually drawing/redrawing a map (i.e. Job 1's "Needs Update" path after a real ledger change) - a passive news glance is never a reason to wipe or modify what's on the chart.

Chart-read discipline (fallback path only): give TradingView a short pause to paint after opening/switching before treating it as accessible or blank. The retry cap is ONE retry, full stop - not one retry per remediation technique (reload, new tab, timeframe switch, symbol-hop-and-back all count as the same attempt). Two total attempts per coin is the entire budget.

---

## Job 0: BTC context check (added 2026-07-27)

Before Job 1, check `SETUP_LEDGER.json`'s `context_watch.BTCUSDT.P` entry against BTC's current price (`node scripts/checkAlerts.mjs` covers this automatically as part of its normal run, or pull BTC's ticker directly). This is context only - BTC is never a trade candidate, no entry/SL/TP - the point is catching a market-wide move before it's already visible piecemeal across the core 6's own crossings.

- If price is inside `key_support`-`key_resistance` (the normal range), note it as one line, nothing more.
- If price has crossed `key_support` or `key_resistance` since the last check, or is testing `deeper_support`, say so explicitly in the Market Filter output line - this raises the bar for how skeptically Job 1's "Still Valid" calls should be read that day (a market-wide move in progress makes individual coin structure less reliable until it settles).
- Do not add BTC's own levels to `WATCHLIST_TIER2.md` or treat this as a Job 2 candidate - it stays out of the tradeable pipeline entirely, same as always.

## Job 1: Light-touch check on the core 6 (HYPE, XRP, DOGE, JTO, AVAX, ZEC)

This is intentionally NOT a full 1D->4H->1H re-derivation for every coin - that was the old behavior this consolidation removed. For each of the 6:

1. Read the coin's current SETUP_LEDGER.json entry (levels, setup_state, analyzed_at).
2. Run `python3 scripts/apiAnalyze.py SYMBOL` and check current price/structure against the mapped levels (watch_zone, reclaim, entry, sl, tp) - this replaces the old single-timeframe TradingView glance with the live API read.
3. Classify: **Still Valid** (structure/levels still make sense, no ledger change needed - just note it, one line), **Needs Update** (something material changed - price broke a level, a trigger fired, structure clearly shifted - in this case do a real ledger update for that coin same as a normal `Analyze [coin]` would, including `node scripts/buildTradeMap.mjs` afterward), or **Stale/Dead** (no real structure left, hasn't triggered in a long time, thesis looks tired) - flag this for a possible Job 3 swap, do not delete it yourself.
4. Do NOT treat HYPE/XRP/DOGE's *scalp-pair membership* as up for debate here - that's `monthly-scalp-review`'s job on different criteria (liquidity/spread, not momentum). You may still flag Still Valid/Needs Update/Stale for their Intraday-relevant structure if they have any, but never suggest removing them from the ledger via this job.
5. A coin that was flagged Stale/Dead and SL/invalidated in a prior pass (e.g. HYPE, 2026-07-27) should be re-checked here for a fresh, real setup before being re-added - not re-added just because time has passed. If nothing new has formed, say so plainly and leave the core-6 slot open.

## Job 2: Outside-mover discovery (unchanged from before)

1. Run `node scripts/scanMovers.mjs` (BTC/ETH excluded, thin-volume filtered, flags anything already in SETUP_LEDGER.json or WATCHLIST_TIER2.md). This includes the intraday-range-mover section (range%/net% round-trip detector, added 2026-07-28) alongside the standard 24h% gainers/losers - a real structural setup (sweep-and-bounce, spike-and-fade) can have a small net 24h% and would otherwise never surface.
2. Silently pre-filter: drop parabolic/blown-off single-session moves (>=20-25% with no visible base) unless a sweep-fail-short or origin-base-retest is plausible, drop the tail of an extended multi-day collapse, drop fresh listings with only days of history. Also drop anything whose candle shape is a long wick with an immediate reversal (noise/liquidity sweep, not a real move) per the Candle-Shape Judgment Rule - contrast against an orderly, sustained trend, which does get a real directional read. Rank survivors by turnover and moderate-but-real move size, cap the shortlist at 5-8.
3. Run `python3 scripts/apiAnalyze.py SYMBOL` on the shortlist (correct trade type per its structure). Rate each: Trade-Worthy (clears Gate 7, has or is near a trigger), Conditional-Reduced-Size, Watch (real structure, no entry yet - state the exact trigger), or Skip (omit entirely). State a directional expectation for every coin mentioned, not just the raw stat line. Fall back to a TradingView chart read only if `apiAnalyze.py` can't run for that symbol.

## Job 3: Tier-2 watchlist maintenance + swap suggestions

`WATCHLIST_TIER2.md` holds coins worth watching that are NOT in the core 6 and are NOT polled by `level-alert-check` - a lighter-weight tier than the ledger, for promising coins that don't yet deserve full ledger depth.

1. Read the current `WATCHLIST_TIER2.md` table.
2. Any Job 2 coin rated Watch or better that isn't already on the tier-2 list and isn't clearly a one-day flash: add it to the table (coin, today's date, one-line why, one-line note). Keep this list itself lean - if it's grown past ~10 rows, the oldest/coldest entries should be dropped in the same pass, noted in the report.
3. For existing tier-2 rows, a quick price-only glance (no full chart read needed) is enough to update the "last note" column - has it kept moving, gone dead, or matured into something worth a real look. If a chart-verified read was already done for a row in this or a prior session, keep that verified note rather than reverting to a price-only placeholder.
4. **Swap suggestions**: if Job 1 flagged a core-6 coin as Stale/Dead, AND either Job 2 or an existing tier-2 entry has real chart-verified structure (not just a big % move - actual Gate 7 checks) that would justify taking that slot, prepare the suggestion: what would come out, what would go in, why. Never touch HYPE/XRP/DOGE this way (see Job 1). Do not apply the swap yourself - report it, the user decides. If suggesting a promotion from tier-2 into the core 6, note that this is also where the "one-in-one-out" ledger-size discipline applies.
5. Write the updated `WATCHLIST_TIER2.md` table back to the file.

## Output format

Produce a single chat message (not a file dump of Job 3's internals), kept SHORT:

- One line: Market Filter (BTC/ETH state, including whether BTC has crossed a `context_watch` level since the last check - see Job 0).
- **CORE 6 CHECK**: one line per coin (Still Valid / Needs Update + what changed / Stale-Dead). If all 6 slots active and Still Valid, one line total: "All 6 still valid, no changes." If a slot is open (e.g. post-SL, not yet re-filled), say so explicitly.
- **OUTSIDE MOVERS WORTH A LOOK** (table): Trade-Worthy/Conditional/Watch coins from Job 2, including any intraday-range-mover finds. Empty is a valid, honest result - say so in one line.
- **TIER 2 WATCHLIST** (table): full current table every run (Coin / Added / Why / Last note - same columns as `WATCHLIST_TIER2.md`), not just today's deltas - the user has to open the file otherwise. Lead with one line stating what changed today (added/dropped/none), then the full table underneath.
- **SUGGESTED SWAP** (only if Job 3 step 4 found one): clearly separated, states the trade-off plainly.
- Do NOT include Skips, Ruled Out, or Unverified sections by default - noise for a daily read. If `apiAnalyze.py` fails for a coin (missing symbol, data gap) and the TradingView fallback also fails, say so explicitly at the top per the stop-and-tell rule rather than silently omitting that coin.

Everything here is educational chart analysis, not financial advice; no trades are executed and no alerts are placed.
