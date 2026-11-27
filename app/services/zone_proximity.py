"""Detects when price sits next to a live 4H supply or demand zone."""
import strategyBacktest as sb
from services.config import ZONE_4H_PROXIMITY_PCT
from services.formatters import serialize_zone


def _nearest(*, zones, side, price):
    # Distance to the zone's near edge; zero while price is inside it.
    if side == "supply":
        found = [(max(0.0, z.low - price), z) for z in zones if z.kind == side and z.high >= price]
    else:
        found = [(max(0.0, price - z.high), z) for z in zones if z.kind == side and z.low <= price]
    return min(found, key=lambda item: item[0], default=None)


def _badge(*, side, dist, zone, price):
    inside = zone.low <= price <= zone.high
    return {
        "label": f"{'INSIDE' if inside else 'NEAR'} 4H {side.upper()}",
        "side": side,
        "distPct": round((dist / price) * 100, 2),
        "zone": serialize_zone(zone),
    }


def detect_4h_zone_proximity(frames240, price, atr_now, now_ms):
    # The last 4H bucket is still forming until its close time has passed.
    closed = [c for c in frames240 if c.t + sb.INTERVAL_MS["240"] <= now_ms]
    if not closed or not price:
        return None
    zones = sb.clone_zones(sb.source_zones(closed, "240"))
    for z in zones:
        for c in closed:
            if c.t < z.known_t:
                continue
            if z.kind == "demand" and c.c < z.low:
                z.invalidated = True
                break
            if z.kind == "supply" and c.c > z.high:
                z.invalidated = True
                break
    live_zones = [z for z in zones if not z.invalidated and z.known_t <= now_ms]
    limit = max(float(atr_now), price * ZONE_4H_PROXIMITY_PCT) if atr_now else price * ZONE_4H_PROXIMITY_PCT
    nearby = {}
    for side in ("supply", "demand"):
        found = _nearest(zones=live_zones, side=side, price=price)
        if found and found[0] <= limit:
            nearby[side] = found
    if not nearby:
        return None
    sides = {side: _badge(side=side, dist=dist, zone=zone, price=price) for side, (dist, zone) in nearby.items()}
    nearest = min(nearby, key=lambda side: nearby[side][0])
    # Both sides travel with the badge so the veto can check the one that blocks the trade.
    return {**sides[nearest], "sides": sides}
