"""Compares zone definitions on the 27-coin out-of-sample set, scalp (live rules) and intraday, after costs."""
import datetime as dt
import inspect
import random
import statistics
import zoneVariants as zv
import strategyBacktest as sb
import scalpBacktestV3 as v3
import apiAnalyze as api

sb.TEST_START = dt.datetime(2026, 8, 1, tzinfo=sb.UTC)
sb.TEST_END = dt.datetime(2026, 11, 16, tzinfo=sb.UTC) - dt.timedelta(milliseconds=1)
sb.WARMUP_START = sb.TEST_START - dt.timedelta(days=61)
SPLIT_MS = sb.ms(dt.datetime(2026, 9, 23, tzinfo=sb.UTC))
DATA = zv.ROOT / "backtests/2026-11-16-oos/data"
EXTRA = ["XRPUSDT", "HYPEUSDT", "DOGEUSDT", "ZECUSDT", "AVAXUSDT", "JTOUSDT", "SOLUSDT", "AAVEUSDT", "ALGOUSDT",
         "AEROUSDT", "BROCCOLIUSDT", "BCHUSDT", "XPLUSDT", "ZROUSDT", "ARKUSDT", "LYNUSDT"]
SYMBOLS = list(dict.fromkeys(sb.unique_symbols() + EXTRA))
COST_PCT = 0.14
MIN_CANDLES = 30000
RESAMPLES = 10000
SEED = 7


def honest_scalp():
    """Scalp engine where an unreachable breakeven stop exits at the 6h close instead of a price never traded."""
    source = inspect.getsource(v3.run_scalp_v3)
    old = '                    position["stop"] = position["entry"]\n'
    new = '''                    reachable = candle.c > position["entry"] if direction == "long" else candle.c < position["entry"]
                    if not reachable:
                        hit_sl = candle.l <= position["stop"] if direction == "long" else candle.h >= position["stop"]
                        px = position["stop"] if hit_sl else candle.c
                        trades.append(sb.make_trade("Scalp", symbol, direction, position["signal_t"], position["entry_t"],
                            candle.t + sb.INTERVAL_MS["5"], position["entry"], position["orig_stop"], position["target"],
                            position["rr"], px, "TS", sb.outcome_from_exit(direction, position["entry"], position["orig_stop"], px),
                            0.5, cost_pct, position["zone_tf"], "EMA+zone"))
                        position = None
                        continue
'''
    assert source.count(old) == 1
    namespace = dict(vars(v3))
    exec(source.replace(old, new), namespace)
    return namespace["run_scalp_v3"]


def line(label, trades):
    if not trades:
        return f"{label:38} n=   0"
    rs = [t.net_r for t in trades]
    stops = statistics.median(abs(t.entry - t.stop) / t.entry * 100 for t in trades)
    halves = [sum(t.net_r for t in trades if (t.entry_t < SPLIT_MS) == first) for first in (True, False)]
    ordered, equity, peak, drawdown = sorted(trades, key=lambda t: t.exit_t), 0.0, 0.0, 0.0
    for t in ordered:
        equity += t.net_r
        peak = max(peak, equity)
        drawdown = max(drawdown, peak - equity)
    return (f"{label:38} n={len(rs):4} win={100 * sum(r > 0 for r in rs) / len(rs):5.1f}% avgR={sum(rs) / len(rs):7.3f} "
            f"totalR={sum(rs):8.2f} medianStop={stops:5.2f}% maxDD={drawdown:6.1f}R halves={halves[0]:7.1f}/{halves[1]:7.1f}")


def interval_by_coin(trades, coins):
    """90% range of avgR when whole coins are resampled, with the share of resamples above zero."""
    per_coin = [[t.net_r for t in trades if t.symbol == coin] for coin in coins]
    rng, means = random.Random(SEED), []
    for _ in range(RESAMPLES):
        picked = [r for group in rng.choices(per_coin, k=len(per_coin)) for r in group]
        if picked:
            means.append(sum(picked) / len(picked))
    means.sort()
    above = 100 * sum(m > 0 for m in means) / len(means)
    return f"{means[len(means) // 20]:+.3f} to {means[-len(means) // 20]:+.3f}  above zero in {above:.0f}%"


def main():
    scalp = honest_scalp()
    results = {(mode, name): [] for mode in ("scalp", "intraday") for name in zv.NAMES}
    sizes = {name: [] for name in zv.NAMES}
    used = []
    for symbol in SYMBOLS:
        five = sb.fetch_5m(symbol, sb.ms(sb.WARMUP_START), sb.ms(sb.TEST_END), DATA / f"{symbol}_5m.json.gz")
        if len(five) < MIN_CANDLES:
            continue
        used.append(symbol)
        frames = {"5": five}
        for interval in ("15", "60", "240", "D"):
            frames[interval] = sb.aggregate(five, interval)
        for name in zv.NAMES:
            zv.use(name)
            for high_tf, low_tf in (("60", "15"), ("240", "60")):
                sizes[name] += [(z.high - z.low) / z.low * 100 for z in sb.refined_zones(frames[high_tf], high_tf, frames[low_tf], low_tf)]
            for mode, trades in (("scalp", scalp(symbol, frames, COST_PCT, **api.LIVE_SCALP_KWARGS)),
                                 ("intraday", sb.run_intraday(symbol, frames, COST_PCT))):
                results[(mode, name)] += [t for t in trades if t.outcome != "OPEN"]
        print(symbol, "done", flush=True)
    print(f"\n{len(used)} coins, 2026-08-01 to 11-15, cost {COST_PCT}%; halves split at 09-23")
    for mode in ("scalp", "intraday"):
        print(f"\n== {mode}")
        for name in zv.NAMES:
            print(line(name, results[(mode, name)]))
    print("\n== 90% range of avgR (resampling coins)")
    for (mode, name), trades in results.items():
        best = max(sum(t.net_r for t in trades if t.symbol == c) for c in used)
        print(f"{mode:9} {name:36} {interval_by_coin(trades, used)}  total without best coin {sum(t.net_r for t in trades) - best:+.1f}R")
    print("\n== zones (1H->15m and 4H->1H)")
    for name, heights in sizes.items():
        print(f"{name:38} count={len(heights):6} medianHeight={statistics.median(heights):5.2f}%")


if __name__ == "__main__":
    main()
