# Analyze Prompt: TradingView Crypto Perpetual Futures

Use this prompt to analyze crypto perpetual futures on Bybit using TradingView.

This is Step 1 of the roadmap: make the analysis trade like the user, then better. Treat all output as educational chart analysis, not financial advice. Do not automate alerts or auto-trade from this prompt.

## Non-Negotiable Execution Rule

The final answer is not complete unless one of these is true:

- The TradingView chart has been cleaned, marked, verified, and left on the chart view.
- The Pine script was regenerated and handed off for manual paste per the Chart Drawing Method rule below, and the final answer clearly starts with `SCRIPT READY - MANUAL PASTE REQUIRED`.
- Chart marking failed, and the final answer clearly starts with `CHART NOT MARKED` and explains why.

Do not give a normal final trade summary while the chart is stale, unmarked, or showing conflicting old levels.

The normal output format is allowed only after TradingView chart marking and verification succeed, or after a manual-paste handoff per the rule below. If the chart is not marked or cannot be verified and no handoff was offered, do not present the setup as completed. You may still provide the setup, but it must be clearly labeled `SETUP ONLY - NOT DRAWN ON TRADINGVIEW`, include the drawing/verification issue, and offer to redraw from the ledger.

**Light Pass Mode is disabled.** Every `Analyze [coin]` request runs the full contract below, every time, regardless of how recently the coin was last analyzed or whether anything appears to have crossed - full timeframe stack, ledger update, `buildTradeMap.mjs` regeneration, script copied to the user's clipboard, and the plain-English summary + image. The user explicitly asked for this after a Light Pass skipped steps they expected to see every time (2026-07-27) - do not reintroduce a shortcut path without the user asking for it back.

## Analyze Always Means A Fresh Read

`Analyze [coin]` is never satisfied by reciting the ledger's last saved entry, no matter how recent it looks. Every request requires a fresh run of `scripts/apiAnalyze.py` (or the coin's live equivalent) this turn and re-deciding the setup from what is actually happening right now.

- The ledger is a write-target and history/context source, not an answer. Read it first for prior setup state, journal history, and mistake tags - then run the live API analysis before writing or reporting anything as the analysis.
- Record the reasoning, not just the numbers: for every entry/retest zone, state what structural evidence produced it (which swing high/low, which liquidity pool, which relative-strength signal, which candle behavior) directly in the ledger's `bias`/`notes`/`nearest_liquidity` fields, and repeat the key reasoning in the chat output. The "why" must survive without needing to be reconstructed later.
- Still check TradingView's news feed for a catalyst read before finalizing - the API has no news source, and the Catalyst Gate below still applies.
- Chart-read fallback (rare, only if `apiAnalyze.py` cannot run for a coin): give TradingView a short pause to paint before reading it - wait a few seconds after opening/switching before the first screenshot. The one-retry-cap still applies here: ONE retry, full stop - reload, new tab, timeframe switch, symbol-hop-and-back all count as the same attempt budget. If still blank after that, stop and state a `CHART NOT MARKED` limitation rather than escalating through more techniques.

### Light Pass Mode - DISABLED

Light Pass Mode previously allowed skipping the full timeframe re-derivation and the Pine regenerate/paste/summary/image steps when nothing had crossed since the last read. The user found this confusing - they expect the same full output (full timeframe stack, ledger update, regenerated Pine script copied to clipboard, plain-English summary, image) every time they say `Analyze [coin]`, whether or not anything changed since the last pass. This mode is off. If a future session wants to re-enable a shortcut path, it must be requested explicitly by the user first, not assumed from context.

## Chart Drawing Method

