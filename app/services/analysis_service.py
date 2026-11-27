"""Builds the full analyzer payload for one symbol."""
import apiAnalyze as live
import scalpBacktestV3 as v3
import strategyBacktest as sb
from services.analysis_context import build_context
from services.candles_output import build_candles
from services.config import ENGINE_LOCK, VALID_TFS
from services.formatters import build_copy_text
from services.nearby_zones import engine_targets, nearby_zones
from services.intraday_verdict import build_intraday, last_closed_15m_label
from services.scalp_ema_verdict import build_scalp_ema
from services.scalp_zone_engine import run_scalp_zone
from services.scalp_zone_verdict import build_scalp_zone
from services.price_format import round_price
from services.zone_proximity import detect_4h_zone_proximity


def _run_engines(symbol, five):
    frames = live.build_frames(five)
    span_days, replay_days = live.set_window(five)
    zone_state, scalp_state, intraday_state = {}, {}, {}
    zone_trades = run_scalp_zone(symbol, frames, live.COST_PCT, state_out=zone_state)
    scalp_trades = v3.run_scalp_v3(symbol, frames, live.COST_PCT, state_out=scalp_state, **live.LIVE_SCALP_KWARGS)
    scalp_state["target_zones"] = live.live_target_zones(scalp_state, frames["5"][-1].t)
    intraday_trades = sb.run_intraday(symbol, frames, live.COST_PCT, state_out=intraday_state)
    return {
        "frames": frames,
        "span_days": span_days,
        "replay_days": replay_days,
        "zone": (zone_state, zone_trades),
        "scalp": (scalp_state, scalp_trades),
        "intraday": (intraday_state, intraday_trades),
    }


def analyze_symbol(symbol, tf="15", include_candles=True):
    if tf not in VALID_TFS:
        tf = "15"
    # Candles load outside the lock so one coin's download never stalls another request.
    five = live.load_history(symbol)
    with ENGINE_LOCK:
        run = _run_engines(symbol, five)

    frames, replay_days = run["frames"], run["replay_days"]
    ctx = build_context(frames)
    price, atr_now = ctx["price"], ctx["atr_now"]
    result = {
        "symbol": symbol,
        "ticker": f"{symbol}.P",
        "tf": tf,
        "price": round_price(price),
        "historyDays": round(run["span_days"]),
        "lastClosed5mUtc": f"{live.hhmm(ctx['now_t'] + live.FIVE_MS)} UTC",
        "lastClosed15mUtc": last_closed_15m_label(frames),
        "structure4h": ctx["bias4h"],
        "structure1d": ctx["bias1d"],
        "zone4hBadge": detect_4h_zone_proximity(frames["240"], price, atr_now, ctx["now_t"] + live.FIVE_MS),
        "atr4hPct": round((atr_now / price) * 100, 2) if atr_now and price else None,
        "vwap": round_price(ctx["vwap"]),
        "emaOrder": ctx["order"],
        "emaSlope": ctx["slope"],
        "lastCross": ctx["last_cross"],
        "scalpZone": build_scalp_zone(ctx, *run["zone"], replay_days),
        "scalp": build_scalp_ema(ctx, *run["scalp"], replay_days),
        "intraday": build_intraday(frames, *run["intraday"], replay_days),
        "candles": build_candles(frames, tf) if include_candles else [],
    }
    result["nearZones"] = {
        "scalp": nearby_zones(zones=run["scalp"][0]["target_zones"], price=price, target_prices=engine_targets(result["scalp"])),
        "intraday": nearby_zones(zones=run["intraday"][0]["active"], price=price, target_prices=engine_targets(result["intraday"])),
    }
    result["copyText"] = build_copy_text(result)
    return result
