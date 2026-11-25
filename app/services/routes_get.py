"""GET API routes. Each handler takes the parsed query dict and returns (status, payload)."""
import riskGuard
from services.analysis_service import analyze_symbol
from services.config import ROOT, SIGNAL_HISTORY_PATH, SIGNAL_HISTORY_VIEW
from services.history_service import load_json, load_signal_history
from services.movers_facade import parse_movers_md, refresh_movers_and_sync, run_node_script
from services.movers_service import normalize_symbol
from services.scan_service import scan_symbols

PINE_TEMPLATE = "AUTOTRADER_TRADE_MAP_TEMPLATE.pine"
BACKTEST_OOS = "backtests/2026-11-16-oos/results.txt"
BACKTEST_EDGE_DECAY = "backtests/2026-11-17-edge-decay/results.txt"


def _first(qs, key, default):
    return (qs.get(key) or [default])[0]


def read_text_safe(path):
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def overview(qs):
    ledger = load_json(ROOT / "SETUP_LEDGER.json", {})
    return 200, {
        "ledgerUpdated": ledger.get("last_updated"),
        "contextWatch": ledger.get("context_watch", {}),
        "setups": ledger.get("setups", {}),
        "tvWatchlist": load_json(ROOT / "TV_WATCHLIST.json", {}).get("symbols", []),
        "risk": riskGuard.status(),
        "riskLine": riskGuard.line(),
        "trades": load_json(ROOT / "RISK_LOG.json", {"trades": []}).get("trades", []),
        "scorecardSummary": load_json(ROOT / "SCORECARD.json", {}).get("summary", {}),
        "movers": parse_movers_md(),
        "signalHistory": load_signal_history(SIGNAL_HISTORY_PATH)[:SIGNAL_HISTORY_VIEW],
    }


def analyze(qs):
    sym = normalize_symbol(_first(qs, "symbol", "XRPUSDT"))
    if not sym:
        return 400, {"error": "Missing symbol"}
    res = analyze_symbol(sym, tf=_first(qs, "tf", "15"), include_candles=True)
    res["risk"] = riskGuard.status()
    return 200, res


def scan(qs):
    extra = [s for s in _first(qs, "symbols", "").split(",") if s.strip()]
    return 200, scan_symbols(extra)


def movers(qs):
    if _first(qs, "refresh", "0") == "1":
        return 200, refresh_movers_and_sync()
    return 200, parse_movers_md()


def pine(qs):
    if _first(qs, "rebuild", "0") == "1":
        run_node_script("buildTradeMap.mjs")
    pine_path = ROOT / PINE_TEMPLATE
    return 200, {"pine": pine_path.read_text(encoding="utf-8") if pine_path.exists() else ""}


def dashboard(qs):
    scorecard = load_json(ROOT / "SCORECARD.json", {})
    ledger = load_json(ROOT / "SETUP_LEDGER.json", {})
    return 200, {
        "scorecard": {
            "last_updated": scorecard.get("last_updated"),
            "summary": scorecard.get("summary", {}),
            "records": list(reversed(scorecard.get("records", []))),
        },
        "journal": list(reversed(ledger.get("journal", []))),
        "trades": load_json(ROOT / "RISK_LOG.json", {"trades": []}).get("trades", []),
        "risk": riskGuard.status(),
        "signalHistory": load_signal_history(SIGNAL_HISTORY_PATH)[:SIGNAL_HISTORY_VIEW],
        "backtests": {
            "oos": read_text_safe(ROOT / BACKTEST_OOS),
            "edgeDecay": read_text_safe(ROOT / BACKTEST_EDGE_DECAY),
        },
    }


GET_ROUTES = {
    "/api/overview": overview,
    "/api/analyze": analyze,
    "/api/scan": scan,
    "/api/movers": movers,
    "/api/pine": pine,
    "/api/dashboard": dashboard,
}
