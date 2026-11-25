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
VARIANTS = {
 "A current rule (counter-trend blocked, 1D short gate)": dict(short_gates=True, allow_counter_trend=False),
 "B counter-trend allowed, 1D short gate kept":           dict(short_gates=True, allow_counter_trend=True),
 "C counter-trend allowed, no short gates":               dict(short_gates=False, allow_counter_trend=True),
}
res = {k: [] for k in VARIANTS}   # (symbol, trade, trend)
for sym in SYMS:
    try:
        five = sb.fetch_5m(sym, sb.ms(sb.WARMUP_START), sb.ms(sb.TEST_END), DATA / f"{sym}_5m.json.gz")
    except Exception as e:
        print(sym, "DATA ERROR", e, flush=True); continue
    if len(five) < 30000: print(sym, "short data", flush=True); continue
    frames = {"5": five}
    for iv in ("15","60","240","D"): frames[iv] = sb.aggregate(five, iv)
    st4 = sb.StructureLookup(frames["240"], "240")
    for name, kw in VARIANTS.items():
        trades = v3.run_scalp_v3(sym, frames, 0.14, time_stop=True, time_stop_candles=72, time_stop_min_r=-0.3, **kw)
        for t in trades:
            if t.outcome == "OPEN": continue
            b = st4.at(t.signal_t)
            trend = "range" if b == "range" else ("with" if (b == "bullish") == (t.direction == "long") else "counter")
            res[name].append((sym, t, trend))
    print(sym, "done", flush=True)

def stat(rows):
    ts = [t for _, t, _ in rows]
    if not ts: return "n=   0"
    n, a, w, tot, _ = v3.stats(ts)
    return f"n={n:4} win={w:5.1f}% avgR={a:7.3f} totalR={tot:8.2f}"
def month(t): return dt.datetime.fromtimestamp(t.entry_t/1000, sb.UTC).month
for sets_name, syms in (("ALL coins", set(SYMS)), ("current ledger 16", set(CURRENT)), ("original 17", set(sb.unique_symbols()))):
    print(f"\n===== {sets_name} =====")
    for name in VARIANTS:
        rows = [r for r in res[name] if r[0] in syms]
        print(f"\n{name}\n  all     {stat(rows)}")
        for trend in ("with", "range", "counter"):
            sel = [r for r in rows if r[2] == trend]
            print(f"  {trend:7} {stat(sel)}   long {stat([r for r in sel if r[1].direction=='long'])[:44]}  short {stat([r for r in sel if r[1].direction=='short'])[:44]}")
        print("  Aug-Sep", stat([r for r in rows if month(r[1]) in (8,9)]), "| Oct-Nov", stat([r for r in rows if month(r[1]) in (10,11)]))
