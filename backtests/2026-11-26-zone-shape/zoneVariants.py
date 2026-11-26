"""Test-only zone builders; the live engine is not changed."""
import bisect
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import strategyBacktest as sb  # noqa: E402

LOOKBACK = 3
CURRENT_BUILDER = sb.source_zones


def _breaks(candles, interval):
    """Yields (candle index, zone kind, broken pivot) for every close beyond the latest confirmed swing."""
    ps = sb.pivots(candles, interval)
    highs = [p for p in ps if p.kind == "high"]
    lows = [p for p in ps if p.kind == "low"]
    high_known = [p.known_t for p in highs]
    low_known = [p.known_t for p in lows]
    for j, candle in enumerate(candles):
        hi = bisect.bisect_right(high_known, candle.t) - 1
        lo = bisect.bisect_right(low_known, candle.t) - 1
        if hi >= 0 and candle.c > highs[hi].price:
            yield j, "demand", highs[hi]
        elif lo >= 0 and candle.c < lows[lo].price:
            yield j, "supply", lows[lo]


def _opposite_colour(candle, kind):
    return candle.c < candle.o if kind == "demand" else candle.c > candle.o


def _zone(*, candles, interval, kind, source_index, break_index, low, high):
    source = candles[source_index]
    return sb.Zone(
        id=f"{interval}-{kind}-{source_index}-{source.t}", kind=kind, source_tf=interval,
        t=source.t, known_t=candles[break_index].t + sb.INTERVAL_MS[interval], low=low, high=high,
        pivot_price=low if kind == "demand" else high,
        has_fvg=sb.leg_has_fvg(candles, source_index, break_index, kind))


def same_candle_wick_body(candles, interval):
    """Current candle choice; supply is body to high, demand is low to body."""
    zones, seen = [], set()
    for j, kind, _ in _breaks(candles, interval):
        index = next((i for i in range(j - 1, max(-1, j - LOOKBACK - 1), -1) if _opposite_colour(candles[i], kind)), None)
        if index is None or (kind, index) in seen:
            continue
        seen.add((kind, index))
        source = candles[index]
        low, high = (source.l, source.o) if kind == "demand" else (source.o, source.h)
        if high > low:
            zones.append(_zone(candles=candles, interval=interval, kind=kind, source_index=index, break_index=j, low=low, high=high))
    return zones


def _extreme_zones(candles, interval, *, use_opposite_colour):
    """Anchors each first break of a swing at the extreme reached since the previous first break."""
    zones, seen_pivots, seen = [], set(), set()
    previous = None
    for j, kind, pivot in _breaks(candles, interval):
        if (kind, pivot.t) in seen_pivots:
            continue
        seen_pivots.add((kind, pivot.t))
        start, previous = previous, j
        if start is None:
            continue
        window = range(start, j + 1)
        extreme = (min(window, key=lambda i: candles[i].l) if kind == "demand"
                   else max(window, key=lambda i: candles[i].h))
        index = extreme
        if use_opposite_colour:
            index = next((i for i in range(extreme, max(-1, extreme - LOOKBACK - 1), -1)
                          if _opposite_colour(candles[i], kind)), None)
        if index is None or (kind, index) in seen:
            continue
        seen.add((kind, index))
        source = candles[index]
        if kind == "demand":
            low = candles[extreme].l
            high = source.o if use_opposite_colour else max(source.o, source.c)
        else:
            high = candles[extreme].h
            low = source.o if use_opposite_colour else min(source.o, source.c)
        if high > low:
            zones.append(_zone(candles=candles, interval=interval, kind=kind, source_index=index, break_index=j, low=low, high=high))
    return zones


def extreme_candle(candles, interval):
    """The candle at the top or bottom of the move: its wick plus body."""
    return _extreme_zones(candles, interval, use_opposite_colour=False)


def extreme_opposite_colour(candles, interval):
    """Last opposite-colour candle at the top or bottom: its body edge out to the extreme wick."""
    return _extreme_zones(candles, interval, use_opposite_colour=True)


CURRENT_REFINER = sb.refined_zones
HIGHER_TF = "240"


def split_by_family(high_candles, high_tf, low_candles, low_tf):
    """4H zone families use the top-of-move candle; 1H families keep the current rule."""
    sb.source_zones = extreme_candle if high_tf == HIGHER_TF else CURRENT_BUILDER
    return CURRENT_REFINER(high_candles, high_tf, low_candles, low_tf)


def use(name):
    """Points both engines at one variant."""
    sb.refined_zones = split_by_family if name == SPLIT else CURRENT_REFINER
    sb.source_zones = BUILDERS.get(name, CURRENT_BUILDER)


SPLIT = "5 candidate: 4H uses 3, 1H current"


BUILDERS = {
    "1 current": CURRENT_BUILDER,
    "2 same candle, wick+body": same_candle_wick_body,
    "3 top/bottom candle, wick+body": extreme_candle,
    "4 last green/red at top, to wick": extreme_opposite_colour,
}
NAMES = [*BUILDERS, SPLIT]
