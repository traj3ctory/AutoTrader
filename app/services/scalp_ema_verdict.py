"""Verdict for the Scalp v4 EMA-cross mode."""
import apiAnalyze as live
import scalpBacktestV3 as v3
from services.formatters import serialize_replay, serialize_zone, signal_position_payload
from services.price_format import fmt_price, round_price


def _position_verdict(ctx, pos, active):
    i, price = ctx["i"], ctx["price"]
    age = i - pos["entry_index"]
    side = pos["direction"].upper()
    drift = round(live.unreal_r(pos, price), 2)
    levels = f"entry {fmt_price(pos['entry'])}, SL {fmt_price(pos['orig_stop'])}, TP {fmt_price(pos['target'])}, R:R {pos['rr']}"
    if age == 0:
        kind, tradeable = "VALID", True
        text = f"VALID {side} closed {live.hhmm(pos['signal_t'] + live.FIVE_MS)} UTC: {levels}"
    elif age <= live.LATE_ENTRY_CANDLES:
        kind, tradeable = "LATE_ENTRY", True
        text = f"LATE ENTRY ({age}c ago, <=12c tested equal) {side}: {levels} ({drift:+.2f}R)"
    else:
        kind, tradeable = "ENGINE_IN_TRADE", False
        text = f"ENGINE IN TRADE ({age}c ago, too old) {side}: {levels} ({drift:+.2f}R)"
    payload = signal_position_payload(pos, active, age, drift)
    return kind, tradeable, text, payload


def _side_gates(ctx, active, target_zones):
    sides = {}
    pairs = (("long", ctx["bull_cross"], ctx["bull_slope"]), ("short", ctx["bear_cross"], ctx["bear_slope"]))
    for direction, crossed, sloped in pairs:
        zone, stop, rr, target = live.scalp_reference(direction, active, ctx["price"], ctx["atr_now"], target_zones)
        blocks = []
        if not crossed:
            blocks.append("no 9/20 cross on last closed 5m candle")
        if not sloped:
            blocks.append("EMAs not sloping in direction")
        if direction == "short":
            if ctx["bias1d"] not in ("bearish", "range"):
                blocks.append(f"1D structure ({ctx['bias1d']})")
            if not v3.micro_break(ctx["c5"], ctx["i"], "short"):
                blocks.append("no 5m micro-structure break")
        side_txt = "below" if direction == "long" else "above"
        kind = "demand" if direction == "long" else "supply"
        if zone is None:
            blocks.append(f"no unused 1H {kind} zone {side_txt} price for an entry (4H zones set targets only)")
        elif rr is None:
            blocks.append("no room for 1.5R before next opposing zone")
        sides[direction] = {
            "blockedBy": blocks,
            "status": "all gates pass" if not blocks else "blocked by: " + "; ".join(blocks),
            "zone": serialize_zone(zone),
            "stop": round_price(stop),
            "target": round_price(target),
            "rr": rr,
        }
    return sides


def build_scalp_ema(ctx, state, trades, replay_days):
    pos, active = state["position"], state["active"]
    target_zones = state.get("target_zones", active)
    if pos is not None:
        kind, tradeable, text, payload = _position_verdict(ctx, pos, target_zones)
    else:
        kind, tradeable, payload = "NO_SIGNAL", False, None
        text = "NO SIGNAL on the last closed 5m candle"
    sides = _side_gates(ctx, active, target_zones)
    return {
        "verdictKind": kind,
        "verdictText": text,
        "tradeable": tradeable,
        "position": payload,
        "long": sides["long"],
        "short": sides["short"],
        "replay": serialize_replay(trades, replay_days),
    }