Manual paste is the default, every time - do not drive the Pine Editor via browser automation (no automated select-all/paste/save/add-to-chart click-through). That path was tried and dropped: it burned excessive time and tokens on click-by-click Pine Editor automation for something the user can do in seconds themselves. Claude in Chrome (the user's real, logged-in browser - never the sandboxed Browser pane) is still the right tool for reading the live chart and for the verification screenshot, just not for performing the paste itself.

Session setup:

- Use one persistent browser tab for the whole session. Do not close and reopen a fresh tab per coin; fresh navigations are the main trigger for the TradingView blank-canvas render bug. Switch symbols within the same tab (watchlist click or symbol search) instead of renavigating.
- Always use Claude in Chrome for any TradingView interaction (chart reads, verification). The sandboxed Browser pane has no TradingView login and will show a blank canvas / sign-up wall that looks like the render bug but isn't - don't burn the retry cap on it.

Manual handoff (the default path, not a fallback):

1. Update the ledger and run `node scripts/buildTradeMap.mjs` to regenerate `AUTOTRADER_TRADE_MAP_TEMPLATE.pine`.
2. Start the final answer with `SCRIPT READY - MANUAL PASTE REQUIRED`.
3. Give a compact analysis: Coin / Trade Type / Direction / Entry / SL / TP / R:R / Trigger-Reclaim / Setup State / Final Action / one-line bias - not the full field list.
4. Render a visual trade-map (entry zone, SL, TP1-3, reclaim line, state) from the same ledger data as a fallback the user can look at immediately, independent of whether the live chart ever renders.
5. Point to the file (`AUTOTRADER_TRADE_MAP_TEMPLATE.pine`) and tell the user to paste it into the Pine Editor themselves (select-all, paste, save, add to chart if needed).
6. When the user says "confirm," run the observed Post-Drawing Verification Gate (fresh screenshot via Claude in Chrome, read the rendered card, confirm every field against the ledger) before calling the chart verified.

The journal and scorecard update every time regardless of paste outcome - the record of what was analyzed does not depend on whether the chart shows it yet.

## Source Of Truth

CHANGED 2026-08-03: Bybit API is now primary for analysis; TradingView is display/news only. This reverses the original chart-first hierarchy after a session of repeated TradingView render failures (blank canvas, stuck symbol switches) versus a fully validated, backtested API pipeline (`scripts/strategyBacktest.py`, `scripts/scalpBacktestV3.py`, `scripts/apiAnalyze.py`) that never failed once across a 3-month/17-coin test.

Use this source hierarchy:

1. `scripts/apiAnalyze.py SYMBOL` (or the coin's live equivalent) - reuses the exact zone-detection, structure, and signal functions from the backtest, live. This is the primary analysis engine: 4H/1D structure, 1H->15m refined zones, 5m EMA/VWAP/slope signal, computed entry/SL/TP/R:R.
2. `SETUP_LEDGER.json` for remembered setup state, prior levels, position status, and journal history.
3. TradingView, for exactly two things: (a) a catalyst/news check (the API has no news feed), and (b) the final Pine paste-and-verify display step - this is for the user's own chart, not an analysis input. A catalyst/news-check visit is read-only: do not clear, hide, remove, or otherwise touch any existing AutoTrader Trade Map drawing while just checking the news panel. The Chart Cleanup Gate below only applies when actually drawing/redrawing a map after a real ledger update - never during a passive news glance.
4. TradingView chart reading as a structural analysis input is now the FALLBACK, used only if `apiAnalyze.py` cannot run (e.g. a coin missing from Bybit's API, a data gap) - not the default path.

If source access is limited, state the limitation before drawing or summarizing.

Do not use old screenshots, old TradingView drawings, or old visible Pine levels as the memory source. The ledger is the memory source. TradingView is the news/catalyst source and the display layer - it is no longer the primary structural read.

## Ledger Memory Rule

AutoTrader remembers. TradingView displays.

Use `SETUP_LEDGER.json` as the source of truth for remembered per-coin analysis. For every `Analyze [coin]` request:

1. Open or switch to the current TradingView chart.
2. Read the current coin's ledger entry if one exists.
3. Analyze the live chart and decide whether the ledger setup is still valid, missed, active, TP hit, invalidated, or stale.
4. Update the ledger entry before drawing the chart.
5. Render only the current coin's setup from the ledger onto TradingView.
6. Verify that the visible TradingView map matches the ledger entry.

The ledger must store coin, exchange, trade type, proposed type, bias, BTC/ETH filter, catalyst, setup type, setup rating, setup state, position status, direction, entry, activation basis (`activation_basis`: entry-zone or reclaim-entry), actual entry if known, reclaim/trigger, SL, SL quality, TP, rr_tp1, rr_tp2, invalidation, liquidity, relative strength, final action, analyzed_at (ISO timestamp of the analysis), and notes.

If TradingView fails to render the map, do not lose the setup. Keep the ledger updated and start final output with `CHART NOT MARKED` or `CHART VERIFICATION FAILED`.

The moment any TradingView read fails (blank canvas after the mandatory pause, retry cap hit, verification mismatch), stop and send the user a short message stating the failure plainly - before doing anything else, including before falling back to Bybit API/kline data. Do not fold "chart failed, falling back to X" into the middle of an otherwise-normal-looking full analysis where it reads as one flagged line rather than a real pause. The user has explicitly said (2026-07-28) that a silent fallback made it impossible to tell which numbers came from the live chart versus an API substitute until they checked their own screen - the fallback itself can be legitimate and correctly labeled in the final output and still fail this rule if it wasn't surfaced as a stop-and-tell moment first.

The user's timezone is UTC+1 (GMT+1). State analysis times in that frame, or give both UTC and UTC+1, rather than defaulting to bare UTC.

Do not treat TradingView Pine/drawings as persistent memory. If TradingView loses or hides a setup during symbol switching, redraw it from the ledger.

## Ledger Validity Gate

Before drawing any saved setup, compare the current TradingView chart to the coin's ledger record.

Classify the setup lifecycle:

- Valid / Waiting
- Triggered But Not Entered
- Active / Manage
- TP Hit / Manage
- SL Hit / Invalidated
- Missed / No Chase
- Failed Reclaim
- Stale / Reanalyze
- No Clean Setup

Rules:

- If the saved setup is still valid, draw or keep that coin's Pine slot.
- If price has hit TP, update the ledger state to `TP HIT / MANAGE` before drawing.
- If price has hit SL or invalidation, update the ledger state to `INVALIDATED`, remove/hide the setup, and journal only if useful.
- If price moved too far without entry, update to `MISSED / NO CHASE`.
- If reclaim failed, update to `FAILED RECLAIM` or `WAIT RECLAIM`.
- If structure changed enough that old levels are no longer useful, reanalyze fresh and overwrite that coin's ledger record.
- If no clean setup remains, update to `WAIT / NO TRADE` and keep the chart mostly clean.

Never draw a ledger setup just because it exists. Draw it only after it passes this validity gate.

## Ledger Hygiene Rule

Keep `SETUP_LEDGER.json` compact and current:

- Maintain one active setup record per coin symbol.
- Update that coin's existing record in place when levels, state, or position status change.
- Do not append duplicate records for repeated analyses of the same coin.
- Keep only the latest active/watch setup in `setups`.
- Move completed, invalidated, stale, TP/SL-hit, or learning-review items into `journal` only when they are worth reviewing.
- Keep journal entries concise: coin, date, setup type, result, mistake tag, and one short note.
- Do not store long narrative analysis inside the ledger.
- `bias` and `notes` on an active setup describe the CURRENT state only - not a growing log of every correction. When a level or read changes, replace the old explanation, don't append "2026-07-15 follow-up: ... 2026-07-16 follow-up: ..." onto it. That history already exists in git commits (every ledger write this session gets committed) and, once a setup closes, in its journal entry - repeating it inside the active record costs real tokens on every future read/edit for zero benefit, since nothing reads an active setup's history, only its current call.
- If a field is approaching a couple hundred words, that's the signal to compress it back to current-state-only, not to keep appending.
- If the ledger entry is older than the current chart structure, classify it as stale and overwrite it with the fresh setup.
- If a setup is no longer useful and not worth journaling, replace it rather than preserving old levels.

## Pre-Analysis State Check

Before choosing a trade, classify the chart state:

- Fresh Setup
- Existing Active Trade
- Missed Setup
- TP Hit / Manage
- Invalidated Setup
- Stale Map / Needs Cleanup

If the chart has stale or conflicting drawings, mark the state as `Stale Map / Needs Cleanup` before analysis.

## Timeframe Rules

First decide the trade type:

- Normal intraday/day trade: use 1D -> 4H -> 1H, with entry planned on 1H, refined to 15m for the confirmation candle (rejection: full body closes outside the zone with a long wick inside it; OR engulfing: full body covers the previous candle's body). Limit order at the zone's entry line.
- Scalp: use 4H -> 1H -> 15m -> 5m. 4H sets trend, 1H draws the zone, 15m refines it - 5m is where the 9/20 EMA cross, VWAP, and the actual entry live (see Scalp Entry Rule below), at market price.

Mandatory scalp HTF veto:

- Before mapping any scalp, mark 4H supply/demand first.
- A scalp long into overhead 4H supply, or a scalp short into 4H demand, is capped at Watch Only unless the setup is explicitly a reaction trade at that 4H zone.
- Reclaims, retests, and confirmations are judged by candle closes on the entry timeframe, not wicks.

Scalp API pre-screen (added 2026-07-30; downgraded from hard gates to reported context 2026-07-31 - see below):

- Before the TradingView structural read, run `node scripts/scalpScreen.mjs SYMBOL` for every coin resolving to Scalp trade type. This is a fast, objective pre-screen sourced from Bybit kline data - it does not replace the chart as source of truth, it decides whether a chart pass is worth spending before doing it.
- VWAP and directional efficiency are REPORTED CONTEXT ONLY - they are NOT vetoes. This was changed 2026-07-31 after a backtest (8 coins, 1000 1H bars each, 1 ATR stop / 1.5R target) showed the hard gates were actively counterproductive: bars passing `efficiency >= 0.4 + slope agreement` averaged -0.123R at a 35.0% win rate, materially WORSE than the ungated baseline (+0.033R, 41.4%), and worse than the sub-0.25 "choppy" bars the gate was rejecting (+0.031R, 41.4%). The result held across 7 of 8 coins. Cause: high directional efficiency means price has already run, which on 1H crypto precedes reversion more often than continuation - a trend-following filter bolted onto a mean-reversion-at-structure framework, selecting against the very setups the framework exists to take.
- Do not reintroduce either as a hard veto without a fresh backtest showing positive expectancy. Report the values, note whether the move looks extended or orderly, and let the structural read make the call.
- Caveat carried from that same backtest: the ungated baseline was only +0.033R/trade, which is inside noise and would be consumed by fees and slippage. This means mechanical indicator filtering showed no measurable edge in EITHER direction on these coins - it does not mean removing the gates creates one. Any real edge must come from the discretionary zone/structure read, which that test did not measure.
- The script's 4H ATR% is the SL-buffer basis for the SL Buffer Calibration Rule below - use it instead of re-deriving ATR by hand from chart candles.
- Always proceed to the full chart-based structural read (4H veto, zones, liquidity, dual-activation). The pre-screen supplies context and the ATR buffer; it no longer decides whether a coin is worth a chart pass.

Scalp Entry Rule (v4, 2026-08-01 - backtest-validated, see `scripts/scalpBacktestV3.py` and `backtests/2026-07-31/`; CORRECTED 2026-08-03 - a documentation error previously said the cross was on 15m, but the actual backtested code has always computed it on 5m. This section now matches the code and the user's stated flow: 4H trend -> 1H zone -> 15m refinement -> 5m EMA/VWAP/entry): the entry trigger is a 9/20 EMA cross on 5m - NOT 15m. 15m is the zone-refinement timeframe only, never the signal timeframe.

- Cross: 9 EMA crosses above 20 EMA on the 5m chart = long signal; 9 crosses below 20 = short signal.
- VWAP confirmation: long needs price above the session VWAP (computed on 5m), short needs price below it. VWAP resets every day (00:00 UTC anchor) - do not use a rolling window.
- Slope confirmation: after the cross, both EMAs (on 5m) must be sloping in the trade's direction.
- Zone alignment is MANDATORY, not a soft preference: the 5m cross must occur at or immediately after a reaction (retest/rejection) at the 15m-refined zone (itself drawn from a 1H zone). This was tested both ways - zone-required trades hold the edge; the framework's earlier "consider" wording undersold how load-bearing this is. No zone, no trade, regardless of how clean the cross looks. If price has already moved away from the zone by the time the 5m candle confirms the cross, that candle no longer qualifies as "at or immediately after" - treat it as a missed signal, not a chase; wait for a retest or a fresh reaction.
- The confirming candle must be a CLOSED 5m candle, not a live/forming one.
- Shorts only, two extra required gates (longs are unaffected by either): 1D structure must also read bearish or range/neutral (not just 4H) before a short is valid, AND a micro-structure break on the same 5m signal timeframe (price breaking the prior 5-candle swing low) must confirm right at the signal. Backtest result: adding these turned shorts from a net loser (-0.032R avg, -1.13R total over the test period) into a net winner (+0.140R avg, positive total) with no cost to longs. Keep both, permanently.
- Entry at market price (not a limit order - this is the scalp/Intraday distinction: Intraday uses a limit at the zone edge, Scalp chases the confirmed cross at market).
- SL beyond the zone's exit line (the far edge, not the entry edge), buffered by the SL Buffer Calibration Rule's ATR method.
- TP at the prior peak/swing before the move, or the nearest opposing 15m zone, whichever is closer - respect the TP Zone Validity Rule (near edge only).
- R:R floor 1:1.5, 1:2 preferred when the next zone allows it - same floor logic as Trade Rules below.
- Time-stop (v4, tuned): at 6 hours held, if the trade is at -0.3R or worse (i.e. actively losing, not merely undecided), tighten the stop to breakeven. Do NOT use a "must be +0.3R favorable by 6h or breakeven" version - that was tested and backtested at -0.132R avg / 15.4% win rate, a severe regression, because it cuts off winners that simply hadn't resolved yet rather than protecting against real drawdown. The -0.3R-or-worse version tested at +0.234R avg / 37.7% win, beating the no-time-stop baseline (+0.205R avg).
- Session filter: tested and REJECTED (2026-08-01) - restricting shorts to 06:00-17:00 UTC and half-sizing 18:00-23:00 cost ~6R over the test period with no offsetting benefit. Do not add a session filter without fresh backtest evidence it helps; the prior attempt didn't.

False Zone Break Rule (added 2026-07-31): a break of a mapped zone is false - and the zone stays live, not invalidated - if it was wick-only: the candle's high/low pierced the level but the candle closed back inside the zone. Only a close beyond the zone (per the existing close-based confirmation standard above) counts as a real break. Do not treat a wick-only pierce as invalidation, a failed reclaim, or a trigger of any kind - it is noise until a close confirms it.

If the user gives only a coin name, choose the trade type based on chart structure, volatility, distance to target, and setup quality.

The chart table and final written output must use the exact same trade type.

## Market Filter

Use BTCUSDT and ETHUSDT as confidence filters:

- If BTC/ETH align with the setup, confidence increases.
- If BTC/ETH conflict strongly, reduce confidence or skip the trade.
- BTC/ETH are confidence filters only, not mandatory confirmation.

Always state the BTC/ETH filter as:

- Aligned
- Mixed
- Conflicting

## Catalyst / News Gate

Before finalizing a call, check whether scheduled or breaking catalysts/news can override structure:

- Macro: CPI, FOMC, jobs/NFP, major rate decisions.
- Coin-specific news: token unlock, exchange listing/delisting, hack/exploit, live headline, major partnership, legal/regulatory update, chain outage, governance vote, or large ecosystem event.

Classify the catalyst as:

- Clear
- News Risk
- Unverified

Rules:

- Catalyst includes news, but the source hierarchy still applies.
- If the user has not explicitly asked for external news/API checks and TradingView does not show enough news context, classify as Unverified.
- If a high-impact event is imminent or unfolding, mark News Risk and cap Final Action at Wait or No Chase, unless the user explicitly says to trade the event.
- If the catalyst cannot be verified, mark Unverified and say "catalyst unverified - check manually." Do not assume Clear.

## Method

Use supply/demand, trendlines, liquidity, reclaim levels, invalidation, relative strength, and R:R.

## Rules Engine Checklist

Analyze every setup with this checklist before giving a final call.

Setup Type:

- Liquidity Sweep + MSS
- Failed Reclaim / Deviation
- FVG / Imbalance Retest
- Breaker / Failed Supply-Demand Flip
- Compression-to-Expansion Breakout
- Standard Supply/Demand Retest
- No Clean Setup

Direction:

- Long
- Short
- Wait / No Trade

Entry Basis:

- Entry-zone activation
- Reclaim-entry activation
- Rejection candle
- Break-and-retest
- No entry yet

Reclaim Status:

- Not reclaimed
- Reclaimed and holding
- Reclaimed but no entry
- Failed reclaim / deviation

SL Quality:

- Safe
- Vulnerable
- Too Tight

BTC/ETH Filter:

- Aligned
- Mixed
- Conflicting

Catalyst:

- Clear
- News Risk
- Unverified

Final Action:

- Trade
- Wait
- Skip
- No Chase

## Setup Rating Model

Always assign a plain-language setup rating.

Clean Trade:

- Clean HTF zone.
- Clear liquidity sweep or clean reclaim/retest structure.
- SL is Safe.
- TP1 meets the trade-type floor and TP2 sits inside the trade-type band.
- BTC/ETH are aligned or not strongly conflicting.
- Entry is not late.

Conditional Trade:

- Valid setup but one important weakness exists.
- TP1 meets the trade-type floor.
- SL is Safe or Vulnerable, not Too Tight.
- Confidence is reduced, but setup can remain conditional.

Watch Only:

- Watch only.
- Useful levels exist, but trade is not ready.
- Needs reclaim, retest, rejection, MSS, or better R:R.

Conditional Trade - Reduced Size:

- See the Conditional (Reduced-Size) Tier in Trade Rules. TP1 is sub-floor but within the defined reduced-size band (1.5-2R Intraday / 1.2-1.5R Scalp), every other gate passes, and the trigger has actually confirmed.
- Trade candidate at half normal risk (0.75% instead of 1.5%), not full size.

Skip / No Trade:

- No clean invalidation.
- SL is Too Tight.
- Proper structural SL puts TP1 below the trade-type floor (including below the reduced-size band).
- Price is late or chasing.
- BTC/ETH strongly conflict and the coin has no clear relative strength.

Final action by rating:

- Clean Trade = Trade candidate if entry condition is met.
- Conditional Trade = Conditional trade or reduced confidence.
- Conditional Trade - Reduced Size = Trade candidate at half risk if the trigger has confirmed.
- Watch Only = Wait / monitor only.
- Skip / No Trade = No trade.

## Pattern Priority

Prioritize these patterns first:

1. Liquidity Sweep + MSS.
2. Failed Reclaim / Deviation.
3. FVG / Imbalance Retest.
4. Relative Strength Filter.

Use these as secondary patterns:

- Breaker / Failed Supply-Demand Flip.
- Compression-to-Expansion Breakout.
- Standard Supply/Demand Retest.

Delay or avoid these for now:

- Harmonics.
- Elliott Wave.
- RSI divergence-heavy systems.
- Too many indicators.
- Fully automated execution logic.

## Pattern Rules

Liquidity Sweep + MSS:

- Identify obvious buy-side or sell-side liquidity.
- Confirm price sweeps the liquidity with a wick or displacement.
- Require a market structure shift after the sweep before treating it as reversal-ready.
- Entry is usually a retest, FVG fill, or demand/supply reaction after MSS.
- If MSS is absent, mark WAIT REACTION or WAIT RECLAIM.

Failed Reclaim / Deviation:

- Identify a key reclaim/resistance/support level.
- If price reclaims but cannot hold, treat it as a potential trap.
- For longs, failed reclaim under resistance is not active long management.
- For shorts, failed reclaim can become a short setup only after rejection and breakdown/retest.
- If price reclaims but no entry was taken, use RECLAIMED / WAIT RETEST or NO CHASE.

FVG / Imbalance Retest:

- Use only after an impulsive displacement candle or clear imbalance.
- FVG is an entry refinement tool, not a standalone reason to trade.
- Entry must still respect supply/demand, liquidity, invalidation, and R:R.
- If FVG entry makes SL too tight or structural SL puts TP1 below the trade-type floor, mark WAIT / SKIP.

Breaker / Failed Supply-Demand Flip:

- Use when price breaks through a prior supply/demand zone, then retests it from the other side.
- The old zone must act as the opposite side on retest.
- Entry requires rejection/acceptance at the retested zone.
- Invalidation goes beyond the breaker zone wick/base, not inside it.

Compression-to-Expansion Breakout:

- Use when price coils under resistance or above support with tightening volatility.
- Prefer break-and-retest, not a blind breakout chase.
- If expansion happens directly into HTF supply/resistance, mark NO CHASE or WAIT RETEST.
- BTC/ETH alignment materially affects confidence.

Relative Strength Filter:

- For longs, prefer coins holding structure better than BTC and ETH.
- For shorts, prefer coins breaking structure weaker than BTC and ETH.
- Weak BTC/ETH + coin bouncing into resistance = reduce confidence or skip.
- Weak BTC/ETH + coin cleanly reclaiming with strong relative strength = moderate confidence, not automatic trade.

## Trendline Rules

- Wick-to-wick.
- 3 touches = valid trendline.
- 2 touches = tentative trendline.
- If no clean trendline exists, skip it.

## Supply And Demand Rules

- Use full candle wick range or base before impulsive move.
- Mark HTF supply/demand first.
- Do not force zones if unclear.
- Prefer clear labeled horizontal lines over large boxes.

## Liquidity And SL Quality Rules

Before giving an entry:

- Identify the nearest obvious liquidity above and below the setup.
- For longs, check the nearest sell-side liquidity below the entry zone.
- For shorts, check the nearest buy-side liquidity above the entry zone.
- SL must be beyond both the obvious liquidity and the full demand/supply wick/base.
- Do not place SL on the first obvious local low/high if that level is likely to be swept.
- If the proper structural SL puts TP1 below the trade-type floor, mark WAIT / SKIP.
- Always classify SL Quality as Safe, Vulnerable, or Too Tight.
- SL earns Safe only when it sits beyond both the nearest obvious liquidity and the full zone wick/base, with buffer for a sweep.
- If the properly placed SL is still Vulnerable, widen the zone or skip; Vulnerable is a warning state, not an acceptable default rating.

## SL Buffer Calibration Rule

- The buffer added beyond the structural level (wick high/low or cluster edge) must be derived from that specific coin's own realized volatility, never a flat percentage of price carried over from a different coin's analysis.
- Method: pull recent 4H candle history and compute the average true range (high minus low) as a percentage of price. Set the buffer as a fraction (around 50%) of that average range, added beyond the technical level - not a round percentage picked because it "looks reasonable."
- Do not reuse a buffer percentage just because a prior analysis in the same session used it. Different coins have meaningfully different volatility profiles - one session found JTO's average 4H range at ~3.5% of price, US's at ~8.5%, and PUMPFUN's at ~3.6%, despite all three initially being given nearly the same ~2.6-3% SL buffer, which was later confirmed to be an unexamined borrowed heuristic, not independent per-coin derivation.
- Recheck this specifically whenever setting or widening an SL. It is exactly as easy to silently drift into a copied number here as it is to violate the TP Zone Validity Rule by skipping a zone - both come from reusing a prior answer instead of re-deriving it from the current coin's own data.

## TP Zone Validity Rule

- Every TP in the ladder sits at the NEAR edge (the entry) of its zone - the zone top for a short, the zone bottom for a long - never inside it, never past its far edge. The near edge is the only level guaranteed reachable if the move works at all, because defenders react at the edge, not the middle.
- TP1 = near edge of the first opposing zone. No precondition.
- TP2 = near edge of the second zone, but only counts as a real (non-conditional) target once the first zone is confirmed broken (a close through it, holding). Until then it is a stretch target, not something to size the trade around.
- TP3 (and beyond) = near edge of each subsequent zone, same conditional rule chained one zone deeper each time.
- No TP may span more than one zone. This was the original form of the rule and still holds - it falls directly out of the near-edge rule above, since the near edge of zone N is always before zone N+1 begins.
- If a TP's placement (round number, old note, arbitrary R multiple) turns out to land inside or beyond a second zone once real zone boundaries are mapped, correct it back to just outside the first zone - do not keep the deeper number for a better-looking R:R.
- Deeper TPs (TP2, TP3) may target beyond further zones, but only as conditional/stretch targets: valid to display, not valid to lean on for the R:R floor check, unless the zone(s) between the current TP and that deeper one are confirmed broken (a close through, holding) as the trade develops.
- Re-check this whenever new zone boundaries are drawn or the chart reveals structure that wasn't visible at initial analysis - it is as easy to violate silently as the SL-too-tight mistake, and gets caught the same way: go back and look at what is actually between entry and the target.

## Extension And Chase Rules

- Do not chase price.
- If the coin has already made a strong extended move, do not use blind limit entry.
- For extended coins, require a rejection candle, reclaim, or break-and-retest before entry.
- If price has already rejected the trigger/reclaim level, downgrade the setup to WAIT until demand/supply confirms.
- If setup is late, clearly label NO CHASE.

Candle-Shape Judgment Rule (applies to every coin surfaced, not just full Analyze):

- Before presenting any coin as a candidate - from a mover scan, tier2, or a full Analyze - classify the shape of its recent move: an orderly, sustained trend (tradeable, has a real directional expectation) versus a long wick with an immediate reversal (spike up then instant dump, or the reverse - noise/a liquidity sweep, not a real move).
- A coin passing a raw %/range filter is not automatically a candidate. `scanMovers.mjs`'s range%/net% ratio can flag both a genuine sweep-and-orderly-reclaim (tradeable, e.g. FARTCOIN's dip-sweep-bounce) and a spike-and-instant-reverse (not tradeable) with a similar signature - the two must be told apart by eye before reporting either as a find.
- State a directional expectation for every coin mentioned: continuation, mean-reversion against an extension (see Parabolic Spike Rule below), or explicitly "noise/skip, not tradeable." Do not just report the stat line and let the user filter it themselves.
- Reference: user flagged this 2026-07-28 after DIA/EUL/ACH/AKE were repeatedly surfaced despite each showing a long wick with an immediate reversal, contrasted with PHAROSUSDT.P's orderly climb, which had a clear, statable short-the-extension read.

Parabolic Spike Rule:

After a single-candle (or near-single-candle) extension of roughly 20%+ with an Unverified catalyst:

- Do not map pullback longs inside the impulse candle's own range. There is no demand mid-candle; entry zones must sit at a visible base/consolidation or at the impulse origin.
- The valid patterns are: (a) liquidity sweep + failed reclaim SHORT per Pattern Priority, or (b) wait for the retest of the impulse origin base.
- Any TP/supply level wick-swept during the spike is no longer virgin liquidity; treat first-touch magnets as consumed and take partials faster.
- Reference: USUSDT.P 2026-07-07 journal entry, mistake tag SWEEP_FAIL_MISREAD.
- This applies to short retest entries too, not just longs: on 2026-07-28, PHAROSUSDT.P's proposed short retest zone (0.44-0.4527) was placed inside the reversal candle's own range instead of at the real resistance zone the user had drawn (0.48-0.5225, actual mid-June consolidation) - the same mistake mirrored to the short side. Price reversed before even tagging real structure, which made the zone void, not confirmed. Always use the user's own drawn zones or verified consolidation ranges as the entry zone - never a point picked from inside the impulse/reversal candle itself, for either direction.

## Setup State Lifecycle Rules

Before updating or summarizing an existing chart setup:

- Check whether the previous setup is still active, already hit TP, hit SL, or changed into a new decision zone.
- If TP1/TP2 has already been hit, do not leave the old entry/SL/TP labels as the active setup.
- If price reaches the old TP and enters demand/supply, refresh the map to the new decision state before summarizing.
- If the setup direction changes, remove or reset the old direction labels first.

Use a clear setup state:

- READY
- ACTIVE / MANAGE
- TP1 HIT / MANAGE
- TP2 HIT / MANAGE
- RECLAIMED / WAIT RETEST
- WAIT REACTION
- WAIT RECLAIM
- WAIT RETEST
- WAIT / SKIP
- NO CHASE
- INVALID

## Entry Activation Rules

State which one controls activation before drawing the map:

- Entry-zone activation.
- Reclaim-entry activation.
- Rejection candle activation.
- Break-and-retest activation.
- No entry yet.

Reclaim alone never equals active unless reclaim-entry activation is explicitly chosen.

Entry zone = where the trade can become active.

Reclaim / trigger = confirmation or permission level unless the entry style is explicitly break-and-retest.

Do not mark ACTIVE / MANAGE from reclaim alone when the planned entry is a limit/pullback zone.

If price reclaims the trigger but never trades into the planned entry zone, use RECLAIMED / WAIT RETEST or NO CHASE.

Mark ACTIVE / MANAGE only when price has traded through the planned entry zone after the setup start, or when the analysis explicitly says the reclaim/break-and-retest is the entry.

If both a pullback entry and reclaim entry are possible, state which one controls activation before drawing the map.

Dual-Activation Rule (mandatory, not situational): every setup with a defined reclaim or trigger level must map BOTH a deep pullback zone AND a break-and-retest activation at that level, and state which one is primary. This applies whenever a reclaim/trigger level exists, not only when momentum is judged to be active - "is this coin in expansion" was too easy to skip. A setup that maps only a deep limit zone is incomplete and must not be presented as final. This rule exists because the scorecard's own history shows repeated MISSED_ENTRY outcomes (HYPE, XRP, SPORTFUN, APE) where price ran through a reclaim without ever returning to a mapped deep zone - a break-and-retest trigger would have caught or correctly scored every one of them.

If price is above reclaim but entry was missed, do not convert the missed trade into active management. Refresh the setup as WAIT RETEST, NO CHASE, or a new breakout-retest setup.

## Position Status Rules

Use position status as an additional field, not as a replacement for setup state.

The Pine/map logic must separate:

- Setup State: what price has done relative to the plan.
- Position Status: whether the user is actually in a trade.

Do not infer that the user is in a position just because price crossed the entry, reclaim, trigger, or TP.

Default Position Status is `NO POSITION` unless the user explicitly says they entered, the exchange position is visible, or the analysis intentionally marks the setup as a simulated/assumed triggered trade.

Allowed Position Status values:

- NO POSITION
- ENTERED LONG
- ENTERED SHORT
- UR PROFIT
- UR LOSS
- TP HIT / MANAGE
- SL HIT
- N/A

For longs:

- If Position Status is ENTERED LONG, price above actual entry = UR PROFIT.
- If Position Status is ENTERED LONG, price below actual entry but above invalidation = UR LOSS.

For shorts:

- If Position Status is ENTERED SHORT, price below actual entry = UR PROFIT.
- If Position Status is ENTERED SHORT, price above actual entry but below invalidation = UR LOSS.

Use actual entry price when known. If actual entry is unknown, use the planned entry midpoint only after the user confirms the position was entered from the planned zone.

If the setup has not entered yet, even if reclaim has happened, show Position Status as `NO POSITION` or `N/A`.

Only show Setup State = ACTIVE / MANAGE when the entry condition has been met and position confirmation exists, or when the map is explicitly tracking a simulated triggered setup.

If price has moved beyond the entry zone but no position was confirmed, show Setup State as `MISSED / NO CHASE`, `WAIT RETEST`, or `RECLAIMED / WAIT RETEST`; do not show UR PROFIT or UR LOSS.

If TP or SL has already been hit, prioritize TP HIT / MANAGE or INVALID over unrealized status.

## Chart Cleanup Gate

Before drawing:

- Treat any visible AutoTrader map whose table coin does not match the current chart symbol as stale by definition.
- Preserve valid existing analysis that belongs to the current chart symbol.
- Hide, remove, or update only drawings/maps that belong to another coin or that conflict with the current analysis.
- Do not wipe a coin's own prior analysis just because a new coin is being analyzed elsewhere.
- Do not leave old wrong-coin levels on the new chart.
- Do not add new markings until the chart is clean.
- If old objects cannot be removed reliably, say so clearly before drawing.

If an old same-coin direction conflicts with the new direction, update or replace that coin's map after explaining the lifecycle change.

If an old wrong-coin direction conflicts with the new chart and cannot be removed or hidden, do not draw a new map on top of it unless the user approves.

If multiple AutoTrader Trade Map indicators are visible and the stale one cannot be safely identified, stop and state `STALE MAP RISK`.

## Per-Coin Persistence And Symbol-Safety Rule

The desired behavior is per-coin persistence:

- XRP analysis should remain attached to XRP.
- FARTCOIN analysis should remain attached to FARTCOIN.
- AVAX analysis should remain attached to AVAX.
- When switching away and later returning to a coin, that coin's own prior analysis should still be visible unless it has been updated, invalidated, or deliberately removed.
- Analysis from one coin must not appear on another coin.

Persistence comes from `SETUP_LEDGER.json`, not from TradingView. Pine is only a renderer. The preferred display is one multi-symbol AutoTrader map whose guarded slots are generated from the current active ledger records.

For every `Analyze [coin]` request:

1. Switch/open the requested symbol first.
2. Immediately inspect visible AutoTrader tables, labels, lines, and drawings.
3. Load the coin's ledger entry and decide whether it is still active, hit TP/SL, invalidated, missed, or needs an update.
4. If the visible analysis belongs to a different coin, hide/remove/update that wrong-coin display before analyzing the current coin.
5. Do not summarize the new coin while another coin's entry, SL, TP, trigger, or table is visible.
6. After updating the ledger and rendering, verify the visible map/drawings match the current symbol and ledger entry.

If the map cannot be reset, updated, hidden, or removed, final output must start with `STALE MAP RISK`.

When leaving a completed analysis, the ledger entry must remain saved even if TradingView later hides the visual map.

## Pine Indicator Rule

Use Pine cautiously because a single Pine instance is layout-wide. The safe pattern is one multi-symbol map with a strict symbol guard per coin slot.

Preferred Pine workflow:

1. Use `AUTOTRADER_TRADE_MAP_TEMPLATE.pine` as the reusable multi-symbol renderer.
2. Generate or update Pine slots from the active records in `SETUP_LEDGER.json`.
3. Each slot must have a strict `syminfo.ticker == coin` guard.
4. When the chart is XRP, only the XRP slot should render; when AVAX, only AVAX; when DOGE, only DOGE.
5. Reanalysis updates that coin's ledger record and that coin's Pine slot only.
6. Do not create duplicate/conflicting AutoTrader map indicators unless the user approves.

Do not overwrite the ledger entry for another coin to analyze the current coin.

Do not rewrite the script for every coin unless the indicator itself needs improvement.

If Pine Editor cannot be opened or updated, say so clearly.

If old Pine levels from a previous coin are visible on the current coin, hide/remove them before analysis.

If the existing Pine map cannot render the current ledger entry, say that the display failed and keep the ledger as the source of truth.

The Pine map must include a symbol guard:

- Compare the current chart symbol to each slot's coin.
- If they do not match, that slot must not plot, label, or table.
- Do not show a full old setup table on the wrong coin.
- If a minimal warning is needed, show only `STALE MAP - UPDATE COIN`.

Keep Pine status-line text quiet so the indicator name/inputs do not overlap the top-right summary table.

If possible, make the setup-state label update dynamically when reclaim, TP, or invalidation conditions are met.

## Pine Map Requirements

The Pine map should show only the current setup:

- Coin.
- Trade Type: Scalp or Intraday.
- Direction: Long, Short, or Wait.
- Setup Rating: Clean Trade, Conditional Trade, Watch Only, or Skip / No Trade, if space allows.
- Setup State.
- Position Status: NO POSITION, ENTERED LONG, ENTERED SHORT, UR PROFIT, UR LOSS, or N/A.
- Entry zone as two labeled horizontal lines by default.
- No shaded risk/reward zones unless explicitly requested.
- SL / invalidation line.
- TP1 / TP2 lines, optional TP3.
- Trigger / reclaim / break-retest line.
- Compact right-side labels.
- Status labels only when useful.
- Small summary table only if it does not cover price action.
- No long status-line string that overlaps the chart or summary table.

If a confirmed position is active, combine setup state and live P/L into one compact on-chart label, for example ACTIVE / MANAGE / UR PROFIT.

If no position is confirmed, the chart label should say NO POSITION, WAIT RETEST, WAIT RECLAIM, MISSED / NO CHASE, or ENTRY AREA instead of UR PROFIT / UR LOSS.

Do not add a separate floating UR PROFIT / UR LOSS label if it can be included in the active/manage label.

The active/manage label should track the current market price, not sit at a fixed old level.

Level lines should extend slightly forward so the right-side labels touch or nearly touch their lines.

If no setup:

- Direction = Wait.
- Mark only the key decision level if useful.
- Otherwise leave the chart clean.

## Color Rules

- Red = supply, resistance, short zones, SL/invalidation, short TP.
- Green = demand, long zones, bullish reaction zones, long TP.
- Blue = reclaim, trigger, confirmation, break/retest.
- Grey = deep liquidity or backup targets.

## Label Rules

Use compact labels only:

- SL 0.545
- SHORT TOP 72
- SHORT BOTTOM 71.2
- LONG TOP 0.43
- LONG BOTTOM 0.42
- RECLAIM 0.545
- TRIGGER < 68.95
- TP1 68
- TP2 64
- INVALID < 0.42
- NO CHASE
- RECLAIMED / WAIT RETEST
- WAIT REJECTION
- WAIT REACTION
- WAIT RECLAIM
- WAIT / SKIP
- ACTIVE / MANAGE / UR PROFIT
- ACTIVE / MANAGE / UR LOSS
- UR PROFIT
- UR LOSS

## Chart Display Rules

- Clean chart first, summary second.
- Close Pine Editor/indicator panel when finished.
- Final view should be the chart, not code.
- Use the minimum markings needed to understand the setup.
- Do not clutter the chart with every possible level.
- Prefer clear labeled horizontal lines over boxes.
- Do not use large shaded risk/reward boxes by default.
- Only use a small clearly labeled zone box when the level cannot be understood with two horizontal lines.
- Always indicate whether the setup is a Scalp or Intraday trade.

## Post-Drawing Verification Gate

Verification is an observed action, not a recollection. After saving/closing the Pine Editor:

1. Close the Pine Editor and bring the chart into full view.
2. Take a fresh screenshot or read of the rendered chart. Do not rely on the values typed into the editor or the ledger record alone; read what is actually displayed.
3. Read the rendered card/labels and compare each field, one by one, against the ledger record that was just written:
   - Coin and trade type.
   - Direction / proposed type.
   - Setup state and position status.
   - Entry, SL, TP levels (on-chart lines/labels).
   - R:R values.
   - Updated/analyzed timestamp.
4. Confirm no old conflicting levels or wrong-coin drawings are visible.
5. Only after this observed field-by-field match may the normal output format be presented as completed and verified.

If any field does not match on the observed re-check, state `CHART VERIFICATION FAILED`, name the exact field(s) that disagree, and do not present the setup as completed.

## Pine Script Corruption Recovery

Symptom: the indicator legend shows a red warning icon with `Compilation error: Script could not be translated from: <garbage string>`, or the Pine Editor content itself is a short random string instead of real code. This is not a chart-side drawing failure; the script's saved source is corrupted. A page reload alone does not fix it, and saving a corrected script does not automatically reattach it to a chart if the broken instance was removed.

Recovery sequence:

1. Reload the chart tab. This flushes stale/ghost indicator renders that persist in the legend after removal but do not appear in the Object Tree - do not trust the legend alone as a sign an old instance still exists; check the Object Tree.
2. Reopen the Pine Editor for the script. Confirm the corruption by inspecting the actual line content, not just the error banner.
3. Select all and replace with the correct script using a real paste event: write the correct content to the OS clipboard and paste natively. If clipboard permission is unavailable in the automation context, dispatch a synthetic `ClipboardEvent('paste', ...)` on the editor's `.inputarea` element with a `DataTransfer` payload as a fallback - typing character-by-character risks Monaco auto-close corruption on a 200+ line ternary-heavy file.
4. Save, then explicitly use the editor's "Add to chart" action. Saving a script does not reattach it if no instance is currently on the chart.
5. Run the full Post-Drawing Verification Gate: fresh screenshot, read the rendered card, confirm every field against the ledger. Do not conclude success from the absence of an error icon alone; confirm the card and lines actually render with correct values.

If any step cannot be completed, do not silently continue: state `STALE MAP RISK` or `CHART NOT MARKED` per the Failure Protocol below, and journal the incident with mistake tag `PINE_SCRIPT_CORRUPTED` - this is a technical incident, not a trading mistake, and should not count against thesis accuracy.

## Failure Protocol

If chart marking fails:

- Start final answer with `CHART NOT MARKED`.
- Explain why marking failed.
- Do not give the normal trade-analysis output.
- You may still give the setup levels, but label them `SETUP ONLY - NOT DRAWN ON TRADINGVIEW`.
- Offer to redraw the setup from the ledger when chart control is available.
- Do not imply the chart was updated.

If cleanup fails:

- Start final answer with `STALE MAP RISK`.
- Explain what could not be removed.
- Do not draw conflicting new levels unless the user approves.

If verification fails:

- Start final answer with `CHART VERIFICATION FAILED`.
- Explain what does not match.
- Do not give the normal trade-analysis output.
- You may still give the setup levels, but label them `SETUP ONLY - NOT VERIFIED ON TRADINGVIEW`.
- Offer to redraw the setup from the ledger when chart control is available.

## Trade Rules

- R:R is measured from the conservative edge of the entry zone (entry high for longs, entry low for shorts) to each TP against the SL. Confirmation fills happen at the edge, so midpoint math flatters the ratio; never use the midpoint for the floor check.
- Scalp floor: TP1 at least 1:1.5, and TP2 placed at structure inside the 1:2.5 to 1:3.5 band.
- Intraday floor: TP1 at least 1:2, and TP2 placed at structure inside the 1:3 to 1:4 band.
- If TP1 is below the floor, cap the setup rating at Watch Only or Skip / No Trade - EXCEPT when the Conditional (Reduced-Size) Tier below applies.
- If TP2 falls outside the band, re-place it at the nearest structural level inside the band; if no structural level exists there, the setup does not fit the template. Never move a TP into empty air to hit a ratio.

### Conditional (Reduced-Size) Tier

A setup whose TP1 (off the conservative entry edge) falls in the 1.5R-2R range (Intraday) or 1.2R-1.5R range (Scalp) - i.e. below the full floor but not far below it - qualifies for `Conditional Trade - Reduced Size` instead of an automatic Watch Only/Skip, but only if every other gate passes cleanly:
- SL is Safe (not Vulnerable, not Too Tight).
- Entry activation has actually triggered (rejection candle confirmed, reclaim confirmed-and-holding, or break-and-retest confirmed) - not "no entry yet."
- Catalyst is Clear or News Risk-with-a-defined-cap, not an active veto-level event.
- BTC/ETH filter is Aligned or Mixed, not strongly Conflicting.

If all four hold, rate the setup `Conditional Trade - Reduced Size` and state explicitly in `final_action`: position size is half the user's normal risk (0.75% of available balance instead of 1.5%, per the Risk Context section), because R:R is genuine but sub-floor. This tier does not apply to setups below 1.5R (Intraday) / 1.2R (Scalp) - those remain Skip / No Trade regardless of how clean the other gates are. This tier never overrides Vulnerable/Too-Tight SL, an unconfirmed trigger, or a hard catalyst veto.
- Store rr_tp1 and rr_tp2 in the ledger record for every setup.
- Do not force a trade.
- If no clean setup exists, say WAIT.
- Even when saying WAIT, always state the proposed trade type:
  - Proposed Long
  - Proposed Short
  - Proposed Wait / No Trade

## Entry Style

Suggest the best entry style:

- Limit at zone.
- Rejection candle.
- Break-and-retest.

Also state the activation basis:

- Entry-zone activation.
- Reclaim-entry activation.
- Rejection candle activation.
- Break-and-retest activation.
- No entry yet.

## Risk Context

Position size is optional unless the user asks.

Per-trade risk (corrected 2026-08-01 - was a flat 1.5% for everything, which didn't match either strategy doc): Intraday 1% of available balance per trade; Scalp 0.5% per trade.

Optional risk rules:

- Max 1-2 open trades.
- Max daily loss 3%.
- Stop after 2 losses in a row.

## Output Format

After marking and verifying the chart, summarize like this:

Trade Type:
Proposed Type:
Coin:
Bias:
BTC/ETH Filter:
Catalyst:
Setup Type:
Setup Rating:
Setup State:
Position Status:
Main Setup:
Entry:
Activation Basis:
SL:
SL Quality:
TP:
R:R:
Entry Style:
Invalidation:
Nearest Liquidity:
Reclaim Status:
Relative Strength:
Alternate Setup:
Final Action:
Final Prediction:

Optional journal line:

Journal Tag:

## Plain-English Setup Summary (Required)

Every analysis ends with a short, plain-language summary of the trade in one or two sentences, written like explaining it to someone who doesn't read the field list - e.g. "Wait for price to drop back into 486-492 and hold, then buy there with a stop below. Alternate: if price breaks and holds above 522 instead, buy the retest of that level." No jargon dump, just: what to wait for, what confirms it, and roughly where the entry/stop would go. If there's no valid setup at all, say so plainly ("nothing tradeable right now, just watching X").

Accompany this with a visual whenever practical, generated as one combined artifact/image - not a separate summary card and a separate zone diagram. The single visual should carry both: a compact summary card (coin, direction, setup state, entry, SL, TP, R:R) and the price-zone diagram (levels on a price line/mini chart) together in one piece. This sits alongside the full field-by-field Output Format above, not instead of it - the full format is the complete record, the combined card+diagram is the fast-read companion.

## Important

If the trade is not ready, still show the conditional setup levels and clearly label WAIT, WAIT / SKIP, or NO CHASE.

Do not force a trade.

Do not leave previous drawings or old coin levels on the chart.

Clean chart first, summary second.

If chart cleanup, marking, or verification fails, do not provide the normal final output format as completed work. Use the failure protocol, include the setup only if clearly labeled as not drawn/verified on TradingView, and offer to redraw from the ledger.
