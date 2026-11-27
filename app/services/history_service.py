"""Signal history persistence and outcome tracking service."""
import datetime as dt
import json
import threading
import time

from services.history_outcome import (INTRADAY_MODE, LEVEL_KEYS, legacy_levels, levels_from_payload,
                                      load_candles, mode_candles, signal_id, walk_signal, window_ms)

import apiAnalyze as live

SIGNAL_LOCK = threading.Lock()
MAX_SIGNAL_HISTORY = 100
MODE_RESULT_KEYS = {"Scalp Zone": "scalpZone", "Scalp EMA": "scalp", INTRADAY_MODE: "intraday"}


def load_json(path, fallback):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return fallback


def load_signal_history(path):
    doc = load_json(path, {"version": 1, "signals": []})
    items = doc.get("signals", [])
    return items if isinstance(items, list) else []


def _is_open(entry):
    return isinstance(entry, dict) and entry.get("outcome") in (None, "OPEN")


def _needs_candles(entry):
    return _is_open(entry) or (isinstance(entry, dict) and any(key not in entry for key in LEVEL_KEYS))


def _fetch_candles(path, loader):
    # Fetched outside the history lock; a failed symbol simply stays open until the next scan.
    candles = {}
    for symbol in {e.get("symbol") for e in load_signal_history(path) if _needs_candles(e)}:
        try:
            candles[symbol] = loader(symbol)
        except Exception:
            continue
    return candles


def _ensure_levels(entry, five):
    # Returns the mode's candles once the entry carries usable levels; the outcome is left alone.
    if not five:
        return None
    candles = mode_candles(five=five, mode=entry.get("mode"))
    if any(key not in entry for key in LEVEL_KEYS):
        levels = legacy_levels(record=entry, candles=candles)
        if levels is None:
            return None
        entry.update(levels)
    return candles


def _resolve(entry, five):
    candles = _ensure_levels(entry, five)
    return None if candles is None else walk_signal(record=entry, candles=candles)


def _refresh_status(entry, *, live_item, res, result):
    if live_item:
        entry.update(status=live_item.get("status", "VALID"), summary=live_item["summary"],
                     copyText=live_item["copyText"])
        return
    mode = entry.get("mode")
    mode_res = (res or {}).get(MODE_RESULT_KEYS.get(mode, "")) or {}
    position = mode_res.get("position")
    if signal_id(symbol=entry.get("symbol"), mode=mode, payload=position) == entry.get("id"):
        entry.update(status="ENGINE_IN_TRADE", summary=mode_res["verdictText"], copyText=res["copyText"])
        return
    filled = result["filled"] if result else mode != INTRADAY_MODE
    expired = int(time.time() * 1000) - entry.get("startMs", 0) > window_ms(mode)
    if entry.get("status") in ("VALID", "LATE_ENTRY", "STALE_ORDER") and (res or expired):
        entry["status"] = "ENGINE_IN_TRADE" if filled else "STALE_ORDER"


def _update_open_entry(entry, *, live_item, res, five):
    result = _resolve(entry, five)
    if result and result["outcome"]:
        entry.update(outcome=result["outcome"], status=result["outcome"], netR=result["netR"],
                     closedAtUtc=f"{live.hhmm(result['exitMs'])} UTC")
        return
    entry["outcome"] = "OPEN"
    _refresh_status(entry, live_item=live_item, res=res, result=result)


def _item_payload(item):
    data = item.get("data") or {}
    return data.get("position") or data.get("pending")


def _new_entry(item, sig_id, scanned_at_utc):
    return {
        "id": sig_id,
        "seenAtUtc": scanned_at_utc,
        "symbol": item["symbol"],
        "mode": item["mode"],
        "status": item.get("status", "VALID"),
        "outcome": "OPEN",
        "netR": None,
        "closedAtUtc": None,
        "emaBadge": item.get("emaBadge"),
        "zone4hBadge": item.get("zone4hBadge"),
        "summary": item["summary"],
        "copyText": item["copyText"],
        **levels_from_payload(_item_payload(item)),
    }


def record_signal_history(path, tradeable_items, scanned_at_utc, by_symbol, loader=load_candles):
    candles = _fetch_candles(path, loader)
    items_by_id = {}
    for item in tradeable_items:
        sig_id = signal_id(symbol=item["symbol"], mode=item["mode"], payload=_item_payload(item))
        items_by_id[sig_id or f"{item['symbol']}:{item['mode']}:{item['summary'][:64]}"] = item
    with SIGNAL_LOCK:
        existing = load_signal_history(path)
        before = json.dumps(existing)
        for entry in existing:
            if _is_open(entry):
                symbol = entry.get("symbol")
                _update_open_entry(entry, live_item=items_by_id.get(entry.get("id")),
                                   res=by_symbol.get(symbol), five=candles.get(symbol))
            elif _needs_candles(entry):
                _ensure_levels(entry, candles.get(entry.get("symbol")))
        seen_ids = {entry.get("id") for entry in existing if isinstance(entry, dict)}
        added = [_new_entry(item, sig_id, scanned_at_utc)
                 for sig_id, item in items_by_id.items() if sig_id not in seen_ids]
        if not added and json.dumps(existing) == before:
            return existing
        merged = (added + existing)[:MAX_SIGNAL_HISTORY]
        path.write_text(json.dumps({"version": 1, "signals": merged}, indent=2) + "\n", encoding="utf-8")
        return merged
