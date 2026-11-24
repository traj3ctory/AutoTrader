#!/usr/bin/env python3
"""Local HTTP server for the AutoTrader Analyzer dashboard."""
import datetime as dt
import json
import mimetypes
import os
import re
import subprocess
import sys
import threading
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = ROOT / "scripts"
WEB_DIST = ROOT / "app" / "web" / "dist"
sys.path.insert(0, str(SCRIPTS_DIR))

import apiAnalyze as live  # noqa: E402
import riskGuard  # noqa: E402
import strategyBacktest as sb  # noqa: E402
import scalpBacktestV3 as v3  # noqa: E402

HOST = os.environ.get("AUTOTRADER_HOST", "127.0.0.1")
PORT = int(os.environ.get("AUTOTRADER_PORT", "8787"))
SUBPROCESS_TIMEOUT_SEC = 60
CANDLE_LIMIT = 220
VALID_TFS = {"5", "15", "60", "240"}

ENGINE_LOCK = threading.Lock()
RISK_LOCK = threading.Lock()


def normalize_symbol(raw):
    sym = raw.strip().upper().replace(".P", "")
    if sym and not sym.endswith("USDT"):
        sym = f"{sym}USDT"
    return sym


def load_json(path, fallback):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return fallback


def read_text_safe(path):
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def parse_movers_md():
    path = ROOT / "MOVER_SCAN.md"
    if not path.exists():
        return {"updatedAt": None, "gainers": [], "losers": [], "rangeMovers": [], "raw": ""}
    raw = path.read_text(encoding="utf-8")
    updated_at = None
    gainers, losers, range_movers = [], [], []
    section = None
    pct_re = re.compile(
        r"^(\S+)\s+([+-]\d+(?:\.\d+)?)%\s+turnover\s+\$(\d+(?:\.\d+)?)M\s+price\s+(\S+)(.*)$"
    )
    range_re = re.compile(
        r"^(\S+)\s+range\s+(\d+(?:\.\d+)?)%\s+\(H\s+(\S+)\s+/\s+L\s+(\S+)\)\s+net\s+([+-]\d+(?:\.\d+)?)%\s+turnover\s+\$(\d+(?:\.\d+)?)M\s+price\s+(\S+)(.*)$"
    )
    for line in raw.splitlines():
        if line.startswith("# Bybit mover scan"):
            parts = line.split("—", 1)
            updated_at = parts[1].strip() if len(parts) > 1 else None
        elif line.startswith("## Top") and "gainer" in line.lower():
            section = "gainers"
        elif line.startswith("## Top") and "loser" in line.lower():
            section = "losers"
        elif line.startswith("## Intraday range movers"):
            section = "range"
        elif line.startswith("Filters:"):
            section = None
        elif section in ("gainers", "losers"):
            m = pct_re.match(line.strip())
            if m:
                row = {
                    "ticker": m.group(1),
                    "symbol": m.group(1).replace(".P", ""),
                    "pct": float(m.group(2)),
                    "turnoverM": float(m.group(3)),
                    "price": float(m.group(4)),
                    "inLedger": "[already in ledger]" in m.group(5),
                }
                (gainers if section == "gainers" else losers).append(row)
        elif section == "range":
            m = range_re.match(line.strip())
            if m:
                range_movers.append({
                    "ticker": m.group(1),
                    "symbol": m.group(1).replace(".P", ""),
                    "rangePct": float(m.group(2)),
                    "high": float(m.group(3)),
                    "low": float(m.group(4)),
                    "pct": float(m.group(5)),
                    "turnoverM": float(m.group(6)),
                    "price": float(m.group(7)),
                    "inLedger": "[already in ledger]" in m.group(8),
                })
    return {
        "updatedAt": updated_at,
        "gainers": gainers,
        "losers": losers,
        "rangeMovers": range_movers,
        "raw": raw,
    }


def serialize_zone(zone):
    if zone is None:
        return None
    return {
        "kind": zone.kind,
        "low": round(zone.low, 8),
        "high": round(zone.high, 8),
        "proximal": round(zone.proximal, 8),
        "distal": round(zone.distal, 8),
        "hasFvg": bool(zone.has_fvg),
        "touchIndex": zone.touch_index,
    }


