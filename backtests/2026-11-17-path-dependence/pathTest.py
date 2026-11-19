#!/usr/bin/env python3
# Measures how much the scalp engine's signals depend on where the replay starts, and whether the unstable ones are worth taking.
import datetime as dt
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import strategyBacktest as sb  # noqa: E402
import scalpBacktestV3 as v3  # noqa: E402

DATA = ROOT / "backtests" / "2026-11-16-oos" / "data"
BASE = dt.datetime(2026, 8, 1, tzinfo=sb.UTC)
END = dt.datetime(2026, 11, 16, tzinfo=sb.UTC) - dt.timedelta(milliseconds=1)
COMPARE_FROM = BASE + dt.timedelta(days=35)
SHIFTS = [0, 3, 7, 14, 21, 28]
CORE = ["XRPUSDT", "HYPEUSDT", "DOGEUSDT", "JTOUSDT", "AVAXUSDT", "ZECUSDT", "SOLUSDT"]


def run(symbol, frames, shift):
    sb.TEST_START = BASE + dt.timedelta(days=shift)
    sb.TEST_END = END
    done = v3.run_scalp_v3(symbol, frames, 0.14, short_gates=True, time_stop=True, time_stop_candles=72, time_stop_min_r=-0.3)
    floor = sb.ms(COMPARE_FROM)
    return {t.signal_t: t for t in done if t.outcome != "OPEN" and t.signal_t >= floor}


def stats(trades):
    rs = [t.net_r for t in trades]
    if not rs:
        return "n=   0"
    return f"n={len(rs):4} win={sum(r > 0 for r in rs) / len(rs) * 100:5.1f}% avgR={sum(rs) / len(rs):7.3f} totalR={sum(rs):8.2f}"


def main():
    v3.DATA_DIR = DATA
    out = []
    for label, symbols in (("core 6 + SOL", CORE), ("all coins with data", sorted(p.name.split("_")[0] for p in DATA.glob("*_5m.json.gz")))):
        runs = {s: {} for s in SHIFTS}
        for symbol in symbols:
            if not (DATA / f"{symbol}_5m.json.gz").exists():
                continue
            frames = v3.load_frames(symbol)
            for shift in SHIFTS:
                for t_sig, trade in run(symbol, frames, shift).items():
                    runs[shift][(symbol, t_sig)] = trade
        out.append(f"== {label}: signals from {COMPARE_FROM.date()} to {END.date()}, replay start shifted 0-28 days from {BASE.date()}")
        base = set(runs[0])
        for shift in SHIFTS:
            keys = set(runs[shift])
            out.append(f"  start +{shift:2}d: {len(keys):3} signals, {len(keys & base):3} shared with +0d, {len(keys - base):3} extra, {len(base - keys):3} missing")
        union = set().union(*(set(r) for r in runs.values()))
        stable = {k for k in union if all(k in runs[s] for s in SHIFTS)}
        pick = lambda keys: [next(runs[s][k] for s in SHIFTS if k in runs[s]) for k in keys]
        out.append(f"  union {len(union)} signals; present in all 6 starts: {len(stable)} ({len(stable) / len(union) * 100:.0f}%)")
        out.append(f"    stable signals   {stats(pick(stable))}")
        out.append(f"    unstable signals {stats(pick(union - stable))}")
        for shift in (0, 14, 28):
            out.append(f"    all signals, start +{shift:2}d: {stats(list(runs[shift].values()))}")
        out.append("")
    text = "\n".join(out)
    print(text)
    (HERE / "results.txt").write_text(text + "\n")


if __name__ == "__main__":
    main()
