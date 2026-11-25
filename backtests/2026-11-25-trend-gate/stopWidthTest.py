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
CAPS = [None, 5.0, 4.0, 3.0, 2.5, 2.0, 1.5]
res = {c: [] for c in CAPS}   # (symbol, trade)
for sym in SYMS:
    try:
        five = sb.fetch_5m(sym, sb.ms(sb.WARMUP_START), sb.ms(sb.TEST_END), DATA / f"{sym}_5m.json.gz")
    except Exception as e:
        print(sym, "DATA ERROR", e, flush=True); continue
    if len(five) < 30000: print(sym, "short data", flush=True); continue
    frames = {"5": five}
    for iv in ("15","60","240","D"): frames[iv] = sb.aggregate(five, iv)
    for cap in CAPS:
        trades = v3.run_scalp_v3(sym, frames, 0.14, short_gates=True, allow_counter_trend=True, time_stop=True,
                                 time_stop_candles=72, time_stop_min_r=-0.3, max_stop_pct=cap)
        res[cap] += [(sym, t) for t in trades if t.outcome != "OPEN"]
    print(sym, "done", flush=True)

def width(t): return abs(t.entry - t.stop) / t.entry * 100
def stat(rows):
    ts = [t for _, t in rows]
    if not ts: return "n=   0"
    n, a, w, tot, _ = v3.stats(ts)
    return f"n={n:4} win={w:5.1f}% avgR={a:7.3f} totalR={tot:8.2f}"
SETS = (("ALL coins", set(SYMS)), ("current ledger 16", set(CURRENT)), ("original 17", set(sb.unique_symbols())))
for sets_name, syms in SETS:
    print(f"\n===== {sets_name}: in-engine max stop width =====")
    for cap in CAPS:
        rows = [r for r in res[cap] if r[0] in syms]
        print(f"  cap {str(cap):>5}%  {stat(rows)}  median width {sorted(width(t) for _, t in rows)[len(rows)//2]:.2f}%" if rows else f"  cap {cap}  none")
    print(f"\n  buckets of the uncapped trades by stop width ({sets_name})")
    rows = [r for r in res[None] if r[0] in syms]
    edges = [0, 1.0, 1.5, 2.0, 3.0, 5.0, 100]
    for lo, hi in zip(edges, edges[1:]):
        sel = [r for r in rows if lo <= width(r[1]) < hi]
        print(f"  {lo:>4}-{hi:<5}% {stat(sel)}")
