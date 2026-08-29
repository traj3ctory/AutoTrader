#!/usr/bin/env python3
"""Isolate the two gates under review:
   - VWAP confirmation gate (doc says removed 2026-08-25, still live in code)
   - 4H structure direction gate (hard-coded in code, NOT in the user's written strategy)

Everything else held constant at the validated v4 config (6h/-0.3R time-stop).
"""
import sys
from pathlib import Path
from typing import Any, Optional

ROOT = Path(__file__).resolve().parents[0]
REPO = Path("/Users/charmz/Documents/PERSONAL/AUTOTRADER")
sys.path.insert(0, str(REPO / "scripts"))

import strategyBacktest as sb  # noqa: E402
import scalpBacktestV3 as v3  # noqa: E402


def run(symbol, frames, cost_pct, *, vwap_gate: bool, bias4h_mode: str,
        short_gates: bool = True, time_stop_candles: int = 72, time_stop_min_r: float = -0.3):
    candles = frames["5"]
    closes = [c.c for c in candles]
    e9, e20 = sb.ema(closes, 9), sb.ema(closes, 20)
    vwaps = sb.daily_vwap(candles)
    zones = sb.clone_zones(sb.refined_zones(frames["60"], "60", frames["15"], "15"))
    zones.sort(key=lambda z: z.known_t)
    structure_4h = sb.StructureLookup(frames["240"], "240")
    structure_1d = sb.StructureLookup(frames["D"], "D")
    atr_lookup = sb.SeriesLookup(frames["240"], "240", sb.atr(frames["240"]))
    active, zone_cursor, trades = [], 0, []
    position: Optional[dict[str, Any]] = None

    for i, candle in enumerate(candles):
        if candle.t > sb.ms(sb.TEST_END):
            break
        in_test = candle.t >= sb.ms(sb.TEST_START)
        while zone_cursor < len(zones) and zones[zone_cursor].known_t <= candle.t:
            active.append(zones[zone_cursor]); zone_cursor += 1
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
            if not position.get("breakeven_applied") and i - position["entry_index"] >= time_stop_candles:
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
                else:
                    exit_price, result, gross_r = position["target"], "TP", position["rr"]
                trades.append(sb.make_trade("Scalp", symbol, direction, position["signal_t"], position["entry_t"],
                                            candle.t + sb.INTERVAL_MS["5"], position["entry"], position["orig_stop"],
                                            position["target"], position["rr"], exit_price, result, gross_r,
                                            0.5, cost_pct, position["zone_tf"], "test"))
                position = None
            continue

        if i < 20 or e9[i] is None or e20[i] is None or e9[i-1] is None or e20[i-1] is None:
            continue
        bull_cross = e9[i-1] <= e20[i-1] and e9[i] > e20[i]
        bear_cross = e9[i-1] >= e20[i-1] and e9[i] < e20[i]
        bull_slope = e9[i] > e9[i-1] and e20[i] > e20[i-1]
        bear_slope = e9[i] < e9[i-1] and e20[i] < e20[i-1]
        bias4h = structure_4h.at(candle.t)

        # --- the two gates under test ---
        vwap_long_ok = (candle.c > vwaps[i]) if vwap_gate else True
        vwap_short_ok = (candle.c < vwaps[i]) if vwap_gate else True
        if bias4h_mode == "hard":
            b4_long_ok, b4_short_ok = bias4h == "bullish", bias4h == "bearish"
        elif bias4h_mode == "soft":   # block only outright counter-trend
            b4_long_ok, b4_short_ok = bias4h != "bearish", bias4h != "bullish"
        else:                          # "off" -> bias is guidance only
            b4_long_ok = b4_short_ok = True

        direction = kind = None
        if bull_cross and bull_slope and vwap_long_ok and b4_long_ok:
            direction, kind = "long", "demand"
        elif bear_cross and bear_slope and vwap_short_ok and b4_short_ok:
            if short_gates:
                if structure_1d.at(candle.t) not in ("bearish", "range"):
                    continue
                if not v3.micro_break(candles, i, "short"):
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
        stop = zone.low - 0.50*current_atr if direction == "long" else zone.high + 0.50*current_atr
        if (direction == "long" and stop >= entry) or (direction == "short" and stop <= entry):
            zone.consumed = True; continue
        opposite = [z for z in active if z.kind != kind and z.known_t <= candle.t and not z.invalidated]
        rr, target = sb.choose_rr(entry, stop, direction, opposite)
        zone.consumed = True
        if rr is None or target is None:
            continue
        position = {"direction": direction, "signal_t": candle.t, "entry_t": candle.t + sb.INTERVAL_MS["5"],
                    "entry_index": i, "entry": entry, "stop": stop, "orig_stop": stop, "target": target,
                    "rr": rr, "zone_tf": zone.source_tf, "breakeven_applied": False}
    return trades


VARIANTS = {
    "1_current_code   (VWAP on,  4H hard)": dict(vwap_gate=True,  bias4h_mode="hard"),
    "2_doc_today      (VWAP off, 4H hard)": dict(vwap_gate=False, bias4h_mode="hard"),
    "3_YOUR_PROPOSAL  (VWAP off, 4H off )": dict(vwap_gate=False, bias4h_mode="off"),
    "4_middle         (VWAP off, 4H soft)": dict(vwap_gate=False, bias4h_mode="soft"),
}


def main():
    symbols = sb.unique_symbols()
    pooled = {k: [] for k in VARIANTS}
    used = 0
    for symbol in symbols:
        cache = v3.DATA_DIR / f"{symbol}_5m.json.gz"
        if not cache.exists():
            continue
        used += 1
        frames = v3.load_frames(symbol)
        for key, flags in VARIANTS.items():
            pooled[key] += run(symbol, frames, cost_pct=0.14, **flags)

    print(f"Symbols: {used}   Window: {sb.TEST_START.date()} -> {sb.TEST_END.date()}   cost 0.14%/side\n")
    print(f"{'VARIANT':38} {'n':>4} {'win%':>6} {'avgR':>7} {'totalR':>8}  {'longs':>16}  {'shorts':>16}")
    print("-" * 108)
    for key in VARIANTS:
        ts = pooled[key]
        n, a, w, s, _ = v3.stats(ts)
        L = [t for t in ts if t.direction == "long"]
        S = [t for t in ts if t.direction == "short"]
        nl, al, *_ = v3.stats(L)
        ns, as_, *_ = v3.stats(S)
        print(f"{key:38} {n:>4} {w:>5.1f}% {a:>7.3f} {s:>8.2f}  n={nl:<3} avgR={al:>6.3f}  n={ns:<3} avgR={as_:>6.3f}")


if __name__ == "__main__":
    main()
