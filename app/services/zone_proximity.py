"""Detects when price sits next to a live 4H supply or demand zone."""
import strategyBacktest as sb
from services.config import ZONE_4H_PROXIMITY_PCT
from services.formatters import serialize_zone


def detect_4h_zone_proximity(frames240, price, atr_now):
    if not frames240 or not price:
        return None
    zones = sb.clone_zones(sb.source_zones(frames240, "240"))
    for z in zones:
        for c in frames240:
            if c.t < z.known_t:
                continue
            if z.kind == "demand" and c.c < z.low:
                z.invalidated = True
                break
            if z.kind == "supply" and c.c > z.high:
                z.invalidated = True
                break
    live_sup = sorted((z for z in zones if not z.invalidated and z.kind == "supply" and z.low >= price), key=lambda z: z.low - price)
    live_dem = sorted((z for z in zones if not z.invalidated and z.kind == "demand" and z.high <= price), key=lambda z: price - z.high)
    limit = max(float(atr_now), price * ZONE_4H_PROXIMITY_PCT) if atr_now else price * ZONE_4H_PROXIMITY_PCT
    sup_dist = (live_sup[0].low - price) if live_sup else None
    dem_dist = (price - live_dem[0].high) if live_dem else None
    candidates = []
    if sup_dist is not None and sup_dist <= limit:
        candidates.append((sup_dist, "supply", "NEAR 4H SUPPLY", live_sup[0]))
    if dem_dist is not None and dem_dist <= limit:
        candidates.append((dem_dist, "demand", "NEAR 4H DEMAND", live_dem[0]))
    if not candidates:
        return None
    dist, side, label, zone = min(candidates, key=lambda x: x[0])
    return {
        "label": label,
        "side": side,
        "distPct": round((dist / price) * 100, 2),
        "zone": serialize_zone(zone),
    }
