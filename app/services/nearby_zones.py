"""Collects the nearest live supply and demand zones per engine for the chart."""
from services.formatters import serialize_zone

ZONES_PER_SIDE = 2
TARGET_MATCH_PCT = 0.0005


def _tag(zone):
    item = serialize_zone(zone)
    item["tf"] = zone.source_tf
    item["refined"] = bool(zone.refined)
    item["consumed"] = bool(zone.consumed)
    item["timeSec"] = int(zone.t // 1000)
    return item


def _is_target_zone(zone, target_prices):
    return any(abs(edge - tp) <= tp * TARGET_MATCH_PCT for edge in (zone.low, zone.high) for tp in target_prices)


def nearby_zones(*, zones, price, target_prices):
    """Nearest unused demand at or below and supply at or above price (including one price sits inside), plus any zone whose edge is a trade target."""
    # Used zones are left out unless they are the target, so each side shows the nearest unused levels.
    live = [z for z in zones if not z.invalidated and (not z.consumed or _is_target_zone(z, target_prices))]
    demand = sorted((z for z in live if z.kind == "demand" and z.low <= price), key=lambda z: abs(price - z.proximal))
    supply = sorted((z for z in live if z.kind == "supply" and z.high >= price), key=lambda z: abs(z.proximal - price))

    def pick(side):
        chosen = side[:ZONES_PER_SIDE]
        chosen += [z for z in side[ZONES_PER_SIDE:] if _is_target_zone(z, target_prices)]
        return [dict(_tag(z), isTarget=_is_target_zone(z, target_prices)) for z in chosen]

    return {"demand": pick(demand), "supply": pick(supply)}


def engine_targets(mode_data):
    pos = mode_data.get("position") or mode_data.get("pending") or {}
    return [t["price"] for t in pos.get("targets", [])] or ([pos["target"]] if pos.get("target") else [])
