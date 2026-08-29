# Scalp Strategy (v5 — 2026-08-26)

Single source of truth for the scalp path. Supersedes the loose written version that carried a
stale VWAP gate and no stated 4H rule. Every gate below is marked **MEASURED** (backtested on this
repo's data) or **ASSUMED** (carried on judgement, never tested) so it is always obvious which
parts are load-bearing evidence and which are convention.

---

## 1. Timeframe stack

| Timeframe | Job | Is it a signal? |
|---|---|---|
| **4H** | Trend bias + mark 4H supply/demand zones | No — guidance + veto only |
| **1H** | Draw the zone | No |
| **15m** | Refine the zone to tight boundaries | No — **never** a signal timeframe |
| **5m** | 9/20 EMA cross, slope, entry | **Yes — the only trigger** |

A 15m EMA cross is not an entry. It is a real event worth *reporting*, but 15m exists to refine
zones, not to fire trades.

---

## 2. Entry trigger — all four required

1. **Cross** — 9 EMA crosses 20 EMA on the **5m**. Above = long, below = short.
2. **Closed candle** — the confirming 5m candle must be closed, never live/forming.
3. **Slope** — both EMAs sloping in the trade's direction after the cross.
4. **Zone alignment (mandatory)** — the cross must occur *at, or immediately after,* a
   reaction/retest at the 15m-refined zone. No zone, no trade, regardless of how clean the cross
   looks. If price has already travelled away from the zone by the time the candle closes, it is a
   **missed signal, not a chase** — wait for a retest.

Entry is at **market price** (this is the scalp/intraday distinction: Intraday uses a limit at the
zone edge; scalp takes the confirmed cross at market).

---

## 3. The two 4H rules — separate, do not conflate

### (a) Direction — blocks counter-trend only  **[MEASURED]**

| 4H reads | Long | Short |
|---|---|---|
| `bullish` | allowed | **blocked** |
| `range` / neutral | allowed | allowed |
| `bearish` | **blocked** | allowed |

4H is **guidance, not a matching requirement**. A neutral 4H does not block either side.

Measured over 17 coins / 3 months at the v4 config (`backtests/2026-08-26-gate-review/`):

```
block counter-trend only   +0.455 avgR   48.1% win   162 trades   ← adopted
hard match required        +0.391 avgR   42.6% win   129 trades   ← previous code
report only, never block   +0.305 avgR   42.0% win   181 trades
```

**Reporting is mandatory, not optional.** The block is silent-by-default only if you let it be.
Every run must state the trend relationship for **both** directions in plain words —
`TREND SUPPORTS` / `TREND NEUTRAL (allowed, not supporting)` / `COUNTER-TREND -> blocked` — and,
when nothing fires, name **which specific gate** suppressed each side. `apiAnalyze.py` prints all
of this automatically as of 2026-08-26. Never report a bare "no signal" while a cross exists and a
gate is quietly vetoing it.

The same rule applies to the cross itself: report the **standing EMA order and when it last
flipped**, not just whether a flip happened on the current candle. On 2026-08-26 a real bearish
cross fired at 13:10 UTC and was still the live state four hours later, while the tooling kept
reporting "cross: none" because it only ever looked at the newest candle. That is a reporting
failure, not a strategy failure, and it is now fixed in the analyzer.

**Known limitation:** 4H structure is derived from *confirmed swing pivots*, so it lags sharp
reversals by construction — it can still read `bullish` hours after price has broken down. When
this tag is the thing blocking a trade, say so explicitly rather than presenting it as current
truth.

### (b) Zone veto — proximity to drawn 4H zones  **[ASSUMED]**

Mark 4H supply/demand before mapping any scalp. A long into overhead 4H supply, or a short into 4H
demand, is capped at **Watch Only** unless the setup is explicitly a reaction trade at that zone.

---

## 4. Shorts — two extra gates  **[MEASURED]**

Longs are unaffected by both. On top of the 4H counter-trend rule:

1. **1D structure** must read `bearish` or `range`/neutral. (Separate check, separate timeframe.)
2. **5m micro-structure break** — price breaks the prior 5-candle swing low, confirming at the signal.

Evidence: adding these turned shorts from a net loser (−0.032R avg) into a net winner (+0.140R
avg) with no cost to longs. Keep both.

---

## 5. What is NOT a gate

These are **reported as context** and must never veto an otherwise valid setup:

- **Session VWAP** — removed as a confirmation gate 2026-08-25. Keeping it cost real money:
  VWAP-on measured **+0.247 avgR** vs **+0.391** with it off, same config. Report the value; never
  trade off it.
- **Directional efficiency** — downgraded 2026-07-31. Gated bars averaged −0.123R vs +0.033R
  ungated; the filter was selecting *against* the setups the framework exists to take.
- **FVG presence** — a zone-quality signal worth mentioning (higher conviction when present), but it
  does not affect entry, sizing, R:R, or which zones are tradeable.

Do not restore any of these as hard gates without a fresh backtest showing positive expectancy.

---

## 6. Stops, targets, R:R

- **SL** — beyond the zone's *exit* line (the far edge, not the entry edge), buffered by ~50% of the
  4H ATR (`scalpScreen.mjs` reports 4H ATR% — use it, don't re-derive by hand).
- **Zones too close together?** If the nearest zone edge sits so close that a normal wick clears it,
  it is not a real invalidation point — skip to the **next real structural level**. If that pushes
  R:R below floor, the trade does not qualify: **reduce size or skip it. Never shrink the stop to
  make the math work.**
- **TP** — prior peak/swing before the move, or the nearest opposing 15m zone, whichever is *closer*.
- **TP zone validity** — every TP sits at the **near edge** of its zone, never inside it, never past
  its far edge. TP1 has no precondition. TP2+ only count as real targets once the zone before them
  is confirmed broken (a close through, holding) — until then they are stretch targets and must not
  be used for the R:R floor check.
- **R:R floor** — 1:1.5 minimum, 1:2 preferred.

### Managing a trade whose TP1 R:R is thin

| TP1 R:R | Action |
|---|---|
| < 1:1 | Don't partial — it locks in a loss-sized win. Question the entry; usually the stop is too wide or the target too close. |
| 1:1 – 2:1 | Scale out 50–75% at TP1, move remainder to **breakeven**. Converts a mediocre trade into a guaranteed non-loss with a free runner. |
| ≥ 2:1 | No urgency. Either let it run full size, or move to breakeven once 1R+ in profit. |

---

## 7. Time stop  **[MEASURED]**

At **6 hours** held: if the trade is at **−0.3R or worse**, tighten the stop to breakeven.

Do **not** use the "must be +0.3R favourable by 6h" variant — tested at −0.132R avg / 15.4% win, a
severe regression, because it cuts off winners that simply hadn't resolved yet.

---

## 8. Risk — the part that actually decides outcomes

- **0.5% of available balance per scalp** (Intraday: 1%).
- Reduced-size tier: **0.25%** (half) when R:R is genuine but sub-floor and every other gate passes.
- **Max daily loss 3%.**
- **Max 1–2 open trades.**
- **Stop after 2 consecutive losses.**

> Research consensus is that position sizing and risk control determine long-run outcome more than
> entry signals — one study found systematic sizing rules gave a **47% higher 3-year survival rate**
> than sizing by feel, while most traders spend ~90% of effort on entries and <10% on sizing. This
> section is short, but it is the highest-leverage part of the document.

---

## 9. Rejected — do not re-add without new evidence

- **Session filter** (block shorts outside 06:00–17:00 UTC, half-size evenings) — tested 2026-08-01,
  cost ~6R over the test period with no offsetting benefit.
- **VWAP / directional-efficiency hard gates** — see §5.
- **15m as a signal timeframe** — see §1.

---

## 10. Honest caveats

- **The trigger is a lagging crossover.** Published work on MA crossovers finds raw 9/21-style
  systems run ~60–65% losers and roughly a 1.0 profit factor, because in ranging markets the two
  lines whip around each other. The 9/20 pair is a 2.2× ratio, below the ~3× commonly cited for
  suppressing whipsaw. **The gates and the zone read are doing the work here, not the cross.**
- **Sample size is modest.** The numbers in §3 come from 129–181 trades over one 3-month window on
  17 coins. Four variants were compared and the best selected, so some of the margin may be
  selection effect. Treat +0.455 avgR as directional evidence, not a promise.
- **Costs matter.** All figures are net of 0.14%/side. An earlier ungated baseline measured +0.033R
  — inside noise and fully consumed by fees. Small edges do not survive contact with slippage.
- **Base rate.** Across markets, consistent retail profitability runs roughly 3–15% depending on
  study and instrument. A system that says "no trade" most of the day is behaving correctly.

---

## 11. Execution flow (per coin)

1. `python3 scripts/apiAnalyze.py SYMBOL` — **live read, every time**, before any opinion is formed.
   Never analyse from a previous reading or a cached ledger entry.
2. `node scripts/scalpScreen.mjs SYMBOL` — 4H ATR% for the stop buffer + context values.
3. TradingView: 4H structure & zones → 1H zone → 15m refine → 5m EMAs. One persistent tab; switch
   symbols via the symbol-search box, **never** a URL nav with a new `symbol=` param.
4. News/catalyst check (the API has no news feed).
5. Apply §2–§6. If a gate blocks the trade, **name the gate out loud** — never report "no signal"
   when a cross exists and something else is vetoing it.
6. Ledger → `node scripts/buildTradeMap.mjs` → paste Pine → verify against the ledger.
