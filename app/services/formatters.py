"""Pure formatting and serialization helpers for analyzer payloads."""
import apiAnalyze as live
import strategyBacktest as sb
from services.price_format import fmt_price, round_price


def fmt_age(ms):
    minutes = int(ms // 60000)
    if minutes < 120:
        return f"{minutes}m"
    if minutes < 2880:
        return f"{minutes // 60}h"
    return f"{minutes // 1440}d"


def serialize_targets(ladder):
    return [
        {
            "label": item["label"],
            "price": round_price(item["price"]),
            "rr": item["rr"],
            "source": item["source"],
            "note": item["note"],
        }
        for item in ladder
    ]


def position_targets(entry, stop, direction, active_zones, target, rr):
    opp_kind = "demand" if direction == "short" else "supply"
    opp = [z for z in active_zones if z.kind == opp_kind and not z.invalidated]
    ladder = sb.build_tp_ladder(entry, stop, direction, opp)
    if not ladder and target is not None:
        ladder = [{
            "label": "TP1",
            "price": target,
            "rr": rr,
            "source": "engine",
            "note": "Engine target",
        }]
    return serialize_targets(ladder)


def serialize_zone(zone):
    if zone is None:
        return None
    return {
        "kind": zone.kind,
        "low": round_price(zone.low),
        "high": round_price(zone.high),
        "proximal": round_price(zone.proximal),
        "distal": round_price(zone.distal),
        "hasFvg": bool(zone.has_fvg),
        "touchIndex": zone.touch_index,
    }


def serialize_replay(trades, replay_days):
    done = [t for t in trades if t.outcome != "OPEN"]
    if not done:
        return {
            "days": round(replay_days),
            "closed": 0,
            "wins": 0,
            "totalR": 0.0,
            "lastTrade": None,
            "summary": f"0 closed ({replay_days:.0f}d)",
        }
    wins = sum(1 for t in done if t.net_r > 0)
    total = round(sum(t.net_r for t in done), 2)
    last = done[-1]
    return {
        "days": round(replay_days),
        "closed": len(done),
        "wins": wins,
        "totalR": total,
        "lastTrade": {
            "outcome": last.outcome,
            "netR": round(last.net_r, 2),
            "exitUtc": f"{live.hhmm(last.exit_t)} UTC",
            "exitMs": last.exit_t,
        },
        "summary": (
            f"{len(done)} closed, {wins} won, {total:+.2f}R net ({live.COST_PCT}% cost) | "
            f"last: {last.direction} {last.outcome} {last.net_r:+.2f}R ({live.hhmm(last.exit_t)} UTC)"
        ),
    }


def signal_position_payload(pos, active, age, drift):
    return {
        "direction": pos["direction"],
        "entry": round_price(pos["entry"]),
        "stop": round_price(pos["orig_stop"]),
        "activeStop": round_price(pos["stop"]),
        "target": round_price(pos["target"]),
        "targets": position_targets(pos["entry"], pos["orig_stop"], pos["direction"], active, pos["target"], pos["rr"]),
        "rr": pos["rr"],
        "ageCandles": age,
        "unrealR": drift,
        "closedAtUtc": f"{live.hhmm(pos['signal_t'] + live.FIVE_MS)} UTC",
        "entryTimeSec": int(pos["entry_t"] // 1000),
    }


def build_copy_text(result):
    sc_zone = result["scalpZone"]
    sc = result["scalp"]
    intr = result["intraday"]
    lines = [
        f"{result['symbol']} | Price {fmt_price(result['price'])} | 4H {result['structure4h']} | 1D {result['structure1d']}",
        f"5m EMA 9/20 [{sc_zone['emaBadge']}]: {result['emaOrder']}, slope {result['emaSlope']} ({result['lastCross']['summary']})",
        f"Scalp Zone (context only, untested): {sc_zone['verdictKind']} — {sc_zone['verdictText']}",
        f"Scalp v4 EMA Cross: {sc['verdictKind']} — {sc['verdictText']}",
    ]
    for side in ("long", "short"):
        info = sc_zone[side]
        z = info["zone"]
        if z:
            lines.append(
                f"  Zone {side.upper()}: {fmt_price(z['low'])}-{fmt_price(z['high'])} "
                f"(SL {fmt_price(info['stop'])}, TP {fmt_price(info['target'])}, {info['rr']}R) | {info['status']}"
            )
        else:
            lines.append(f"  Zone {side.upper()}: {info['status']}")
    lines.append(f"Intraday: {intr['verdictKind']} — {intr['verdictText']}")
    for side in ("long", "short"):
        info = intr[side]
        z = info["nearestZone"]
        ztxt = f"{fmt_price(z['low'])}-{fmt_price(z['high'])}" if z else "none"
        lines.append(f"  Intraday {side.upper()} nearest zone: {ztxt} | {info['status']}")
    return "\n".join(lines)
