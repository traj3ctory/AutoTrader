#!/usr/bin/env python3
"""Live, API-first analysis - the primary decision engine per the 2026-08-03
Source Of Truth change (Bybit API first, TradingView for news + final
display only). Reuses the EXACT zone-detection, structure, and signal
functions from strategyBacktest.py (imported directly, not reimplemented) so
a live read can never silently drift from what was actually backtested.

Prints: 4H trend, the nearest 1H->15m refined zone to current price, whether
price is currently reacting at it, the 5m EMA9/20 signal (cross/slope) at
that zone, VWAP alignment, and - if every condition in the Scalp Entry Rule
is met - a computed entry/SL/TP/R:R ready to drop into SETUP_LEDGER.json.

Usage: python3 scripts/apiAnalyze.py XRPUSDT [--trade-type scalp|intraday]
"""
import sys
import time
import urllib.parse
import urllib.request
import json
from pathlib import Path
from dataclasses import asdict

sys.path.insert(0, str(Path(__file__).parent))
import strategyBacktest as sb  # noqa: E402

MICRO_LOOKBACK = 5


def fetch_live(symbol: str, interval: str, limit: int = 300):
    query = urllib.parse.urlencode({
        "category": "linear", "symbol": symbol, "interval": interval, "limit": limit,
    })
    with urllib.request.urlopen(f"https://api.bybit.com/v5/market/kline?{query}", timeout=20) as r:
        data = json.load(r)
    if data.get("retCode") != 0:
        raise RuntimeError(f"{symbol} {interval}: {data.get('retMsg')}")
    rows = sorted(data["result"]["list"], key=lambda x: int(x[0]))
    return [sb.Candle(t=int(x[0]), o=float(x[1]), h=float(x[2]), l=float(x[3]),
                       c=float(x[4]), v=float(x[5])) for x in rows]


def micro_break(candles, i, direction):
    if i < MICRO_LOOKBACK + 1:
        return False
    window = candles[i - MICRO_LOOKBACK:i]
    if direction == "short":
        return candles[i].l < min(c.l for c in window)
    return candles[i].h > max(c.h for c in window)


def analyze_scalp(symbol: str):
    c5 = fetch_live(symbol, "5", 300)
    c15 = fetch_live(symbol, "15", 200)
    c60 = fetch_live(symbol, "60", 200)
    c240 = fetch_live(symbol, "240", 100)
    cD = fetch_live(symbol, "D", 60)

    zones = sb.clone_zones(sb.refined_zones(c60, "60", c15, "15"))
    zones.sort(key=lambda z: z.known_t)
    for z in zones:
        if z.kind == "demand" and c5[-1].c < z.low:
            z.invalidated = True
        elif z.kind == "supply" and c5[-1].c > z.high:
            z.invalidated = True

    structure_4h = sb.StructureLookup(c240, "240")
    structure_1d = sb.StructureLookup(cD, "D")
    atr_lookup = sb.SeriesLookup(c240, "240", sb.atr(c240))
    closes = [c.c for c in c5]
    e9, e20 = sb.ema(closes, 9), sb.ema(closes, 20)
    vwaps = sb.daily_vwap(c5)
    i = len(c5) - 1
    price = c5[i].c
    now_t = c5[i].t

    bias4h = structure_4h.at(now_t)
    bias1d = structure_1d.at(now_t)
    print(f"\n===== {symbol} — LIVE API ANALYSIS (Scalp) =====")
    print(f"Price: {price}")
    print(f"4H structure: {bias4h}   |   1D structure: {bias1d}")
    print(f"Session VWAP (5m, resets 00:00 UTC): {vwaps[i]:.6f}  ({'ABOVE' if price > vwaps[i] else 'BELOW'})")

    active_demand = [z for z in zones if z.kind == "demand" and not z.invalidated and not z.consumed]
    active_supply = [z for z in zones if z.kind == "supply" and not z.invalidated and not z.consumed]
    near_demand = max(active_demand, key=lambda z: z.high, default=None)
    near_supply = min(active_supply, key=lambda z: z.low, default=None)
    print(f"Nearest live demand zone: {f'{near_demand.low:.6f}-{near_demand.high:.6f}' if near_demand else 'none'}")
    print(f"Nearest live supply zone: {f'{near_supply.low:.6f}-{near_supply.high:.6f}' if near_supply else 'none'}")

    if e9[i] is None or e20[i] is None or e9[i - 3] is None or e20[i - 3] is None:
        print("Not enough 5m data for EMA cross yet.")
        return

    bull_cross = e9[i - 1] <= e20[i - 1] and e9[i] > e20[i]
    bear_cross = e9[i - 1] >= e20[i - 1] and e9[i] < e20[i]
    bull_slope = e9[i] > e9[i - 3]
    bear_slope = e9[i] < e9[i - 3]
    print(f"5m EMA 9/20 cross: {'BULLISH' if bull_cross else 'BEARISH' if bear_cross else 'none'}   "
          f"slope: {'UP' if bull_slope else 'DOWN' if bear_slope else 'FLAT'}")

    reacting_at_demand = near_demand and near_demand.low <= price <= near_demand.high * 1.004
    reacting_at_supply = near_supply and near_supply.high >= price >= near_supply.low * 0.996

    verdict = "WATCH ONLY — no valid signal right now"
    if bull_cross and bull_slope and price > vwaps[i] and bias4h == "bullish" and reacting_at_demand:
        risk = price - (near_demand.low - 0.5 * atr_lookup.at(now_t))
        opposite = [z for z in zones if z.kind == "supply" and not z.invalidated]
        rr, target = sb.choose_rr(price, price - risk, "long", opposite)
        if rr:
            verdict = f"VALID LONG — entry {price:.6f}, SL {price-risk:.6f}, TP {target:.6f}, R:R {rr}"
        else:
            verdict = "Zone/cross/VWAP all align for LONG but no R:R-clearing target found — no trade"
    elif bear_cross and bear_slope and price < vwaps[i] and bias4h == "bearish" and reacting_at_supply:
        if bias1d not in ("bearish", "range") or not micro_break(c5, i, "short"):
            verdict = "Bearish cross+VWAP+zone align, but 1D structure or 5m micro-break gate fails — no short"
        else:
            risk = (near_supply.high + 0.5 * atr_lookup.at(now_t)) - price
            opposite = [z for z in zones if z.kind == "demand" and not z.invalidated]
            rr, target = sb.choose_rr(price, price + risk, "short", opposite)
            if rr:
                verdict = f"VALID SHORT — entry {price:.6f}, SL {price+risk:.6f}, TP {target:.6f}, R:R {rr}"
            else:
                verdict = "Zone/cross/VWAP/1D/micro-break all align for SHORT but no R:R-clearing target — no trade"
    print(f"\nVERDICT: {verdict}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 scripts/apiAnalyze.py SYMBOL")
        sys.exit(1)
    analyze_scalp(sys.argv[1])
