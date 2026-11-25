"""Verdict for the intraday (1H zone, 15m confirmation) mode."""
import apiAnalyze as live
import strategyBacktest as sb
from services.config import INTRADAY_PENDING_VALID_CANDLES
from services.formatters import fmt4, fmt_age, position_targets, serialize_replay, serialize_zone


def _filled_verdict(pos, active, p15, t15, span15):
    drift = round(live.unreal_r(pos, p15), 2)
    text = (
        f"ENGINE IN TRADE {pos['direction'].upper()} filled {live.hhmm(pos['entry_t'])} UTC: "
        f"entry {fmt4(pos['entry'])}, SL {fmt4(pos['stop'])}, TP {fmt4(pos['target'])}, "
        f"R:R {pos['rr']} ({drift:+.2f}R)"
    )
    payload = {
        "direction": pos["direction"],
        "entry": round(pos["entry"], 4),
        "stop": round(pos["stop"], 4),
        "target": round(pos["target"], 4),
        "targets": position_targets(pos["entry"], pos["stop"], pos["direction"], active, pos["target"], pos["rr"]),
        "rr": pos["rr"],
        "ageCandles": max(0, int((t15 - pos["entry_t"]) // span15)),
        "unrealR": drift,
        "entryAtUtc": f"{live.hhmm(pos['entry_t'])} UTC",
        "entryTimeSec": int(pos["entry_t"] // 1000),
    }
    return "ENGINE_IN_TRADE", False, text, payload, None


def _pending_verdict(pend, active, p15, t15, span15):
    age = (t15 - pend["signal_t"]) // span15
    gap = round(abs(pend["entry"] - p15) / p15 * 100, 2)
    if age <= INTRADAY_PENDING_VALID_CANDLES:
        text = (
            f"VALID {pend['direction'].upper()} "
            f"({pend['confirmation']}, {age}c ago): limit {fmt4(pend['entry'])} ({gap:.1f}% away), "
            f"SL {fmt4(pend['stop'])}, TP {fmt4(pend['target'])}, R:R {pend['rr']}"
        )
        payload = {
            "direction": pend["direction"],
            "confirmation": pend["confirmation"],
            "entry": round(pend["entry"], 4),
            "stop": round(pend["stop"], 4),
            "target": round(pend["target"], 4),
            "targets": position_targets(pend["entry"], pend["stop"], pend["direction"], active, pend["target"], pend["rr"]),
            "rr": pend["rr"],
            "ageCandles": age,
            "gapPct": gap,
            "entryTimeSec": int((pend["signal_t"] + span15) // 1000),
        }
        return "VALID", True, text, None, payload
    # The engine never expires an unfilled limit; past the tested window it is a missed signal.
    text = (
        f"STALE ORDER {pend['direction'].upper()} (signalled {fmt_age(age * span15)} ago, "
        f"limit {fmt4(pend['entry'])} is {gap:.1f}% from price) - missed signal, not actionable"
    )
    return "STALE_ORDER", False, text, None, None


def _side_gates(frames, active, bias1d, p15):
    c15 = frames["15"]
    last15 = c15[-1]
    i15 = len(c15) - 1
    sides = {}
    for direction, kind in (("long", "demand"), ("short", "supply")):
        live_zones = [z for z in active if z.kind == kind and not z.invalidated and not z.consumed]
        live_zones.sort(key=lambda z: abs(p15 - z.proximal))
        nearest = live_zones[0] if live_zones else None
        blocks = []
        if bias1d == "range":
            blocks.append("1D structure is range (trades neither side)")
        elif (bias1d == "bullish") != (direction == "long"):
            blocks.append(f"1D structure ({bias1d}) opposes {direction}")
        touched = [z for z in live_zones if z.touch_index is not None and 0 <= i15 - z.touch_index <= 4]
        if not touched:
            blocks.append(f"no unused {kind} zone first touched in last 4 closed 15m candles")
        elif not any(sb.rejection(last15, z, direction) or sb.engulfing(c15[-2], last15, z, direction) for z in touched):
            blocks.append("touched zone lacks 15m rejection/engulfing")
        sides[direction] = {
            "blockedBy": blocks,
            "status": "all gates pass" if not blocks else "blocked by: " + "; ".join(blocks),
            "nearestZone": serialize_zone(nearest),
        }
    return sides


def build_intraday(frames, state, trades, replay_days):
    last15 = frames["15"][-1]
    p15, t15 = last15.c, last15.t
    span15 = sb.INTERVAL_MS["15"]
    bias1d = sb.StructureLookup(frames["D"], "D").at(t15)
    pos, pend, active = state["position"], state["pending"], state["active"]

    if pos is not None:
        kind, tradeable, text, pos_payload, pend_payload = _filled_verdict(pos, active, p15, t15, span15)
    elif pend is not None:
        kind, tradeable, text, pos_payload, pend_payload = _pending_verdict(pend, active, p15, t15, span15)
    else:
        kind, tradeable, text, pos_payload, pend_payload = "NO_SIGNAL", False, "NO SIGNAL on the last closed 15m candle", None, None

    sides = _side_gates(frames, active, bias1d, p15)
    return {
        "verdictKind": kind,
        "verdictText": text,
        "tradeable": tradeable,
        "position": pos_payload,
        "pending": pend_payload,
        "long": sides["long"],
        "short": sides["short"],
        "replay": serialize_replay(trades, replay_days),
    }


def last_closed_15m_label(frames):
    last15 = frames["15"][-1]
    return f"{live.hhmm(last15.t + sb.INTERVAL_MS['15'])} UTC"
