"""Resolves a recorded signal against the candles that followed it."""
import datetime as dt
import re

from services.config import INTRADAY_PENDING_VALID_CANDLES

import apiAnalyze as live
import strategyBacktest as sb

INTRADAY_MODE = "Intraday"
# A legacy level printed to four decimals is only usable when the risk spans this many printed steps.
MIN_LEGACY_RISK_STEPS = 10
LEVEL_KEYS = ("direction", "entry", "stop", "target", "startMs")
LEGACY_LEVELS = re.compile(r"(?:entry|limit) ([\d.]+).*?SL ([\d.]+), TP ([\d.]+)")
LEGACY_SIDE = re.compile(r"\b(LONG|SHORT)\b")
LEGACY_FILLED = re.compile(r"filled (\d{2}-\d{2} \d{2}:\d{2}) UTC")
ID_STAMP = re.compile(r":(\d{2}-\d{2} \d{2}:\d{2}) UTC$")


def span_ms(mode):
    return sb.INTERVAL_MS["15" if mode == INTRADAY_MODE else "5"]


def window_ms(mode):
    candles = INTRADAY_PENDING_VALID_CANDLES if mode == INTRADAY_MODE else live.LATE_ENTRY_CANDLES
    return candles * span_ms(mode)


def signal_id(*, symbol, mode, payload):
    stamp = (payload or {}).get("closedAtUtc") or (payload or {}).get("signalAtUtc")
    return f"{symbol}:{mode}:{stamp}" if stamp else None


def levels_from_payload(payload):
    if not payload:
        return {}
    return {
        "direction": payload["direction"],
        "entry": payload["entry"],
        "stop": payload["stop"],
        "target": payload["target"],
        "startMs": payload["entryTimeSec"] * 1000,
    }


def mode_candles(*, five, mode):
    if mode != INTRADAY_MODE:
        return five
    closed_until = five[-1].t + sb.INTERVAL_MS["5"] if five else 0
    return [c for c in sb.aggregate(five, "15") if c.t + sb.INTERVAL_MS["15"] <= closed_until]


def _stamp_ms(stamp, seen):
    month = int(stamp[:2])
    year = seen.year - 1 if month > seen.month else seen.year
    parsed = dt.datetime.strptime(f"{year}-{stamp}", "%Y-%m-%d %H:%M")
    return int(parsed.replace(tzinfo=dt.timezone.utc).timestamp() * 1000)


def legacy_levels(*, record, candles):
    # Entries written before levels were stored carry them only inside the summary text and the id.
    summary = record.get("summary", "")
    found, side = LEGACY_LEVELS.search(summary), LEGACY_SIDE.search(summary)
    if not found or not side:
        return None
    entry, stop, target = (float(v) for v in found.groups())
    step = 10 ** -len(found.group(1).partition(".")[2])
    if abs(entry - stop) < MIN_LEGACY_RISK_STEPS * step:
        return None
    seen = dt.datetime.fromisoformat(record["seenAtUtc"].replace("Z", "+00:00"))
    levels = {"direction": side.group(1).lower(), "entry": entry, "stop": stop, "target": target}
    if record.get("mode") == INTRADAY_MODE:
        filled = LEGACY_FILLED.search(summary)
        start = _stamp_ms(filled.group(1), seen) if filled else int(seen.timestamp() * 1000)
        return {**levels, "startMs": start, "filled": bool(filled)}
    stamp = ID_STAMP.search(record.get("id", ""))
    if not stamp:
        return None
    start = _stamp_ms(stamp.group(1), seen)
    # The scalp entry is the signal candle's close; a mismatch means the text belongs to another signal.
    signal = next((c for c in candles if c.t == start - span_ms(record.get("mode"))), None)
    if signal is None or abs(signal.c - entry) > step:
        return None
    return {**levels, "startMs": start}


def walk_signal(*, record, candles):
    """Fill and SL/TP walk using the engines' order: stop first, and a stop before the fill cancels."""
    mode = record.get("mode")
    if not candles or candles[0].t > record["startMs"]:
        return None
    long = record["direction"] == "long"
    entry, stop, target = record["entry"], record["stop"], record["target"]
    risk = abs(entry - stop)
    if not risk:
        return None
    filled = record.get("filled", mode != INTRADAY_MODE)
    for candle in candles:
        if candle.t < record["startMs"]:
            continue
        exit_ms = candle.t + span_ms(mode)
        stop_hit = candle.l <= stop if long else candle.h >= stop
        if not filled:
            if stop_hit:
                return {"filled": False, "outcome": "EXPIRED", "netR": None, "exitMs": exit_ms}
            if not candle.l <= entry <= candle.h:
                continue
            filled = True
        target_hit = candle.h >= target if long else candle.l <= target
        if stop_hit or target_hit:
            gross = -1.0 if stop_hit else abs(target - entry) / risk
            net = round(gross - live.COST_PCT / 100 * entry / risk, 2)
            outcome = "WIN" if net > 0 else "LOSS" if net < 0 else "BE"
            return {"filled": True, "outcome": outcome, "netR": net, "exitMs": exit_ms}
    return {"filled": filled, "outcome": None}
