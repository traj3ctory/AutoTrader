"""Verdict for the experimental Scalp Zone mode."""
import apiAnalyze as live
import strategyBacktest as sb
from services.config import SL_ATR_BUFFER_MULT, ZONE_LATE_ENTRY_CANDLES
from services.formatters import serialize_replay, serialize_zone, signal_position_payload
from services.price_format import fmt_price, round_price


def _ema_badge(ctx, direction):
    e9, e20, i = ctx["e9"], ctx["e20"], ctx["i"]
    bull, bear = ctx["bull_slope"], ctx["bear_slope"]
    if direction is None:
        return "BULL" if (e9[i] > e20[i] and bull) else "BEAR" if (e9[i] < e20[i] and bear) else "MIXED"
    if direction == "long":
        return "SUPPORTING" if (e9[i] > e20[i] and bull) else "COUNTER" if (e9[i] < e20[i] and bear) else "NEUTRAL"
    return "SUPPORTING" if (e9[i] < e20[i] and bear) else "COUNTER" if (e9[i] > e20[i] and bull) else "NEUTRAL"


def _position_verdict(ctx, pos, active):
    age = ctx["i"] - pos["entry_index"]
    side = pos["direction"].upper()
    drift = round(live.unreal_r(pos, ctx["price"]), 2)
    levels = f"entry {fmt_price(pos['entry'])}, SL {fmt_price(pos['orig_stop'])}, TP {fmt_price(pos['target'])}, R:R {pos['rr']}"
    if age == 0:
        kind, tradeable = "VALID", True
        text = f"VALID {side} zone bounce closed {live.hhmm(pos['signal_t'] + live.FIVE_MS)} UTC: {levels}"
    elif age <= ZONE_LATE_ENTRY_CANDLES:
        kind, tradeable = "LATE_ENTRY", True
        text = f"LATE ENTRY ({age}c ago) {side} zone bounce: {levels} ({drift:+.2f}R)"
    else:
        kind, tradeable = "ENGINE_IN_TRADE", False
        text = f"ENGINE IN TRADE ({age}c ago) {side}: {levels} ({drift:+.2f}R)"
    payload = signal_position_payload(pos, active, age, drift)
    return kind, tradeable, text, payload


def _side_gates(ctx, active):
    c5, i, price, atr_now = ctx["c5"], ctx["i"], ctx["price"], ctx["atr_now"]
    prev5 = c5[i - 1]
    sides = {}
    for direction, kind in (("long", "demand"), ("short", "supply")):
        against = "bearish" if direction == "long" else "bullish"
        blocks = []
        if ctx["bias4h"] == against:
            blocks.append(f"4H counter-trend ({ctx['bias4h']})")
        if direction == "short" and ctx["bias1d"] not in ("bearish", "range"):
            blocks.append(f"1D structure ({ctx['bias1d']})")
        live_z = [z for z in active if z.kind == kind and not z.invalidated and not z.consumed]
        live_z.sort(key=lambda z: abs(price - z.proximal))
        nearest_z = live_z[0] if live_z else None
        touched_z = [z for z in live_z if z.touch_index is not None and 0 <= i - z.touch_index <= 4]
        picked_z = None
        if not touched_z:
            blocks.append(f"no unused {kind} zone touched in last 4 closed 5m candles")
        else:
            picked_z = next(
                (z for z in touched_z if sb.rejection(c5[i], z, direction) or sb.engulfing(prev5, c5[i], z, direction)),
                None,
            )
            if picked_z is None:
                blocks.append("touched zone lacks 5m rejection/engulfing")
        ref_z = picked_z or nearest_z
        z_stop = z_rr = z_target = None
        if ref_z is not None and atr_now:
            z_stop = ref_z.low - SL_ATR_BUFFER_MULT * atr_now if direction == "long" else ref_z.high + SL_ATR_BUFFER_MULT * atr_now
            opp = [z for z in active if z.kind != kind and not z.invalidated]
            z_rr, z_target = sb.choose_rr(price, z_stop, direction, opp)
            if picked_z is not None and z_rr is None:
                blocks.append("no room for 1.5R before next opposing zone")
        sides[direction] = {
            "blockedBy": blocks,
            "status": "all gates pass" if not blocks else "blocked by: " + "; ".join(blocks),
            "zone": serialize_zone(ref_z),
            "stop": round_price(z_stop),
            "target": round_price(z_target),
            "rr": z_rr,
        }
    return sides


def build_scalp_zone(ctx, state, trades, replay_days):
    pos, active = state["position"], state["active"]
    if pos is not None:
        kind, _, text, payload = _position_verdict(ctx, pos, active)
        badge = _ema_badge(ctx, pos["direction"])
    else:
        kind, payload = "NO_SIGNAL", None
        text = "NO SIGNAL — waiting for 15m zone touch + 5m rejection/engulfing"
        badge = _ema_badge(ctx, None)
    sides = _side_gates(ctx, active)
    return {
        "verdictKind": kind,
        "verdictText": text,
        "tradeable": False,
        "contextOnly": True,
        "emaBadge": badge,
        "position": payload,
        "long": sides["long"],
        "short": sides["short"],
        "replay": serialize_replay(trades, replay_days),
    }
