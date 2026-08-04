#!/usr/bin/env python3
"""Sequential signal-funnel audit for the pasted scalp strategy."""

import gzip
import json
from collections import Counter
from pathlib import Path

from strategyBacktest import (Candle, INTERVAL_MS, SeriesLookup, StructureLookup,
                              aggregate, atr, choose_rr, daily_vwap, ema, ms,
                              refined_zones, TEST_END, TEST_START)


def audit(path: Path) -> Counter:
    rows = json.load(gzip.open(path, "rt", encoding="utf-8"))
    candles = [Candle(**row) for row in rows]
    frames = {"5": candles}
    for interval in ("15", "60", "240", "D"):
        frames[interval] = aggregate(candles, interval)
    e9, e20 = ema([c.c for c in candles], 9), ema([c.c for c in candles], 20)
    vwaps = daily_vwap(candles)
    structure = StructureLookup(frames["240"], "240")
    atr_lookup = SeriesLookup(frames["240"], "240", atr(frames["240"]))
    zones = refined_zones(frames["60"], "60", frames["15"], "15")
    zones.sort(key=lambda z: z.known_t)
    active, cursor = [], 0
    counts = Counter()

    for i, candle in enumerate(candles):
        if candle.t > ms(TEST_END):
            break
        while cursor < len(zones) and zones[cursor].known_t <= candle.t:
            active.append(zones[cursor])
            cursor += 1
        for zone in active:
            if zone.invalidated:
                continue
            if zone.kind == "demand" and candle.c < zone.low:
                zone.invalidated = True
            elif zone.kind == "supply" and candle.c > zone.high:
                zone.invalidated = True
        if candle.t < ms(TEST_START) or i < 20 or None in (e9[i], e20[i], e9[i - 1], e20[i - 1]):
            continue
        bull = e9[i - 1] <= e20[i - 1] and e9[i] > e20[i] \
            and e9[i] > e9[i - 1] and e20[i] > e20[i - 1]
        bear = e9[i - 1] >= e20[i - 1] and e9[i] < e20[i] \
            and e9[i] < e9[i - 1] and e20[i] < e20[i - 1]
        if not (bull or bear):
            continue
        counts["5m_cross+same_direction_slopes"] += 1
        direction, kind = ("long", "demand") if bull else ("short", "supply")
        if (direction == "long" and candle.c <= vwaps[i]) or (direction == "short" and candle.c >= vwaps[i]):
            continue
        counts["+daily_vwap"] += 1
        if structure.at(candle.t) != ("bullish" if direction == "long" else "bearish"):
            continue
        counts["+4h_trend"] += 1
        candidates = [z for z in active if z.kind == kind and not z.invalidated
                      and (z.proximal <= candle.c if direction == "long" else z.proximal >= candle.c)]
        if not candidates:
            continue
        counts["+nearest_refined_zone"] += 1
        zone = min(candidates, key=lambda z: (abs(candle.c - z.proximal), -z.known_t))
        current_atr = atr_lookup.at(candle.t)
        if not current_atr:
            continue
        stop = zone.low - 0.50 * current_atr if direction == "long" else zone.high + 0.50 * current_atr
        if direction == "long" and stop >= candle.c or direction == "short" and stop <= candle.c:
            continue
        counts["+valid_4h_atr_stop"] += 1
        opposite = [z for z in active if z.kind != kind and not z.invalidated]
        rr, _ = choose_rr(candle.c, stop, direction, opposite)
        if rr is not None:
            counts["+next_zone_allows_1.5R_or_2R"] += 1
    return counts


if __name__ == "__main__":
    total = Counter()
    data_dir = Path("backtests/2026-08-01-strategy-rerun/data")
    for source in sorted(data_dir.glob("*_5m.json.gz")):
        total.update(audit(source))
    result = json.loads(Path("backtests/2026-08-01-strategy-rerun/backtest_results.json").read_text())
    scalp = next(x for x in result["portfolio"] if x["strategy"] == "Scalp")
    total["executed_after_position_and_risk_limits"] = scalp["trades"]
    print("TOTAL", dict(total))
    Path("backtests/2026-08-01-strategy-rerun/scalp_funnel.json").write_text(
        json.dumps(dict(total), indent=2) + "\n", encoding="utf-8")
