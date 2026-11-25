"""Candle series with EMA overlays for the chart."""
import strategyBacktest as sb
from services.config import CANDLE_LIMIT


def build_candles(frames, tf):
    tf_candles = frames[tf]
    closes = [c.c for c in tf_candles]
    e9 = sb.ema(closes, 9)
    e20 = sb.ema(closes, 20)
    out = []
    for idx in range(max(0, len(tf_candles) - CANDLE_LIMIT), len(tf_candles)):
        c = tf_candles[idx]
        out.append({
            "time": int(c.t // 1000),
            "open": c.o,
            "high": c.h,
            "low": c.l,
            "close": c.c,
            "ema9": round(e9[idx], 8) if e9[idx] is not None else None,
            "ema20": round(e20[idx], 8) if e20[idx] is not None else None,
        })
    return out
