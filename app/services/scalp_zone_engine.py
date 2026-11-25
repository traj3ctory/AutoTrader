"""Scalp Zone engine: 5m rejection or engulfing at a 15m zone, replayed over cached candles."""
import apiAnalyze as live
import strategyBacktest as sb
from services.config import SL_ATR_BUFFER_MULT

ZONE_TOUCH_WINDOW = 4
WARMUP_CANDLES = 20


def _update_zones(active, candle, i):
    for zone in active:
        if zone.invalidated or zone.consumed:
            continue
        if zone.kind == "demand" and candle.c < zone.low:
            zone.invalidated = True
        elif zone.kind == "supply" and candle.c > zone.high:
            zone.invalidated = True
        elif sb.overlaps(candle, zone):
            if zone.touch_index is None:
                zone.touch_index = i
        if zone.touch_index is not None and i - zone.touch_index > ZONE_TOUCH_WINDOW:
            zone.consumed = True


def _close_position(symbol, position, candle, i, cost_pct):
    """Returns the closed trade when the stop or target is hit on this candle, else None."""
    direction = position["direction"]
    if not position.get("breakeven_applied") and i - position["entry_index"] >= live.TIME_STOP_CANDLES:
        risk = abs(position["entry"] - position["orig_stop"])
        unreal = ((candle.c - position["entry"]) if direction == "long" else (position["entry"] - candle.c)) / risk if risk else 0.0
        if unreal < live.TIME_STOP_MIN_R:
            position["stop"] = position["entry"]
        position["breakeven_applied"] = True
    stop_hit = candle.l <= position["stop"] if direction == "long" else candle.h >= position["stop"]
    target_hit = candle.h >= position["target"] if direction == "long" else candle.l <= position["target"]
    if not (stop_hit or target_hit):
        return None
    if stop_hit:
        exit_price = position["stop"]
        gross_r = sb.outcome_from_exit(direction, position["entry"], position["orig_stop"], exit_price)
        result = "SL" if exit_price != position["entry"] else "BE"
    else:
        exit_price, result, gross_r = position["target"], "TP", position["rr"]
    return sb.make_trade(
        "ScalpZone", symbol, direction, position["signal_t"], position["entry_t"],
        candle.t + sb.INTERVAL_MS["5"], position["entry"], position["orig_stop"],
        position["target"], position["rr"], exit_price, result, gross_r,
        0.5, cost_pct, position["zone_tf"], "5m-zone-rej",
    )


def _find_entry(candles, i, active, bias4h, bias1d, current_atr):
    candle = candles[i]
    prev = candles[i - 1]
    for direction, kind in (("long", "demand"), ("short", "supply")):
        if direction == "long" and bias4h == "bearish":
            continue
        if direction == "short" and (bias4h == "bullish" or bias1d not in ("bearish", "range")):
            continue
        cands = [
            z for z in active
            if z.kind == kind and not z.invalidated and not z.consumed
            and z.touch_index is not None and 0 <= i - z.touch_index <= ZONE_TOUCH_WINDOW
        ]
        picked = next(
            (z for z in cands if sb.rejection(candle, z, direction) or sb.engulfing(prev, candle, z, direction)),
            None,
        )
        if picked is None:
            continue
        entry = candle.c
        stop = picked.low - SL_ATR_BUFFER_MULT * current_atr if direction == "long" else picked.high + SL_ATR_BUFFER_MULT * current_atr
        if (direction == "long" and stop >= entry) or (direction == "short" and stop <= entry):
            picked.consumed = True
            continue
        opposite = [z for z in active if z.kind != kind and z.known_t <= candle.t and not z.invalidated]
        rr, target = sb.choose_rr(entry, stop, direction, opposite)
        picked.consumed = True
        if rr is None or target is None:
            continue
        return {
            "direction": direction,
            "signal_t": candle.t,
            "entry_t": candle.t + sb.INTERVAL_MS["5"],
            "entry_index": i,
            "entry": entry,
            "stop": stop,
            "orig_stop": stop,
            "target": target,
            "rr": rr,
            "zone_tf": picked.source_tf,
            "breakeven_applied": False,
        }
    return None


def run_scalp_zone(symbol, frames, cost_pct, state_out=None):
    candles = frames["5"]
    zones = sb.clone_zones(sb.refined_zones(frames["60"], "60", frames["15"], "15"))
    zones.sort(key=lambda z: z.known_t)
    structure_4h = sb.StructureLookup(frames["240"], "240")
    structure_1d = sb.StructureLookup(frames["D"], "D")
    atr_lookup = sb.SeriesLookup(frames["240"], "240", sb.atr(frames["240"]))

    active = []
    zone_cursor = 0
    trades = []
    position = None

    for i, candle in enumerate(candles):
        if candle.t > sb.ms(sb.TEST_END):
            break
        in_test = candle.t >= sb.ms(sb.TEST_START)
        while zone_cursor < len(zones) and zones[zone_cursor].known_t <= candle.t:
            active.append(zones[zone_cursor])
            zone_cursor += 1
        _update_zones(active, candle, i)

        if not in_test:
            continue

        if position is not None:
            trade = _close_position(symbol, position, candle, i, cost_pct)
            if trade is not None:
                trades.append(trade)
                position = None
            continue

        if i < WARMUP_CANDLES:
            continue
        current_atr = atr_lookup.at(candle.t)
        if not current_atr:
            continue
        position = _find_entry(candles, i, active, structure_4h.at(candle.t), structure_1d.at(candle.t), current_atr)

    if state_out is not None:
        state_out.update(active=active, position=position)
    return trades
