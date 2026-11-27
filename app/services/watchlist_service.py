"""Live 24h quotes for the ledger and synced watchlist coins."""
import strategyBacktest as sb

from services.config import ROOT
from services.history_service import load_json
from services.movers_service import normalize_symbol

TICKERS_URL = "https://api.bybit.com/v5/market/tickers?category=linear"
TICKERS_RETRIES = 2


def watchlist_symbols():
    ledger = load_json(ROOT / "SETUP_LEDGER.json", {}).get("setups", {})
    synced = load_json(ROOT / "TV_WATCHLIST.json", {}).get("symbols", [])
    return {normalize_symbol(raw) for raw in [*ledger, *synced]}


def quote_row(ticker):
    return {
        "ticker": f"{ticker['symbol']}.P",
        "symbol": ticker["symbol"],
        "pct": round(float(ticker["price24hPcnt"]) * 100, 2),
        "turnoverM": round(float(ticker["turnover24h"]) / 1e6, 1),
        "price": float(ticker["lastPrice"]),
    }


def watchlist_quotes():
    payload = sb.request_json(TICKERS_URL, retries=TICKERS_RETRIES)
    if payload.get("retCode") != 0:
        raise RuntimeError(f"Bybit tickers error: {payload.get('retMsg')}")
    wanted = watchlist_symbols()
    return [quote_row(item) for item in payload["result"]["list"] if item["symbol"] in wanted]
