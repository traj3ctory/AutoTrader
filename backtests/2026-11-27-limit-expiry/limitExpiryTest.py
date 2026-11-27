"""Intraday unfilled limit: never expires (engine today) vs cancelled after N 15m candles. Test only."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "2026-11-26-zone-shape"))
import zoneShapeTest as base  # noqa: E402

sb = base.sb
# The live app treats a limit as fresh for four candles; the others show how sensitive that choice is.
EXPIRIES = (None, 4, 8, 16, 96)


def label(expiry):
    return "never expires (current)" if expiry is None else f"expires after {expiry} candles"


def main():
    results = {expiry: [] for expiry in EXPIRIES}
    used = []
    for symbol in base.SYMBOLS:
        five = sb.fetch_5m(symbol, sb.ms(sb.WARMUP_START), sb.ms(sb.TEST_END), base.DATA / f"{symbol}_5m.json.gz")
        if len(five) < base.MIN_CANDLES:
            continue
        used.append(symbol)
        frames = {"5": five}
        for interval in ("15", "60", "240", "D"):
            frames[interval] = sb.aggregate(five, interval)
        for expiry in EXPIRIES:
            trades = sb.run_intraday(symbol, frames, base.COST_PCT, pending_expiry_candles=expiry)
            results[expiry] += [t for t in trades if t.outcome != "OPEN"]
        print(symbol, "done", flush=True)
    print(f"\n{len(used)} coins, 2026-08-01 to 11-15, cost {base.COST_PCT}%; halves split at 09-23\n\n== intraday")
    for expiry, trades in results.items():
        print(base.line(label(expiry), trades))
    print("\n== 90% range of avgR (resampling coins)")
    for expiry, trades in results.items():
        best = max(sum(t.net_r for t in trades if t.symbol == coin) for coin in used)
        total = sum(t.net_r for t in trades)
        print(f"{label(expiry):28} {base.interval_by_coin(trades, used)}  total without best coin {total - best:+.1f}R")
    print("\n== filled trades by wait from signal candle to fill candle (current rule)")
    waits = [((t.entry_t - t.signal_t) // sb.INTERVAL_MS["15"], t.net_r) for t in results[None]]
    for name, low, high in (("1-4", 1, 4), ("5-16", 5, 16), ("17-96", 17, 96), ("over 96", 97, 10**9)):
        group = [r for wait, r in waits if low <= wait <= high]
        print(f"{name:8} n={len(group):3} totalR={sum(group):+7.2f} avgR={sum(group) / len(group) if group else 0:+.3f}")


if __name__ == "__main__":
    main()
