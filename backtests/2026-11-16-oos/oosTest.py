#!/usr/bin/env python3
# Out-of-sample re-run of the v4 scalp and intraday engines on 2026-08-01 -> 2026-11-15.
import datetime as dt
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "scripts"))
import strategyBacktest as sb  # noqa: E402
import scalpBacktestV3 as v3  # noqa: E402

sb.TEST_START = dt.datetime(2026, 8, 1, tzinfo=sb.UTC)
sb.TEST_END = dt.datetime(2026, 11, 16, tzinfo=sb.UTC) - dt.timedelta(milliseconds=1)
sb.WARMUP_START = sb.TEST_START - dt.timedelta(days=61)

ORIGINAL = sb.unique_symbols()
CURRENT = ["XRPUSDT", "HYPEUSDT", "DOGEUSDT", "ZECUSDT", "AVAXUSDT", "JTOUSDT", "SOLUSDT", "AAVEUSDT",
           "ALGOUSDT", "AEROUSDT", "BROCCOLIUSDT", "BCHUSDT", "XPLUSDT", "ZROUSDT", "ARKUSDT", "LYNUSDT"]


def line(label, trades):
    done = [t for t in trades if t.outcome != "OPEN"]
    n, a, w, tot, _ = v3.stats(done)
    longs = [t for t in done if t.direction == "long"]
    shorts = [t for t in done if t.direction == "short"]
    nl, al, *_ = v3.stats(longs)
    ns, as_, *_ = v3.stats(shorts)
    return (f"{label:44} n={n:4} win={w:5.1f}% avgR={a:7.3f} totalR={tot:8.2f}   "
            f"longs n={nl:<4} avgR={al:7.3f}   shorts n={ns:<4} avgR={as_:7.3f}")


def main():
    out = {"scalp": {}, "intraday0": {}, "intraday14": {}}
    for symbol in dict.fromkeys(ORIGINAL + CURRENT):
        try:
            five = sb.fetch_5m(symbol, sb.ms(sb.WARMUP_START), sb.ms(sb.TEST_END), HERE / "data" / f"{symbol}_5m.json.gz")
        except Exception as exc:
            print(f"{symbol}: DATA ERROR {exc}", flush=True)
            continue
        if len(five) < 30000:
            print(f"{symbol}: only {len(five)} candles, skipped", flush=True)
            continue
        frames = {"5": five}
        for interval in ("15", "60", "240", "D"):
            frames[interval] = sb.aggregate(five, interval)
        out["scalp"][symbol] = v3.run_scalp_v3(symbol, frames, 0.14, short_gates=True, time_stop=True,
                                               time_stop_candles=72, time_stop_min_r=-0.3)
        out["intraday0"][symbol] = sb.run_intraday(symbol, frames, 0.0)
        out["intraday14"][symbol] = sb.run_intraday(symbol, frames, 0.14)
        print(f"{symbol}: scalp={len(out['scalp'][symbol])} intraday={len(out['intraday0'][symbol])}", flush=True)

    rows = [f"Window: {sb.TEST_START.date()} -> {sb.TEST_END.date()} (out-of-sample, rules frozen 2026-08-26)", ""]
    for name, symbols in (("original 17", ORIGINAL), ("current ledger 16", CURRENT)):
        for key, label in (("scalp", "Scalp v4, cost 0.14%"), ("intraday0", "Intraday, cost 0"),
                           ("intraday14", "Intraday, cost 0.14%")):
            trades = [t for s in symbols for t in out[key].get(s, [])]
            rows.append(line(f"{label} [{name}]", trades))
        rows.append("")
    rows.append("Per-month, scalp v4, all symbols:")
    every = [t for ts in out["scalp"].values() for t in ts if t.outcome != "OPEN"]
    for month in (8, 9, 10, 11):
        sel = [t for t in every if dt.datetime.fromtimestamp(t.entry_t / 1000, sb.UTC).month == month]
        rows.append(line(f"  2026-{month:02d}", sel))
    text = "\n".join(rows)
    (HERE / "results.txt").write_text(text + "\n")
    print(text)


if __name__ == "__main__":
    main()
