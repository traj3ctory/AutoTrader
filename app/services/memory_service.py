"""Ledger write-back and scorecard persistence service."""
import datetime as dt
import json
import threading

from services.analysis_service import analyze_symbol
from services.config import ROOT, SCRIPTS_DIR
from services.history_service import load_json
from services.movers_service import normalize_symbol, run_node_script
from services.trade_tier import classify_signal

LEDGER_LOCK = threading.Lock()
SCORECARD_LOCK = threading.Lock()


def _utc_now_iso():
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _build_ledger_record(sym, res, now_iso, existing=None):
    ticker = f"{sym}.P"
    prev = dict(existing) if isinstance(existing, dict) else {}
    sc_pos = res["scalp"].get("position") if res["scalp"]["tradeable"] else None
    in_pend = res["intraday"].get("pending") if res["intraday"]["tradeable"] else None
    active = sc_pos or in_pend
    tier = classify_signal(res=res, mode_data=res["scalp"] if sc_pos else res["intraday"], symbol=sym, majors={}) if active else None
    vetoed = bool(tier and tier["zoneVeto"])
    if vetoed:
        active = None
    trade_type = "Scalp" if sc_pos else "Intraday" if in_pend else prev.get("trade_type", "Scalp")

    target_levels = []
    if active:
        side = "Long" if active["direction"] == "long" else "Short"
        target_levels = active.get("targets", [])
        tps = [t["price"] for t in target_levels] or [active["target"]]
        entry_val = active["entry"]
        sl_val = active["stop"]
        rr1 = active["rr"]
        rating = "Conditional Trade - Reduced Size" if tier["lowerTier"] else "Clean Trade"
        state = f"{(res['scalp'] if sc_pos else res['intraday'])['verdictKind']} {side.upper()}"
        proposed = side
        action = "TRADE"
    else:
        tps, entry_val, sl_val, rr1 = [], None, None, None
        side = "Wait"
        rating = "Watch Only"
        state = f"NO SIGNAL; 4H {res['structure4h'].upper()} / 1D {res['structure1d'].upper()}"
        proposed = "Proposed Wait / No Trade"
        action = "WAIT - no valid engine signal."
        if vetoed:
            state = f"WATCH ONLY; {tier['zoneVeto']}"
            action = "WAIT - engine signal capped by the 4H zone veto."

    near_s = res["intraday"]["short"].get("nearestZone")
    near_l = res["intraday"]["long"].get("nearestZone")
    watch = prev.get("watch_zone") or (
        {"low": near_s["low"], "high": near_s["high"], "label": "SUPPLY / WAIT TOUCH"}
        if near_s
        else {"low": near_l["low"], "high": near_l["high"], "label": "DEMAND / WAIT TOUCH"}
        if near_l
        else {"low": None, "high": None, "label": "REANALYZE ZONE"}
    )
    return {
        **prev,
        "coin": ticker,
        "exchange": prev.get("exchange", "BYBIT"),
        "trade_type": trade_type,
        "proposed_type": proposed,
        "bias": f"Price {res['price']}; 4H {res['structure4h']}, 1D {res['structure1d']}; {res['scalp']['verdictText']}",
        "setup_rating": rating,
        "setup_state": state,
        "position_status": prev.get("position_status", "NO POSITION"),
        "direction": side,
        "entry": {"low": entry_val, "high": entry_val, "basis": (res["scalp"] if sc_pos else res["intraday"])["verdictText"], "actual": None},
        "watch_zone": watch,
        "sl": sl_val,
        "tp": tps,
        "rr_tp1": rr1,
        "rr_tp2": target_levels[1]["rr"] if len(target_levels) > 1 else None,
        "final_action": action,
        "analyzed_at": now_iso,
    }


def sync_symbol_to_ledger(raw_symbol):
    sym = normalize_symbol(raw_symbol)
    if not sym:
        raise ValueError("Missing symbol")
    res = analyze_symbol(sym, tf="15", include_candles=False)
    now_iso = _utc_now_iso()
    ledger_path = ROOT / "SETUP_LEDGER.json"
    ticker = f"{sym}.P"
    with LEDGER_LOCK:
        ledger = load_json(ledger_path, {"version": 1, "setups": {}, "journal": []})
        setups = ledger.setdefault("setups", {})
        setups[ticker] = _build_ledger_record(sym, res, now_iso, setups.get(ticker))
        ledger["last_updated"] = now_iso
        ledger_path.write_text(json.dumps(ledger, indent=2) + "\n", encoding="utf-8")
    run_node_script(ROOT, SCRIPTS_DIR, "buildTradeMap.mjs")
    return {"ok": True, "ticker": ticker, "ledgerUpdated": now_iso}


def append_scorecard_close(trade_record, r_val):
    sc_path = ROOT / "SCORECARD.json"
    today_str = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d")
    ticker = trade_record.get("coin", "")
    result_label = "Win" if r_val > 0 else "Loss" if r_val < 0 else "Breakeven"
    direction = "Long" if trade_record.get("entry", 0) > trade_record.get("stop", 0) else "Short"
    entry = {
        "id": f"{today_str}-{ticker}-{int(dt.datetime.now(dt.timezone.utc).timestamp())}",
        "date": today_str,
        "coin": ticker,
        "exchange": "BYBIT",
        "trade_type": str(trade_record.get("type", "scalp")).capitalize(),
        "direction": direction,
        "setup_type": "Risk Guard Logged Trade",
        "setup_rating": "Taken",
        "final_action": "CLOSED",
        "planned_entry": trade_record.get("entry"),
        "planned_sl": trade_record.get("stop"),
        "planned_tp": [trade_record["target"]] if trade_record.get("target") is not None else [],
        "trade_taken": True,
        "trade_result": f"{result_label} ({r_val:+.2f}R)",
        "outcome": result_label,
        "realized_r": r_val,
    }
    with SCORECARD_LOCK:
        doc = load_json(sc_path, {"version": 1, "summary": {}, "records": []})
        records = doc.setdefault("records", [])
        records.append(entry)
        summary = doc.setdefault("summary", {})
        summary["reviewed_setups"] = int(summary.get("reviewed_setups", 0)) + 1
        summary["trades_taken"] = int(summary.get("trades_taken", 0)) + 1
        if r_val > 0:
            summary["trade_wins"] = int(summary.get("trade_wins", 0)) + 1
        elif r_val < 0:
            summary["trade_losses"] = int(summary.get("trade_losses", 0)) + 1
        doc["last_updated"] = today_str
        sc_path.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
