"""POST risk-log routes. Each handler takes the JSON body and returns (status, payload)."""
import datetime as dt

import riskGuard
from services.config import RISK_LOCK
from services.memory_service import append_scorecard_close, sync_symbol_to_ledger


def _risk_response(state, doc, extra=None):
    payload = {"risk": state, "riskLine": riskGuard.line(state), "trades": doc["trades"]}
    if extra:
        payload.update(extra)
    return 200, payload


def open_trade(body):
    coin = riskGuard.normalize_coin(str(body.get("coin", "")))
    trade_type = str(body.get("type", "")).strip().lower()
    if trade_type not in riskGuard.RISK_PCT:
        raise ValueError(f"type must be one of {list(riskGuard.RISK_PCT)}")
    entry = round(float(body["entry"]), 4)
    stop = round(float(body["stop"]), 4)
    target = round(float(body["target"]), 4) if body.get("target") not in (None, "") else None
    risk_pct = float(body["risk_pct"]) if body.get("risk_pct") is not None else riskGuard.RISK_PCT[trade_type]
    with RISK_LOCK:
        doc = riskGuard.load_doc()
        doc["trades"].append({
            "coin": coin,
            "type": trade_type,
            "opened": riskGuard.utc_now_iso(),
            "entry": entry,
            "stop": stop,
            "target": target,
            "risk_pct": risk_pct,
            "closed": None,
            "r": None,
        })
        riskGuard.save_doc(doc)
        state = riskGuard.status()
    return _risk_response(state, doc, {"sizing": riskGuard.size_line(trade_type, entry, stop)})


def close_trade(body):
    coin = riskGuard.normalize_coin(str(body.get("coin", "")))
    r_val = float(body["r"])
    fill_price = float(body["fill_price"]) if body.get("fill_price") not in (None, "") else None
    with RISK_LOCK:
        doc = riskGuard.load_doc()
        match = next(
            (t for t in reversed(doc["trades"]) if not t.get("closed") and riskGuard.normalize_coin(t.get("coin", "")) == coin),
            None,
        )
        if match is None:
            raise ValueError(f"No open trade found for {coin}")
        match["closed"] = riskGuard.utc_now_iso()
        match["r"] = r_val
        if fill_price is not None:
            match["fill_price"] = fill_price
        riskGuard.save_doc(doc)
        append_scorecard_close(match, r_val)
        state = riskGuard.status()
    return _risk_response(state, doc)


def sync_ledger(body):
    symbol = str(body.get("symbol", "")).strip()
    return 200, sync_symbol_to_ledger(symbol)


def clear_history(body):
    with RISK_LOCK:
        doc = riskGuard.load_doc()
        today = dt.datetime.now(riskGuard.USER_TZ).date()
        doc["trades"] = [
            t for t in doc.get("trades", [])
            if not t.get("closed") or riskGuard.local_day(t["closed"]) == today
        ]
        riskGuard.save_doc(doc)
        state = riskGuard.status()
    return _risk_response(state, doc)


POST_ROUTES = {
    "/api/risk/open": open_trade,
    "/api/risk/close": close_trade,
    "/api/risk/clear": clear_history,
    "/api/ledger/sync": sync_ledger,
}
