"""Signal history persistence and outcome tracking service."""
import datetime as dt
import json
import threading

SIGNAL_LOCK = threading.Lock()
MAX_SIGNAL_HISTORY = 100
MODE_RESULT_KEYS = {"Scalp Zone": "scalpZone", "Scalp EMA": "scalp", "Intraday": "intraday"}


def load_json(path, fallback):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return fallback


def parse_iso_ms(iso_str):
    if not iso_str:
        return 0
    try:
        return int(dt.datetime.fromisoformat(iso_str.replace("Z", "+00:00")).timestamp() * 1000)
    except Exception:
        return 0


def load_signal_history(path):
    doc = load_json(path, {"version": 1, "signals": []})
    items = doc.get("signals", [])
    return items if isinstance(items, list) else []


def record_signal_history(path, tradeable_items, scanned_at_utc, by_symbol):
    with SIGNAL_LOCK:
        doc = load_json(path, {"version": 1, "signals": []})
        existing = doc.get("signals", [])
        if not isinstance(existing, list):
            existing = []
        active_by_pair = {(item["symbol"], item["mode"]): item for item in tradeable_items}
        handled_pairs = set()
        changed = False
        seen_ids = set()

        for entry in existing:
            if not isinstance(entry, dict):
                continue
            seen_ids.add(entry.get("id"))
            if entry.get("outcome") not in (None, "OPEN"):
                continue
            pair = (entry.get("symbol"), entry.get("mode"))
            if pair in active_by_pair:
                live_item = active_by_pair[pair]
                handled_pairs.add(pair)
                next_status = live_item.get("status", "VALID")
                if entry.get("status") != next_status or entry.get("summary") != live_item["summary"]:
                    entry["status"] = next_status
                    entry["summary"] = live_item["summary"]
                    entry["copyText"] = live_item["copyText"]
                    changed = True
                if entry.get("outcome") is None:
                    entry["outcome"] = "OPEN"
                    changed = True
            elif entry.get("symbol") in by_symbol:
                res = by_symbol[entry["symbol"]]
                mode_key = MODE_RESULT_KEYS.get(entry.get("mode", ""))
                mode_res = res.get(mode_key) if mode_key else None
                if mode_res and mode_res.get("verdictKind") == "ENGINE_IN_TRADE":
                    if entry.get("status") != "ENGINE_IN_TRADE" or entry.get("summary") != mode_res["verdictText"]:
                        entry["status"] = "ENGINE_IN_TRADE"
                        entry["summary"] = mode_res["verdictText"]
                        entry["copyText"] = res["copyText"]
                        changed = True
                    continue
                last_trade = mode_res["replay"].get("lastTrade") if mode_res else None
                seen_ms = parse_iso_ms(entry.get("seenAtUtc", ""))
                if last_trade and int(last_trade.get("exitMs") or 0) >= seen_ms:
                    net_r = float(last_trade["netR"])
                    entry["outcome"] = "WIN" if net_r > 0 else "LOSS" if net_r < 0 else "BE"
                    entry["netR"] = net_r
                    entry["closedAtUtc"] = last_trade.get("exitUtc")
                else:
                    entry["outcome"] = "EXPIRED"
                entry["status"] = entry["outcome"]
                changed = True

        added = []
        for item in tradeable_items:
            pair = (item["symbol"], item["mode"])
            if pair in handled_pairs:
                continue
            pos = (item.get("data") or {}).get("position") or {}
            pend = (item.get("data") or {}).get("pending") or {}
            stamp = pos.get("closedAtUtc") or pos.get("entryAtUtc") or pend.get("confirmation") or item["summary"][:64]
            sig_id = f"{item['symbol']}:{item['mode']}:{stamp}"
            if sig_id in seen_ids:
                continue
            seen_ids.add(sig_id)
            added.append({
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
            })
        if added or changed:
            merged = (added + existing)[:MAX_SIGNAL_HISTORY]
            path.write_text(json.dumps({"version": 1, "signals": merged}, indent=2) + "\n", encoding="utf-8")
            return merged
        return existing
