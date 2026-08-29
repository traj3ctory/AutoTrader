#!/usr/bin/env python3
"""A/B backtest: v2 scalp rules (already validated, +0.541R avg/trade, 75%
win, PF 3.25 over the 3-month test) vs v3 (adds: mandatory zone alignment
[already true in v2 - see strategyBacktest.py run_scalp], an asymmetric
1D-structure gate for shorts only, a 5m micro-structure-break requirement
for shorts only, a UTC session filter that blocks shorts 18h/day and
half-sizes the evening window, and a 6h/0.3R time-stop that moves the stop
to breakeven if a trade hasn't moved in its favor).

Reuses the exact cached 5m data and helper functions from strategyBacktest.py
so this is a true apples-to-apples comparison on the same candles, same
zones, same EMA/VWAP core signal - only the v3-specific deltas are toggled.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import strategyBacktest as sb  # noqa: E402
from dataclasses import asdict
import gzip, json, statistics
from typing import Optional, Any

ROOT = Path(__file__).parent.parent
DATA_DIR = ROOT / "backtests" / "2026-07-31" / "data"

MICRO_LOOKBACK = 5
TIME_STOP_CANDLES_DEFAULT = 72  # 6h at 5m
TIME_STOP_MIN_R_DEFAULT = 0.3
SESSION_FULL = (6, 17)     # 06:00-17:59 UTC: both directions, full size
SESSION_LONG_ONLY_NIGHT = (0, 5)   # 00:00-05:59 UTC: longs only, full size
SESSION_LONG_ONLY_EVE = (18, 23)   # 18:00-23:59 UTC: longs only, half size


def utc_hour(t_ms: int) -> int:
    import datetime as dt
    return dt.datetime.fromtimestamp(t_ms / 1000, dt.timezone.utc).hour


def session_rule(t_ms: int) -> tuple[bool, bool, float]:
    """Returns (longs_allowed, shorts_allowed, size_mult)."""
    h = utc_hour(t_ms)
    if SESSION_FULL[0] <= h <= SESSION_FULL[1]:
        return True, True, 1.0
    if SESSION_LONG_ONLY_NIGHT[0] <= h <= SESSION_LONG_ONLY_NIGHT[1]:
        return True, False, 1.0
    return True, False, 0.5  # evening window


def micro_break(candles, i: int, direction: str) -> bool:
    if i < MICRO_LOOKBACK + 1:
        return False
    window = candles[i - MICRO_LOOKBACK:i]
    if direction == "short":
        swing_low = min(c.l for c in window)
        return candles[i].l < swing_low
    swing_high = max(c.h for c in window)
    return candles[i].h > swing_high


def run_scalp_v3(symbol: str, frames: dict, cost_pct: float, *, short_gates: bool = False, session_filter: bool = False, time_stop: bool = False, time_stop_candles: int = TIME_STOP_CANDLES_DEFAULT, time_stop_min_r: float = TIME_STOP_MIN_R_DEFAULT) -> list:
    candles = frames["5"]
    closes = [c.c for c in candles]
    e9, e20 = sb.ema(closes, 9), sb.ema(closes, 20)
    vwaps = sb.daily_vwap(candles)
    zones = sb.clone_zones(sb.refined_zones(frames["60"], "60", frames["15"], "15"))
    zones.sort(key=lambda z: z.known_t)
    structure_4h = sb.StructureLookup(frames["240"], "240")
    structure_1d = sb.StructureLookup(frames["D"], "D")
    atr_lookup = sb.SeriesLookup(frames["240"], "240", sb.atr(frames["240"]))
    active = []
    zone_cursor = 0
    trades = []
    position: Optional[dict[str, Any]] = None

    for i, candle in enumerate(candles):
        if candle.t > sb.ms(sb.TEST_END):
            break
        in_test = candle.t >= sb.ms(sb.TEST_START)
        while zone_cursor < len(zones) and zones[zone_cursor].known_t <= candle.t:
            active.append(zones[zone_cursor])
            zone_cursor += 1
        for zone in active:
            if zone.invalidated or zone.consumed:
                continue
            if zone.kind == "demand" and candle.c < zone.low:
                zone.invalidated = True
            elif zone.kind == "supply" and candle.c > zone.high:
                zone.invalidated = True
        if not in_test:
            continue

        if position is not None:
            direction = position["direction"]
            # v3: 6h / 0.3R time-stop -> tighten to breakeven
            if time_stop and not position.get("breakeven_applied") and i - position["entry_index"] >= time_stop_candles:
                risk = abs(position["entry"] - position["orig_stop"])
                unreal = ((candle.c - position["entry"]) if direction == "long"
                          else (position["entry"] - candle.c)) / risk if risk else 0
                if unreal < time_stop_min_r:
                    position["stop"] = position["entry"]
                position["breakeven_applied"] = True

            stop_hit = candle.l <= position["stop"] if direction == "long" else candle.h >= position["stop"]
            target_hit = candle.h >= position["target"] if direction == "long" else candle.l <= position["target"]
            if stop_hit or target_hit:
                if stop_hit:
                    exit_price = position["stop"]
                    gross_r = sb.outcome_from_exit(direction, position["entry"], position["orig_stop"], exit_price)
                    result = "SL" if exit_price != position["entry"] else "BE"
                elif target_hit:
                    exit_price, result, gross_r = position["target"], "TP", position["rr"]
                size_mult = position.get("size_mult", 1.0)
                t = sb.make_trade("Scalp", symbol, direction, position["signal_t"], position["entry_t"],
                                   candle.t + sb.INTERVAL_MS["5"], position["entry"], position["orig_stop"],
                                   position["target"], position["rr"], exit_price, result, gross_r,
                                   0.5 * size_mult, cost_pct, position["zone_tf"], "EMA+zone")
                trades.append(t)
                position = None
            continue

        if i < 20 or e9[i] is None or e20[i] is None or e9[i - 1] is None or e20[i - 1] is None:
            continue
        bull_cross = e9[i - 1] <= e20[i - 1] and e9[i] > e20[i]
        bear_cross = e9[i - 1] >= e20[i - 1] and e9[i] < e20[i]
        bull_slope = e9[i] > e9[i - 1] and e20[i] > e20[i - 1]
        bear_slope = e9[i] < e9[i - 1] and e20[i] < e20[i - 1]
        bias4h = structure_4h.at(candle.t)

        longs_ok, shorts_ok, size_mult = session_rule(candle.t) if session_filter else (True, True, 1.0)

        direction = kind = None
        # 2026-08-26: VWAP confirmation gate REMOVED (it was stale here long after the
        # 2026-08-25 doc correction) and 4H downgraded from hard gate to counter-trend-only.
        # Measured over 17 coins / 3 months: VWAP-on+4H-hard +0.247 avgR, VWAP-off+4H-hard
        # +0.391, VWAP-off+4H-soft +0.455 (48.1% win). VWAP is context for reporting only.
        if bull_cross and bull_slope and bias4h != "bearish" and longs_ok:
            direction, kind = "long", "demand"
        elif bear_cross and bear_slope and bias4h != "bullish" and shorts_ok:
            if short_gates:
                bias1d = structure_1d.at(candle.t)
                if bias1d not in ("bearish", "range"):
                    continue
                if not micro_break(candles, i, "short"):
                    continue
            direction, kind = "short", "supply"
        else:
            continue

        candidates = [z for z in active if z.kind == kind and not z.invalidated and not z.consumed
                      and (z.proximal <= candle.c if direction == "long" else z.proximal >= candle.c)]
        candidates.sort(key=lambda z: (abs(candle.c - z.proximal), -z.known_t))
        if not candidates:
            continue
        zone = candidates[0]
        current_atr = atr_lookup.at(candle.t)
        if not current_atr:
            continue
        entry = candle.c
        stop = zone.low - 0.50 * current_atr if direction == "long" else zone.high + 0.50 * current_atr
        if direction == "long" and stop >= entry or direction == "short" and stop <= entry:
            zone.consumed = True
            continue
        opposite = [z for z in active if z.kind != kind and z.known_t <= candle.t and not z.invalidated]
        rr, target = sb.choose_rr(entry, stop, direction, opposite)
        zone.consumed = True
        if rr is None or target is None:
            continue
        position = {"direction": direction, "signal_t": candle.t, "entry_t": candle.t + sb.INTERVAL_MS["5"],
                    "entry_index": i, "entry": entry, "stop": stop, "orig_stop": stop, "target": target,
                    "rr": rr, "zone_tf": zone.source_tf, "size_mult": size_mult,
                    "breakeven_applied": False}

    if position is not None and candles:
        final = next((c for c in reversed(candles) if c.t <= sb.ms(sb.TEST_END)), candles[-1])
        trades.append(sb.make_trade("Scalp", symbol, position["direction"], position["signal_t"],
                                     position["entry_t"], final.t + sb.INTERVAL_MS["5"], position["entry"],
                                     position["orig_stop"], position["target"], position["rr"], final.c,
                                     "OPEN", 0.0, 0.5, 0.0, position["zone_tf"], "EMA+zone"))
    return trades


def load_frames(symbol: str) -> dict:
    cache = DATA_DIR / f"{symbol}_5m.json.gz"
    with gzip.open(cache, "rt", encoding="utf-8") as h:
        rows = json.load(h)
    five = [sb.Candle(**r) for r in rows]
    frames = {"5": five}
    for interval in ("15", "60", "240", "D"):
        frames[interval] = sb.aggregate(five, interval)
    return frames


def stats(trades) -> tuple:
    if not trades:
        return (0, 0.0, 0.0, 0.0, 0.0)
    rs = [t.net_r for t in trades]
    n = len(rs)
    wins = sum(1 for r in rs if r > 0)
    return (n, sum(rs) / n, 100 * wins / n, sum(rs), max(0, -min(rs, default=0)))


VARIANTS = {
    "A_baseline":     dict(short_gates=False, session_filter=False, time_stop=False),
    "B_short_gates":  dict(short_gates=True,  session_filter=False, time_stop=False),
    "C_session":      dict(short_gates=False, session_filter=True,  time_stop=False),
    "D_timestop":     dict(short_gates=False, session_filter=False, time_stop=True),
    "E_full_v3":      dict(short_gates=True,  session_filter=True,  time_stop=True),
    # Time-stop tuning: looser thresholds/windows to find one that keeps risk
    # control without cutting off winners that just haven't resolved yet.
    "D1_6h_0.0R":     dict(short_gates=False, session_filter=False, time_stop=True, time_stop_candles=72,  time_stop_min_r=0.0),
    "D2_6h_-0.3R":    dict(short_gates=False, session_filter=False, time_stop=True, time_stop_candles=72,  time_stop_min_r=-0.3),
    "D3_12h_0.3R":    dict(short_gates=False, session_filter=False, time_stop=True, time_stop_candles=144, time_stop_min_r=0.3),
    "D4_12h_0.0R":    dict(short_gates=False, session_filter=False, time_stop=True, time_stop_candles=144, time_stop_min_r=0.0),
    "D5_12h_-0.3R":   dict(short_gates=False, session_filter=False, time_stop=True, time_stop_candles=144, time_stop_min_r=-0.3),
    "D6_18h_-0.3R":   dict(short_gates=False, session_filter=False, time_stop=True, time_stop_candles=216, time_stop_min_r=-0.3),
    # Best-guess combo: short gates (proven) + a tuned time-stop, no session filter.
    "F_gates+D5":     dict(short_gates=True,  session_filter=False, time_stop=True, time_stop_candles=144, time_stop_min_r=-0.3),
    "G_gates+D2":     dict(short_gates=True,  session_filter=False, time_stop=True, time_stop_candles=72,  time_stop_min_r=-0.3),
}

def main():
    symbols = sb.unique_symbols()
    pooled = {k: [] for k in VARIANTS}
    for symbol in symbols:
        cache = DATA_DIR / f"{symbol}_5m.json.gz"
        if not cache.exists():
            continue
        frames = load_frames(symbol)
        for key, flags in VARIANTS.items():
            pooled[key] += run_scalp_v3(symbol, frames, cost_pct=0.14, **flags)

    print(f"{'VARIANT':16} {'n':>5} {'win%':>6} {'avgR':>8} {'totalR':>8}   {'longs n/avgR':>14}   {'shorts n/avgR':>15}")
    print("-" * 96)
    for key in VARIANTS:
        ts = pooled[key]
        n, a, w, s, _ = stats(ts)
        longs = [t for t in ts if t.direction == "long"]
        shorts = [t for t in ts if t.direction == "short"]
        nl, al, wl, sl_, _ = stats(longs)
        ns, as_, ws, ss, _ = stats(shorts)
        print(f"{key:16} {n:>5} {w:>5.1f}% {a:>8.3f} {s:>8.2f}   "
              f"n={nl:<3} avgR={al:>6.3f}   n={ns:<3} avgR={as_:>6.3f}")

    print()
    print("A = current v2 baseline (no new rules)")
    print("B = + short-side gates only (1D structure filter + 5m micro-break, shorts only)")
    print("C = + session filter only (shorts blocked outside 06-17 UTC, half-size 18-23 UTC)")
    print("D = + 6h/0.3R breakeven time-stop only (both directions)")
    print("E = full v3 (all three combined)")


if __name__ == "__main__":
    main()
