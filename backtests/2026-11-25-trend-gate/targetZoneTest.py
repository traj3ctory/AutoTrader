import datetime as dt, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import strategyBacktest as sb, scalpBacktestV3 as v3
sb.TEST_START = dt.datetime(2026, 8, 1, tzinfo=sb.UTC)
sb.TEST_END = dt.datetime(2026, 11, 16, tzinfo=sb.UTC) - dt.timedelta(milliseconds=1)
sb.WARMUP_START = sb.TEST_START - dt.timedelta(days=61)
DATA = ROOT / "backtests/2026-11-16-oos/data"
CURRENT = ["XRPUSDT","HYPEUSDT","DOGEUSDT","ZECUSDT","AVAXUSDT","JTOUSDT","SOLUSDT","AAVEUSDT","ALGOUSDT","AEROUSDT","BROCCOLIUSDT","BCHUSDT","XPLUSDT","ZROUSDT","ARKUSDT","LYNUSDT"]
SYMS = list(dict.fromkeys(sb.unique_symbols() + CURRENT))
VARIANTS = {"current": {}, "+4H 5m-close, 30d": {"target_htf_zones": True, "target_max_age_days": 30},
            "+4H 4H-close, 30d": {"target_htf_zones": True, "target_max_age_days": 30, "htf_close_invalidation": True},
            "+4H 4H-close, no cap": {"target_htf_zones": True, "htf_close_invalidation": True},
            "LIVE: 1H<=60d, 4H any age, 4H-close": {"target_htf_zones": True, "target_max_age_days": 60, "htf_close_invalidation": True}}
res = {k: [] for k in VARIANTS}
for sym in SYMS:
    try:
        five = sb.fetch_5m(sym, sb.ms(sb.WARMUP_START), sb.ms(sb.TEST_END), DATA / f"{sym}_5m.json.gz")
    except Exception as e:
        print(sym, "DATA ERROR", e, flush=True); continue
    if len(five) < 30000: continue
    frames = {"5": five}
    for iv in ("15","60","240","D"): frames[iv] = sb.aggregate(five, iv)
    for k, kw in VARIANTS.items():
        tr = v3.run_scalp_v3(sym, frames, 0.14, short_gates=True, allow_counter_trend=True, time_stop=True, time_stop_candles=72, time_stop_min_r=-0.3, **kw)
        res[k] += [t for t in tr if t.outcome != "OPEN"]
    print(sym, "done", flush=True)
for k, ts in res.items():
    n, a, w, tot, _ = v3.stats(ts)
    med = sorted(t.planned_rr for t in ts)[len(ts)//2] if ts else 0
    two = sum(1 for t in ts if abs(t.planned_rr - 2.0) < 1e-9)
    print(f"2R-planned={two:4} {k:36} n={n:4} win={w:5.1f}% avgR={a:7.3f} totalR={tot:8.2f} medianTargetR={med:.2f}")
