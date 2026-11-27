"""Scans the core ledger, TV watchlist and extra symbols for fresh signals."""
import datetime as dt

import riskGuard
from services.analysis_service import analyze_symbol
from services.config import ROOT, SIGNAL_HISTORY_PATH, SIGNAL_HISTORY_VIEW, TV_EXTRA_LIMIT
from services.history_service import load_json, record_signal_history
from services.movers_service import normalize_symbol
from services.trade_tier import MAJOR_SYMBOLS, TREND_RANK, classify_signal, watch_reasons


def is_fresh_active(mode_data):
    # Only a signal still inside its tested entry window is actionable; an engine trade past it is a missed signal.
    return mode_data["verdictKind"] in ("VALID", "LATE_ENTRY")


def _tradeable_entry(*, sym, mode, data, res, tier, locked):
    reasons = watch_reasons(tier=tier, locked=locked)
    return {
        "watchOnly": bool(reasons),
        "watchReasons": reasons,
        "trend": tier["trend"],
        "lowerTier": tier["lowerTier"],
        "btcEth": tier["btcEth"],
        "symbol": sym,
        "mode": mode,
        "status": data["verdictKind"],
        "zone4hBadge": res.get("zone4hBadge"),
        "summary": data["verdictText"],
        "data": data,
        "copyText": res["copyText"],
    }


def _majors_structure(by_symbol):
    majors = {}
    for sym in MAJOR_SYMBOLS:
        res = by_symbol.get(sym)
        if res is None:
            try:
                res = analyze_symbol(sym, tf="15", include_candles=False)
            except Exception:
                continue
        majors[sym] = res["structure4h"]
    return majors


def _checked_entry(sym, res, is_active):
    return {
        "symbol": sym,
        "ticker": f"{sym}.P",
        "price": res["price"],
        "structure4h": res["structure4h"],
        "structure1d": res["structure1d"],
        "scalpZoneKind": res["scalpZone"]["verdictKind"],
        "scalpKind": res["scalp"]["verdictKind"],
        "intradayKind": res["intraday"]["verdictKind"],
        "tradeable": is_active,
        "copyText": res["copyText"],
    }


def _scan_universe(extra_symbols, ledger, tv_doc):
    symbols = [s.replace(".P", "") for s in ledger.get("setups", {})]
    active_tv = [normalize_symbol(r) for r in tv_doc.get("symbols", [])[:TV_EXTRA_LIMIT]]
    for sym in active_tv + [normalize_symbol(r) for r in extra_symbols]:
        if sym and sym not in symbols:
            symbols.append(sym)
    return symbols


def scan_symbols(extra_symbols):
    ledger = load_json(ROOT / "SETUP_LEDGER.json", {})
    tv_doc = load_json(ROOT / "TV_WATCHLIST.json", {})
    tradeable, checked, failed, by_symbol, fresh_signals = [], [], [], {}, []
    risk_state = riskGuard.status()
    locked = risk_state["locked"]
    for sym in _scan_universe(extra_symbols, ledger, tv_doc):
        try:
            res = analyze_symbol(sym, tf="15", include_candles=False)
            by_symbol[sym] = res
            fresh_signals += [
                (sym, label, res[key], res)
                for label, key in (("Scalp EMA", "scalp"), ("Intraday", "intraday"))
                if is_fresh_active(res[key])
            ]
        except Exception as exc:
            failed.append({"symbol": sym, "error": str(exc)})

    majors = _majors_structure(by_symbol) if fresh_signals else {}
    actionable = set()
    for sym, label, data, res in fresh_signals:
        tier = classify_signal(res=res, mode_data=data, symbol=sym, majors=majors)
        entry = _tradeable_entry(sym=sym, mode=label, data=data, res=res, tier=tier, locked=locked)
        tradeable.append(entry)
        if not entry["watchOnly"]:
            actionable.add(sym)
    tradeable.sort(key=lambda e: (e["watchOnly"], TREND_RANK[e["trend"]]))
    for sym, res in by_symbol.items():
        checked.append(_checked_entry(sym, res, sym in actionable))

    now_iso = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    history = record_signal_history(SIGNAL_HISTORY_PATH, tradeable, now_iso, by_symbol)
    return {
        "scannedAtUtc": now_iso,
        "tradeable": tradeable,
        "checked": checked,
        "failed": failed,
        "tvWatchlist": tv_doc.get("symbols", [])[:TV_EXTRA_LIMIT],
        "signalHistory": history[:SIGNAL_HISTORY_VIEW],
        "risk": risk_state,
    }