def serialize_replay(trades, replay_days):
    done = [t for t in trades if t.outcome != "OPEN"]
    if not done:
        return {"days": round(replay_days), "closed": 0, "wins": 0, "totalR": 0.0, "summary": f"0 closed ({replay_days:.0f}d)"}
    wins = sum(1 for t in done if t.net_r > 0)
    total = round(sum(t.net_r for t in done), 2)
    last = done[-1]
    return {
        "days": round(replay_days),
        "closed": len(done),
        "wins": wins,
        "totalR": total,
        "summary": (
            f"{len(done)} closed, {wins} won, {total:+.2f}R net ({live.COST_PCT}% cost) | "
            f"last: {last.direction} {last.outcome} {last.net_r:+.2f}R ({live.hhmm(last.exit_t)} UTC)"
        ),
    }


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
            if zone.touch_index is not None and i - zone.touch_index > 4:
                zone.consumed = True

        if not in_test:
            continue

        if position is not None:
            direction = position["direction"]
            if not position.get("breakeven_applied") and i - position["entry_index"] >= live.TIME_STOP_CANDLES:
                risk = abs(position["entry"] - position["orig_stop"])
                unreal = ((candle.c - position["entry"]) if direction == "long" else (position["entry"] - candle.c)) / risk if risk else 0.0
                if unreal < live.TIME_STOP_MIN_R:
                    position["stop"] = position["entry"]
                position["breakeven_applied"] = True
            stop_hit = candle.l <= position["stop"] if direction == "long" else candle.h >= position["stop"]
            target_hit = candle.h >= position["target"] if direction == "long" else candle.l <= position["target"]
            if stop_hit or target_hit:
                if stop_hit:
                    exit_price = position["stop"]
                    gross_r = sb.outcome_from_exit(direction, position["entry"], position["orig_stop"], exit_price)
                    result = "SL" if exit_price != position["entry"] else "BE"
                else:
                    exit_price, result, gross_r = position["target"], "TP", position["rr"]
                trades.append(sb.make_trade(
                    "ScalpZone", symbol, direction, position["signal_t"], position["entry_t"],
                    candle.t + sb.INTERVAL_MS["5"], position["entry"], position["orig_stop"],
                    position["target"], position["rr"], exit_price, result, gross_r,
                    0.5, cost_pct, position["zone_tf"], "5m-zone-rej",
                ))
                position = None
            continue

        if i < 20:
            continue
        bias4h = structure_4h.at(candle.t)
        bias1d = structure_1d.at(candle.t)
        current_atr = atr_lookup.at(candle.t)
        if not current_atr:
            continue

        prev = candles[i - 1]
        for direction, kind in (("long", "demand"), ("short", "supply")):
            if direction == "long" and bias4h == "bearish":
                continue
            if direction == "short" and (bias4h == "bullish" or bias1d not in ("bearish", "range")):
                continue
            cands = [
                z for z in active
                if z.kind == kind and not z.invalidated and not z.consumed
                and z.touch_index is not None and 0 <= i - z.touch_index <= 4
            ]
            picked = next(
                (z for z in cands if sb.rejection(candle, z, direction) or sb.engulfing(prev, candle, z, direction)),
                None,
            )
            if picked is None:
                continue
            entry = candle.c
            stop = picked.low - 0.50 * current_atr if direction == "long" else picked.high + 0.50 * current_atr
            if (direction == "long" and stop >= entry) or (direction == "short" and stop <= entry):
                picked.consumed = True
                continue
            opposite = [z for z in active if z.kind != kind and z.known_t <= candle.t and not z.invalidated]
            rr, target = sb.choose_rr(entry, stop, direction, opposite)
            picked.consumed = True
            if rr is None or target is None:
                continue
            position = {
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
            break

    if state_out is not None:
        state_out.update(active=active, position=position)
    return trades


def build_copy_text(result):
    sc_zone = result["scalpZone"]
    sc = result["scalp"]
    intr = result["intraday"]
    lines = [
        f"{result['symbol']} | Price {result['price']:.6g} | 4H {result['structure4h']} | 1D {result['structure1d']}",
        f"5m EMA 9/20 [{sc_zone['emaBadge']}]: {result['emaOrder']}, slope {result['emaSlope']} ({result['lastCross']['summary']})",
        f"Scalp Zone (EMA badge only): {sc_zone['verdictKind']} — {sc_zone['verdictText']}",
        f"Scalp v4 EMA Cross: {sc['verdictKind']} — {sc['verdictText']}",
    ]
    for side in ("long", "short"):
        info = sc_zone[side]
        z = info["zone"]
        if z:
            lines.append(f"  Zone {side.upper()}: {z['low']}-{z['high']} (SL {info['stop']}, TP {info['target']}, {info['rr']}R) | {info['status']}")
        else:
            lines.append(f"  Zone {side.upper()}: {info['status']}")
    lines.append(f"Intraday: {intr['verdictKind']} — {intr['verdictText']}")
    for side in ("long", "short"):
        info = intr[side]
        z = info["nearestZone"]
        ztxt = f"{z['low']}-{z['high']}" if z else "none"
        lines.append(f"  Intraday {side.upper()} nearest zone: {ztxt} | {info['status']}")
    return "\n".join(lines)


def analyze_symbol(symbol, tf="15", include_candles=True):
    if tf not in VALID_TFS:
        tf = "15"
    with ENGINE_LOCK:
        five = live.load_history(symbol)
        frames = live.build_frames(five)
        span_days, replay_days = live.set_window(five)

        c5 = frames["5"]
        scalp_zone_state = {}
        scalp_zone_trades = run_scalp_zone(symbol, frames, live.COST_PCT, state_out=scalp_zone_state)
        scalp_state = {}
        scalp_trades = v3.run_scalp_v3(
            symbol,
            frames,
            live.COST_PCT,
            short_gates=True,
            time_stop=True,
            time_stop_candles=live.TIME_STOP_CANDLES,
            time_stop_min_r=live.TIME_STOP_MIN_R,
            state_out=scalp_state,
        )
        c15 = frames["15"]
        intraday_state = {}
        intraday_trades = sb.run_intraday(symbol, frames, live.COST_PCT, state_out=intraday_state)

    i = len(c5) - 1
    price, now_t = c5[i].c, c5[i].t
    closes5 = [c.c for c in c5]
    e9, e20 = sb.ema(closes5, 9), sb.ema(closes5, 20)
    bias4h = sb.StructureLookup(frames["240"], "240").at(now_t)
    bias1d = sb.StructureLookup(frames["D"], "D").at(now_t)
    atr_now = sb.SeriesLookup(frames["240"], "240", sb.atr(frames["240"])).at(now_t)
    vwap = sb.daily_vwap(c5)[i]

    bull_cross = e9[i - 1] <= e20[i - 1] and e9[i] > e20[i]
    bear_cross = e9[i - 1] >= e20[i - 1] and e9[i] < e20[i]
    bull_slope = e9[i] > e9[i - 1] and e20[i] > e20[i - 1]
    bear_slope = e9[i] < e9[i - 1] and e20[i] < e20[i - 1]

    order = "BULL-ordered (9 above 20)" if e9[i] > e20[i] else "BEAR-ordered (9 below 20)"
    slope = "UP" if bull_slope else "DOWN" if bear_slope else "MIXED"
    last_cross = {"direction": None, "closedAtUtc": None, "candlesAgo": None, "summary": "none"}
    for j in range(i, 0, -1):
        if None in (e9[j], e20[j], e9[j - 1], e20[j - 1]):
            break
        if (e9[j - 1] <= e20[j - 1]) != (e9[j] <= e20[j]):
            flip_dir = "BULLISH" if e9[j] > e20[j] else "BEARISH"
            closed_utc = f"{live.hhmm(c5[j].t + live.FIVE_MS)} UTC"
            ago = i - j
            last_cross = {
                "direction": flip_dir,
                "closedAtUtc": closed_utc,
                "candlesAgo": ago,
                "summary": f"{flip_dir} {closed_utc} ({ago}c ago)",
            }
            break

    pos = scalp_state["position"]
    active_scalp = scalp_state["active"]
    if pos is not None:
        age = i - pos["entry_index"]
        side = pos["direction"].upper()
        drift = round(live.unreal_r(pos, price), 2)
        if age == 0:
            scalp_kind = "VALID"
            scalp_tradeable = True
            scalp_text = (
                f"VALID {side} closed {live.hhmm(pos['signal_t'] + live.FIVE_MS)} UTC: "
                f"entry {pos['entry']:.6g}, SL {pos['orig_stop']:.6g}, TP {pos['target']:.6g}, R:R {pos['rr']}"
            )
        elif age <= live.LATE_ENTRY_CANDLES:
            scalp_kind = "LATE_ENTRY"
            scalp_tradeable = True
            scalp_text = (
                f"LATE ENTRY ({age}c ago, <=12c tested equal) {side}: "
                f"entry {pos['entry']:.6g}, SL {pos['orig_stop']:.6g}, TP {pos['target']:.6g}, R:R {pos['rr']} ({drift:+.2f}R)"
            )
        else:
            scalp_kind = "ENGINE_IN_TRADE"
            scalp_tradeable = False
            scalp_text = (
                f"ENGINE IN TRADE ({age}c ago, too old) {side}: "
                f"entry {pos['entry']:.6g}, SL {pos['orig_stop']:.6g}, TP {pos['target']:.6g}, R:R {pos['rr']} ({drift:+.2f}R)"
            )
        scalp_pos = {
            "direction": pos["direction"],
            "entry": round(pos["entry"], 8),
            "stop": round(pos["orig_stop"], 8),
            "activeStop": round(pos["stop"], 8),
            "target": round(pos["target"], 8),
            "rr": pos["rr"],
            "ageCandles": age,
            "unrealR": drift,
            "closedAtUtc": f"{live.hhmm(pos['signal_t'] + live.FIVE_MS)} UTC",
        }
    else:
        scalp_kind = "NO_SIGNAL"
        scalp_tradeable = False
        scalp_text = "NO SIGNAL on the last closed 5m candle"
        scalp_pos = None

    scalp_sides = {}
    for direction, crossed, sloped in (("long", bull_cross, bull_slope), ("short", bear_cross, bear_slope)):
        against = "bearish" if direction == "long" else "bullish"
        zone, stop, rr, target = live.scalp_reference(direction, active_scalp, price, atr_now)
        blocks = []
        if not crossed:
            blocks.append("no 9/20 cross on last closed 5m candle")
        if not sloped:
            blocks.append("EMAs not sloping in direction")
        if bias4h == against:
            blocks.append(f"4H counter-trend ({bias4h})")
        if direction == "short":
            if bias1d not in ("bearish", "range"):
                blocks.append(f"1D structure ({bias1d})")
            if not v3.micro_break(c5, i, "short"):
                blocks.append("no 5m micro-structure break")
        side_txt = "below" if direction == "long" else "above"
        kind = "demand" if direction == "long" else "supply"
        if zone is None:
            blocks.append(f"no live unused {kind} zone {side_txt} price")
        elif rr is None:
            blocks.append("no room for 1.5R before next opposing zone")
        scalp_sides[direction] = {
            "blockedBy": blocks,
            "status": "all gates pass" if not blocks else "blocked by: " + "; ".join(blocks),
            "zone": serialize_zone(zone),
            "stop": round(stop, 8) if stop is not None else None,
            "target": round(target, 8) if target is not None else None,
            "rr": rr,
        }

    zone_pos_raw = scalp_zone_state["position"]
    zone_active = scalp_zone_state["active"]
    if zone_pos_raw is not None:
        z_age = i - zone_pos_raw["entry_index"]
        z_side = zone_pos_raw["direction"].upper()
        z_drift = round(live.unreal_r(zone_pos_raw, price), 2)
        if z_age == 0:
            zone_kind = "VALID"
            zone_tradeable = True
            zone_text = (
                f"VALID {z_side} zone bounce closed {live.hhmm(zone_pos_raw['signal_t'] + live.FIVE_MS)} UTC: "
                f"entry {zone_pos_raw['entry']:.6g}, SL {zone_pos_raw['orig_stop']:.6g}, "
                f"TP {zone_pos_raw['target']:.6g}, R:R {zone_pos_raw['rr']}"
            )
        elif z_age <= 4:
            zone_kind = "LATE_ENTRY"
            zone_tradeable = True
            zone_text = (
                f"LATE ENTRY ({z_age}c ago) {z_side} zone bounce: "
                f"entry {zone_pos_raw['entry']:.6g}, SL {zone_pos_raw['orig_stop']:.6g}, "
                f"TP {zone_pos_raw['target']:.6g}, R:R {zone_pos_raw['rr']} ({z_drift:+.2f}R)"
            )
        else:
            zone_kind = "ENGINE_IN_TRADE"
            zone_tradeable = False
            zone_text = (
                f"ENGINE IN TRADE ({z_age}c ago) {z_side}: "
                f"entry {zone_pos_raw['entry']:.6g}, SL {zone_pos_raw['orig_stop']:.6g}, "
                f"TP {zone_pos_raw['target']:.6g}, R:R {zone_pos_raw['rr']} ({z_drift:+.2f}R)"
            )
        zone_pos = {
            "direction": zone_pos_raw["direction"],
            "entry": round(zone_pos_raw["entry"], 8),
            "stop": round(zone_pos_raw["orig_stop"], 8),
            "activeStop": round(zone_pos_raw["stop"], 8),
            "target": round(zone_pos_raw["target"], 8),
            "rr": zone_pos_raw["rr"],
            "ageCandles": z_age,
            "unrealR": z_drift,
            "closedAtUtc": f"{live.hhmm(zone_pos_raw['signal_t'] + live.FIVE_MS)} UTC",
        }
        if zone_pos_raw["direction"] == "long":
            zone_ema_badge = "SUPPORTING" if (e9[i] > e20[i] and bull_slope) else "COUNTER" if (e9[i] < e20[i] and bear_slope) else "NEUTRAL"
        else:
            zone_ema_badge = "SUPPORTING" if (e9[i] < e20[i] and bear_slope) else "COUNTER" if (e9[i] > e20[i] and bull_slope) else "NEUTRAL"
    else:
        zone_kind = "NO_SIGNAL"
        zone_tradeable = False
        zone_text = "NO SIGNAL — waiting for 15m zone touch + 5m rejection/engulfing"
        zone_pos = None
        zone_ema_badge = "BULL" if (e9[i] > e20[i] and bull_slope) else "BEAR" if (e9[i] < e20[i] and bear_slope) else "MIXED"

    prev5 = c5[i - 1]
    zone_sides = {}
    for direction, kind in (("long", "demand"), ("short", "supply")):
        against = "bearish" if direction == "long" else "bullish"
        blocks = []
        if bias4h == against:
            blocks.append(f"4H counter-trend ({bias4h})")
        if direction == "short" and bias1d not in ("bearish", "range"):
            blocks.append(f"1D structure ({bias1d})")
        live_z = [z for z in zone_active if z.kind == kind and not z.invalidated and not z.consumed]
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
            z_stop = ref_z.low - 0.50 * atr_now if direction == "long" else ref_z.high + 0.50 * atr_now
            opp = [z for z in zone_active if z.kind != kind and not z.invalidated]
            z_rr, z_target = sb.choose_rr(price, z_stop, direction, opp)
            if picked_z is not None and z_rr is None:
                blocks.append("no room for 1.5R before next opposing zone")
        zone_sides[direction] = {
            "blockedBy": blocks,
            "status": "all gates pass" if not blocks else "blocked by: " + "; ".join(blocks),
            "zone": serialize_zone(ref_z),
            "stop": round(z_stop, 8) if z_stop is not None else None,
            "target": round(z_target, 8) if z_target is not None else None,
            "rr": z_rr,
        }

    last15 = c15[-1]
    i15 = len(c15) - 1
    p15, t15 = last15.c, last15.t
    bias1d_15 = sb.StructureLookup(frames["D"], "D").at(t15)
    span15 = sb.INTERVAL_MS["15"]
    intr_pos_raw = intraday_state["position"]
    intr_pend_raw = intraday_state["pending"]
    intr_active = intraday_state["active"]

    if intr_pos_raw is not None:
        intr_kind = "ENGINE_IN_TRADE"
        intr_tradeable = False
        drift15 = round(live.unreal_r(intr_pos_raw, p15), 2)
        intr_text = (
            f"ENGINE IN TRADE {intr_pos_raw['direction'].upper()} filled {live.hhmm(intr_pos_raw['entry_t'])} UTC: "
            f"entry {intr_pos_raw['entry']:.6g}, SL {intr_pos_raw['stop']:.6g}, TP {intr_pos_raw['target']:.6g}, "
            f"R:R {intr_pos_raw['rr']} ({drift15:+.2f}R)"
        )
        intr_pos = {
            "direction": intr_pos_raw["direction"],
            "entry": round(intr_pos_raw["entry"], 8),
            "stop": round(intr_pos_raw["stop"], 8),
            "target": round(intr_pos_raw["target"], 8),
            "rr": intr_pos_raw["rr"],
            "unrealR": drift15,
            "entryAtUtc": f"{live.hhmm(intr_pos_raw['entry_t'])} UTC",
        }
        intr_pend = None
    elif intr_pend_raw is not None:
        age15 = (t15 - intr_pend_raw["signal_t"]) // span15
        gap = round(abs(intr_pend_raw["entry"] - p15) / p15 * 100, 2)
        intr_tradeable = age15 <= 4
        intr_kind = "VALID" if intr_tradeable else "RESTING"
        intr_text = (
            f"{'VALID' if intr_tradeable else 'RESTING'} {intr_pend_raw['direction'].upper()} "
            f"({intr_pend_raw['confirmation']}, {age15}c ago): limit {intr_pend_raw['entry']:.6g} ({gap:.1f}% away), "
            f"SL {intr_pend_raw['stop']:.6g}, TP {intr_pend_raw['target']:.6g}, R:R {intr_pend_raw['rr']}"
        )
        intr_pos = None
        intr_pend = {
            "direction": intr_pend_raw["direction"],
            "confirmation": intr_pend_raw["confirmation"],
            "entry": round(intr_pend_raw["entry"], 8),
            "stop": round(intr_pend_raw["stop"], 8),
            "target": round(intr_pend_raw["target"], 8),
            "rr": intr_pend_raw["rr"],
            "ageCandles": age15,
            "gapPct": gap,
        }
    else:
        intr_kind = "NO_SIGNAL"
        intr_tradeable = False
        intr_text = "NO SIGNAL on the last closed 15m candle"
        intr_pos = None
        intr_pend = None

    intr_sides = {}
    for direction, kind in (("long", "demand"), ("short", "supply")):
        live_zones = [z for z in intr_active if z.kind == kind and not z.invalidated and not z.consumed]
        live_zones.sort(key=lambda z: abs(p15 - z.proximal))
        nearest = live_zones[0] if live_zones else None
        blocks = []
        if bias1d_15 == "range":
            blocks.append("1D structure is range (trades neither side)")
        elif (bias1d_15 == "bullish") != (direction == "long"):
            blocks.append(f"1D structure ({bias1d_15}) opposes {direction}")
        touched = [z for z in live_zones if z.touch_index is not None and 0 <= i15 - z.touch_index <= 4]
        if not touched:
            blocks.append(f"no unused {kind} zone first touched in last 4 closed 15m candles")
        elif not any(sb.rejection(last15, z, direction) or sb.engulfing(c15[-2], last15, z, direction) for z in touched):
            blocks.append("touched zone lacks 15m rejection/engulfing")
        intr_sides[direction] = {
            "blockedBy": blocks,
            "status": "all gates pass" if not blocks else "blocked by: " + "; ".join(blocks),
            "nearestZone": serialize_zone(nearest),
        }

    candles_out = []
    if include_candles:
        tf_candles = frames[tf]
        tf_closes = [c.c for c in tf_candles]
        tf_e9 = sb.ema(tf_closes, 9)
        tf_e20 = sb.ema(tf_closes, 20)
        start_idx = max(0, len(tf_candles) - CANDLE_LIMIT)
        for idx in range(start_idx, len(tf_candles)):
            c = tf_candles[idx]
            candles_out.append({
                "time": int(c.t // 1000),
                "open": c.o,
                "high": c.h,
                "low": c.l,
                "close": c.c,
                "ema9": round(tf_e9[idx], 8) if tf_e9[idx] is not None else None,
                "ema20": round(tf_e20[idx], 8) if tf_e20[idx] is not None else None,
            })

    result = {
        "symbol": symbol,
        "ticker": f"{symbol}.P",
        "tf": tf,
        "price": round(price, 8),
        "historyDays": round(span_days),
        "lastClosed5mUtc": f"{live.hhmm(now_t + live.FIVE_MS)} UTC",
        "lastClosed15mUtc": f"{live.hhmm(t15 + span15)} UTC",
        "structure4h": bias4h,
        "structure1d": bias1d,
        "atr4hPct": round((atr_now / price) * 100, 2) if atr_now and price else None,
        "vwap": round(vwap, 8),
        "emaOrder": order,
        "emaSlope": slope,
        "lastCross": last_cross,
        "scalpZone": {
            "verdictKind": zone_kind,
            "verdictText": zone_text,
            "tradeable": zone_tradeable,
            "emaBadge": zone_ema_badge,
            "position": zone_pos,
            "long": zone_sides["long"],
            "short": zone_sides["short"],
            "replay": serialize_replay(scalp_zone_trades, replay_days),
        },
        "scalp": {
            "verdictKind": scalp_kind,
            "verdictText": scalp_text,
            "tradeable": scalp_tradeable,
            "position": scalp_pos,
            "long": scalp_sides["long"],
            "short": scalp_sides["short"],
            "replay": serialize_replay(scalp_trades, replay_days),
        },
        "intraday": {
            "verdictKind": intr_kind,
            "verdictText": intr_text,
            "tradeable": intr_tradeable,
            "position": intr_pos,
            "pending": intr_pend,
            "long": intr_sides["long"],
            "short": intr_sides["short"],
            "replay": serialize_replay(intraday_trades, replay_days),
        },
        "candles": candles_out,
    }
    result["copyText"] = build_copy_text(result)
    return result


TV_EXTRA_LIMIT = 3
SIGNAL_HISTORY_PATH = ROOT / "SIGNAL_HISTORY.json"
MAX_SIGNAL_HISTORY = 100
SIGNAL_LOCK = threading.Lock()


def load_signal_history():
    doc = load_json(SIGNAL_HISTORY_PATH, {"version": 1, "signals": []})
    items = doc.get("signals", [])
    return items if isinstance(items, list) else []


def record_signal_history(tradeable_items, scanned_at_utc):
    with SIGNAL_LOCK:
        doc = load_json(SIGNAL_HISTORY_PATH, {"version": 1, "signals": []})
        existing = doc.get("signals", [])
        if not isinstance(existing, list):
            existing = []
        seen_ids = {item.get("id") for item in existing if isinstance(item, dict)}
        added = []
        for item in tradeable_items:
            pos = (item.get("data") or {}).get("position") or {}
            pend = (item.get("data") or {}).get("pending") or {}
            stamp = pos.get("closedAtUtc") or pend.get("confirmation") or item["summary"][:64]
            sig_id = f"{item['symbol']}:{item['mode']}:{stamp}"
            if sig_id in seen_ids:
                continue
            seen_ids.add(sig_id)
            added.append({
                "id": sig_id,
                "seenAtUtc": scanned_at_utc,
                "symbol": item["symbol"],
                "mode": item["mode"],
                "emaBadge": item.get("emaBadge"),
                "summary": item["summary"],
                "copyText": item["copyText"],
            })
        if added:
            merged = (added + existing)[:MAX_SIGNAL_HISTORY]
            SIGNAL_HISTORY_PATH.write_text(
                json.dumps({"version": 1, "signals": merged}, indent=2) + "\n",
                encoding="utf-8",
            )
            return merged
        return existing


def parse_tier2_symbols():
    path = ROOT / "WATCHLIST_TIER2.md"
    if not path.is_file():
        return []
    found = []
    in_table = False
    row_re = re.compile(r"^\|\s*([A-Z0-9]+USDT(?:\.P)?)\s*\|")
    for line in path.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if s.startswith("| Coin |"):
            in_table = True
            continue
        if in_table:
            if not s.startswith("|"):
                break
            m = row_re.match(s)
            if m:
                sym = normalize_symbol(m.group(1))
                if sym and sym not in ("BTCUSDT", "ETHUSDT") and sym not in found:
                    found.append(sym)
    return found


def score_tv_candidate(res):
    score = 0.0
    if res["scalpZone"]["tradeable"] or res["scalp"]["tradeable"] or res["intraday"]["tradeable"]:
        score += 1000.0
    for side in ("long", "short"):
        sz = res["scalpZone"][side]
        if any("lacks 5m rejection/engulfing" in b for b in sz["blockedBy"]):
            score += 200.0
        if sz["zone"] is not None and sz["rr"] is not None:
            score += 50.0
        intr = res["intraday"][side]
        if any("lacks 15m rejection/engulfing" in b for b in intr["blockedBy"]):
            score += 120.0
    if res["structure4h"] == res["structure1d"] and res["structure4h"] in ("bullish", "bearish"):
        score += 80.0
    if res["intraday"]["pending"] is not None:
        score += 40.0
    score += max(0.0, min(40.0, float(res["scalpZone"]["replay"].get("totalR") or 0.0)))
    return score


def scan_symbols(extra_symbols):
    ledger = load_json(ROOT / "SETUP_LEDGER.json", {})
    tv_path = ROOT / "TV_WATCHLIST.json"
    tv_doc = load_json(tv_path, {})
    core_symbols = [s.replace(".P", "") for s in ledger.get("setups", {})]
    pool_raw = list(tv_doc.get("pool") or tv_doc.get("symbols") or []) + parse_tier2_symbols()
    pool_symbols = []
    for raw in pool_raw:
        sym = normalize_symbol(raw)
        if sym and sym not in core_symbols and sym not in pool_symbols:
            pool_symbols.append(sym)
    symbols = list(core_symbols)
    for sym in pool_symbols + [normalize_symbol(r) for r in extra_symbols]:
        if sym and sym not in symbols:
            symbols.append(sym)
    tradeable, checked, failed = [], [], []
    by_symbol = {}
    for sym in symbols:
        try:
            res = analyze_symbol(sym, tf="15", include_candles=False)
            by_symbol[sym] = res
            checked.append({
                "symbol": sym,
                "ticker": f"{sym}.P",
                "price": res["price"],
                "structure4h": res["structure4h"],
                "structure1d": res["structure1d"],
                "scalpZoneKind": res["scalpZone"]["verdictKind"],
                "scalpKind": res["scalp"]["verdictKind"],
                "intradayKind": res["intraday"]["verdictKind"],
                "tradeable": res["scalpZone"]["tradeable"] or res["scalp"]["tradeable"] or res["intraday"]["tradeable"],
                "copyText": res["copyText"],
            })
            if res["scalpZone"]["tradeable"]:
                tradeable.append({"symbol": sym, "mode": "Scalp Zone", "emaBadge": res["scalpZone"]["emaBadge"], "summary": res["scalpZone"]["verdictText"], "data": res["scalpZone"], "copyText": res["copyText"]})
            if res["scalp"]["tradeable"]:
                tradeable.append({"symbol": sym, "mode": "Scalp EMA", "summary": res["scalp"]["verdictText"], "data": res["scalp"], "copyText": res["copyText"]})
            if res["intraday"]["tradeable"]:
                tradeable.append({"symbol": sym, "mode": "Intraday", "summary": res["intraday"]["verdictText"], "data": res["intraday"], "copyText": res["copyText"]})
        except Exception as exc:
            failed.append({"symbol": sym, "error": str(exc)})

    now_iso = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    ranked_pool = sorted(
        (sym for sym in pool_symbols if sym in by_symbol),
        key=lambda sym: score_tv_candidate(by_symbol[sym]),
        reverse=True,
    )
    top_tv = [f"{sym}.P" for sym in ranked_pool[:TV_EXTRA_LIMIT]]
    if top_tv and tv_doc:
        tv_doc["symbols"] = top_tv
        tv_doc["updated_at"] = now_iso
        tv_path.write_text(json.dumps(tv_doc, indent=2) + "\n", encoding="utf-8")

    history = record_signal_history(tradeable, now_iso)
    return {
        "scannedAtUtc": now_iso,
        "tradeable": tradeable,
        "checked": checked,
        "failed": failed,
        "tvWatchlist": top_tv or tv_doc.get("symbols", []),
        "signalHistory": history[:30],
        "risk": riskGuard.status(),
    }


def run_node_script(script_name):
    proc = subprocess.run(
        ["node", str(SCRIPTS_DIR / script_name)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=SUBPROCESS_TIMEOUT_SEC,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or proc.stdout.strip() or f"{script_name} exited {proc.returncode}")
    return proc.stdout.strip()


class AnalyzerHandler(BaseHTTPRequestHandler):
    def send_json(self, code, payload):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def send_file(self, file_path):
        data = file_path.read_bytes()
        ctype, _ = mimetypes.guess_type(str(file_path))
        self.send_response(200)
        self.send_header("Content-Type", ctype or "application/octet-stream")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def read_json_body(self):
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0 or length > 65536:
            raise ValueError("Invalid request body size")
        return json.loads(self.rfile.read(length).decode("utf-8"))

    def log_message(self, format, *args):
        # Keep daemon logs concise
        return

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        qs = urllib.parse.parse_qs(parsed.query)
        try:
            if parsed.path == "/api/overview":
                ledger = load_json(ROOT / "SETUP_LEDGER.json", {})
                tv_watchlist = load_json(ROOT / "TV_WATCHLIST.json", {})
                risk_doc = load_json(ROOT / "RISK_LOG.json", {"trades": []})
                scorecard = load_json(ROOT / "SCORECARD.json", {})
                self.send_json(200, {
                    "ledgerUpdated": ledger.get("last_updated"),
                    "contextWatch": ledger.get("context_watch", {}),
                    "setups": ledger.get("setups", {}),
                    "tvWatchlist": tv_watchlist.get("symbols", []),
                    "risk": riskGuard.status(),
                    "riskLine": riskGuard.line(),
                    "trades": risk_doc.get("trades", []),
                    "scorecardSummary": scorecard.get("summary", {}),
                    "movers": parse_movers_md(),
                    "signalHistory": load_signal_history()[:30],
                })
                return

            if parsed.path == "/api/analyze":
                raw_sym = (qs.get("symbol") or ["XRPUSDT"])[0]
                tf = (qs.get("tf") or ["15"])[0]
                sym = normalize_symbol(raw_sym)
                if not sym:
                    self.send_json(400, {"error": "Missing symbol"})
                    return
                res = analyze_symbol(sym, tf=tf, include_candles=True)
                res["risk"] = riskGuard.status()
                self.send_json(200, res)
                return

            if parsed.path == "/api/scan":
                extra_raw = (qs.get("symbols") or [""])[0]
                extra = [s for s in extra_raw.split(",") if s.strip()]
                self.send_json(200, scan_symbols(extra))
                return

            if parsed.path == "/api/movers":
                if (qs.get("refresh") or ["0"])[0] == "1":
                    run_node_script("scanMovers.mjs")
                self.send_json(200, parse_movers_md())
                return

            if parsed.path == "/api/pine":
                if (qs.get("rebuild") or ["0"])[0] == "1":
                    run_node_script("buildTradeMap.mjs")
                pine_path = ROOT / "AUTOTRADER_TRADE_MAP_TEMPLATE.pine"
                self.send_json(200, {"pine": pine_path.read_text(encoding="utf-8") if pine_path.exists() else ""})
                return

            if parsed.path == "/api/dashboard":
                scorecard = load_json(ROOT / "SCORECARD.json", {})
                ledger = load_json(ROOT / "SETUP_LEDGER.json", {})
                risk_doc = load_json(ROOT / "RISK_LOG.json", {"trades": []})
                self.send_json(200, {
                    "scorecard": {
                        "last_updated": scorecard.get("last_updated"),
                        "summary": scorecard.get("summary", {}),
                        "records": list(reversed(scorecard.get("records", []))),
                    },
                    "journal": list(reversed(ledger.get("journal", []))),
                    "trades": risk_doc.get("trades", []),
                    "risk": riskGuard.status(),
                    "signalHistory": load_signal_history()[:30],
                    "backtests": {
                        "oos": read_text_safe(ROOT / "backtests" / "2026-11-16-oos" / "results.txt"),
                        "edgeDecay": read_text_safe(ROOT / "backtests" / "2026-11-17-edge-decay" / "results.txt"),
                    },
                })
                return

            if parsed.path.startswith("/api/"):
                self.send_json(404, {"error": "Not found"})
                return

            if not WEB_DIST.exists():
                self.send_json(503, {"error": "Frontend not built yet. Run npm run build in app/web."})
                return

            rel = parsed.path.lstrip("/") or "index.html"
            candidate = (WEB_DIST / rel).resolve()
            if not str(candidate).startswith(str(WEB_DIST.resolve())) or not candidate.is_file():
                candidate = WEB_DIST / "index.html"
            self.send_file(candidate)
        except Exception as exc:
            self.send_json(500, {"error": str(exc)})

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        try:
            body = self.read_json_body()
            if parsed.path == "/api/risk/open":
                coin = riskGuard.normalize_coin(str(body.get("coin", "")))
                trade_type = str(body.get("type", "")).strip().lower()
                if trade_type not in riskGuard.RISK_PCT:
                    raise ValueError(f"type must be one of {list(riskGuard.RISK_PCT)}")
                entry = float(body["entry"])
                stop = float(body["stop"])
                risk_pct = float(body["risk_pct"]) if body.get("risk_pct") is not None else riskGuard.RISK_PCT[trade_type]
                with RISK_LOCK:
                    doc = riskGuard.load_doc()
                    doc["trades"].append({
                        "coin": coin,
                        "type": trade_type,
                        "opened": riskGuard.utc_now_iso(),
                        "entry": entry,
                        "stop": stop,
                        "risk_pct": risk_pct,
                        "closed": None,
                        "r": None,
                    })
                    riskGuard.save_doc(doc)
                    s = riskGuard.status()
                self.send_json(200, {
                    "risk": s,
                    "riskLine": riskGuard.line(s),
                    "sizing": riskGuard.size_line(trade_type, entry, stop),
                    "trades": doc["trades"],
                })
                return

            if parsed.path == "/api/risk/close":
                coin = riskGuard.normalize_coin(str(body.get("coin", "")))
                r_val = float(body["r"])
                fill_price = float(body["fill_price"]) if body.get("fill_price") not in (None, "") else None
                with RISK_LOCK:
                    doc = riskGuard.load_doc()
                    match = None
                    for t in reversed(doc["trades"]):
                        if not t.get("closed") and riskGuard.normalize_coin(t.get("coin", "")) == coin:
                            match = t
                            break
                    if match is None:
                        raise ValueError(f"No open trade found for {coin}")
                    match["closed"] = riskGuard.utc_now_iso()
                    match["r"] = r_val
                    if fill_price is not None:
                        match["fill_price"] = fill_price
                    riskGuard.save_doc(doc)
                    s = riskGuard.status()
                self.send_json(200, {
                    "risk": s,
                    "riskLine": riskGuard.line(s),
                    "trades": doc["trades"],
                })
                return

            self.send_json(404, {"error": "Not found"})
        except ValueError as exc:
            self.send_json(400, {"error": str(exc)})
        except Exception as exc:
            self.send_json(500, {"error": str(exc)})


def main():
    server = ThreadingHTTPServer((HOST, PORT), AnalyzerHandler)
    print(f"AutoTrader Analyzer listening on http://{HOST}:{PORT}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
