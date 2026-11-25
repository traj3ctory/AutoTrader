"""Indicator context (EMA, structure, ATR, VWAP) shared by every verdict builder."""
import apiAnalyze as live
import strategyBacktest as sb


def _last_cross(c5, e9, e20, i):
    for j in range(i, 0, -1):
        if None in (e9[j], e20[j], e9[j - 1], e20[j - 1]):
            break
        if (e9[j - 1] <= e20[j - 1]) != (e9[j] <= e20[j]):
            flip_dir = "BULLISH" if e9[j] > e20[j] else "BEARISH"
            closed_utc = f"{live.hhmm(c5[j].t + live.FIVE_MS)} UTC"
            ago = i - j
            return {
                "direction": flip_dir,
                "closedAtUtc": closed_utc,
                "candlesAgo": ago,
                "summary": f"{flip_dir} {closed_utc} ({ago}c ago)",
            }
    return {"direction": None, "closedAtUtc": None, "candlesAgo": None, "summary": "none"}


def build_context(frames):
    c5 = frames["5"]
    i = len(c5) - 1
    price, now_t = c5[i].c, c5[i].t
    closes5 = [c.c for c in c5]
    e9, e20 = sb.ema(closes5, 9), sb.ema(closes5, 20)
    bull_slope = e9[i] > e9[i - 1] and e20[i] > e20[i - 1]
    bear_slope = e9[i] < e9[i - 1] and e20[i] < e20[i - 1]
    return {
        "c5": c5,
        "i": i,
        "price": price,
        "now_t": now_t,
        "e9": e9,
        "e20": e20,
        "bias4h": sb.StructureLookup(frames["240"], "240").at(now_t),
        "bias1d": sb.StructureLookup(frames["D"], "D").at(now_t),
        "atr_now": sb.SeriesLookup(frames["240"], "240", sb.atr(frames["240"])).at(now_t),
        "vwap": sb.daily_vwap(c5)[i],
        "bull_cross": e9[i - 1] <= e20[i - 1] and e9[i] > e20[i],
        "bear_cross": e9[i - 1] >= e20[i - 1] and e9[i] < e20[i],
        "bull_slope": bull_slope,
        "bear_slope": bear_slope,
        "order": "BULL-ordered (9 above 20)" if e9[i] > e20[i] else "BEAR-ordered (9 below 20)",
        "slope": "UP" if bull_slope else "DOWN" if bear_slope else "MIXED",
        "last_cross": _last_cross(c5, e9, e20, i),
    }
