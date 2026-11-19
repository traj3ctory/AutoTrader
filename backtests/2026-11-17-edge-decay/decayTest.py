#!/usr/bin/env python3
# Slices the v4 scalp trades by regime and trade features in both windows; only splits with the same sign in both count as evidence.
import datetime as dt
import sys
import time
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import strategyBacktest as sb  # noqa: E402
import scalpBacktestV3 as v3  # noqa: E402

WINDOWS = {
    "IS": (sb.TEST_START, sb.TEST_END, ROOT / "backtests" / "2026-07-31" / "data"),
    "OOS": (dt.datetime(2026, 8, 1, tzinfo=sb.UTC), dt.datetime(2026, 11, 16, tzinfo=sb.UTC) - dt.timedelta(milliseconds=1),
            ROOT / "backtests" / "2026-11-16-oos" / "data"),
}


def collect(start, end, data_dir):
    sb.TEST_START, sb.TEST_END = start, end
    v3.DATA_DIR = data_dir
    rows = []
    for path in sorted(data_dir.glob("*_5m.json.gz")):
        symbol = path.name.split("_")[0]
        frames = v3.load_frames(symbol)
        s4, s1 = sb.StructureLookup(frames["240"], "240"), sb.StructureLookup(frames["D"], "D")
        for t in v3.run_scalp_v3(symbol, frames, 0.14, short_gates=True, time_stop=True, time_stop_candles=72, time_stop_min_r=-0.3):
            if t.outcome == "OPEN":
                continue
            width = abs(t.entry - t.stop) / t.entry * 100
            rows.append({"r": t.net_r, "symbol": symbol, "dir": t.direction, "rr": t.planned_rr, "out": t.outcome,
                         "b4": s4.at(t.signal_t), "b1": s1.at(t.signal_t),
                         "stop": "tight <1.5%" if width < 1.5 else "mid 1.5-3%" if width < 3 else "wide >3%",
                         "hour": ("Asia 00-08" if (h := time.gmtime(t.signal_t / 1000).tm_hour) < 8 else "EU 08-16" if h < 16 else "US 16-24"),
                         "zone_tf": t.zone_tf})
    return rows


def agg(rows):
    n = len(rows)
    return (n, sum(r["r"] for r in rows) / n) if n else (0, 0.0)


def main():
    data = {k: collect(*v) for k, v in WINDOWS.items()}
    out = []
    for k, rows in data.items():
        n, a = agg(rows)
        out.append(f"{k}: n={n} avgR={a:.3f} win={sum(r['r'] > 0 for r in rows) / n * 100:.1f}% outcomes={dict(sorted(defaultdict(int, {o: sum(1 for r in rows if r['out'] == o) for o in {r['out'] for r in rows}}).items()))}")
    out.append("")
    out.append(f"{'slice':32} {'IS n':>5} {'IS avgR':>8} {'OOS n':>6} {'OOS avgR':>9}  verdict")
    for feat in ("dir", "rr", "b4", "b1", "stop", "hour", "zone_tf"):
        for val in sorted({r[feat] for rows in data.values() for r in rows}, key=str):
            (ni, ai), (no, ao) = (agg([r for r in data[w] if r[feat] == val]) for w in ("IS", "OOS"))
            if ni < 15 or no < 15:
                note = "small sample"
            elif ai < 0 and ao < 0:
                note = "NEGATIVE in both - candidate to gate"
            elif ai > 0.2 and ao > 0.2:
                note = "strong in both"
            elif (ai > 0) != (ao > 0):
                note = "sign flips - noise"
            else:
                note = ""
            out.append(f"{feat + '=' + str(val):32} {ni:5} {ai:8.3f} {no:6} {ao:9.3f}  {note}")
    out.append("")
    out.append("Per coin (OOS vs IS, coins with >=8 trades in each):")
    for sym in sorted({r["symbol"] for rows in data.values() for r in rows}):
        (ni, ai), (no, ao) = (agg([r for r in data[w] if r["symbol"] == sym]) for w in ("IS", "OOS"))
        if ni >= 8 and no >= 8:
            out.append(f"  {sym:14} IS n={ni:3} avgR={ai:7.3f}   OOS n={no:3} avgR={ao:7.3f}")
    text = "\n".join(out)
    print(text)
    (HERE / "results.txt").write_text(text + "\n")


if __name__ == "__main__":
    main()
