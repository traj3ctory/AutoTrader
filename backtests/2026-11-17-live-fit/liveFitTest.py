#!/usr/bin/env python3
# Tests two live-use questions on the v4 scalp engine: cost of entering late, and signals hidden behind an open engine position.
import datetime as dt
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import strategyBacktest as sb  # noqa: E402
import scalpBacktestV3 as v3  # noqa: E402

COST = 0.14
STEP = sb.INTERVAL_MS["5"]
CORE = ["XRPUSDT", "HYPEUSDT", "DOGEUSDT", "JTOUSDT", "AVAXUSDT", "ZECUSDT", "SOLUSDT"]
WINDOWS = {
    "in-sample May-Jul": (sb.TEST_START, sb.TEST_END, ROOT / "backtests" / "2026-07-31" / "data"),
    "out-of-sample Aug-Nov": (dt.datetime(2026, 8, 1, tzinfo=sb.UTC),
                              dt.datetime(2026, 11, 16, tzinfo=sb.UTC) - dt.timedelta(milliseconds=1),
                              ROOT / "backtests" / "2026-11-16-oos" / "data"),
}


def simulate(candles, start, direction, entry, stop, target):
    # Walks one trade forward from the candle after `start` with the engine's exit and time-stop rules; returns net R or None if still open.
    risk = abs(entry - stop)
    if risk <= 0:
        return None
    live_stop, be_done = stop, False
    for j in range(start + 1, len(candles)):
        c = candles[j]
        if c.t > sb.ms(sb.TEST_END):
            return None
        if not be_done and j - start >= 72:
            unreal = ((c.c - entry) if direction == "long" else (entry - c.c)) / risk
            if unreal < -0.3:
                live_stop = entry
            be_done = True
        stop_hit = c.l <= live_stop if direction == "long" else c.h >= live_stop
        target_hit = c.h >= target if direction == "long" else c.l <= target
        if stop_hit or target_hit:
            exit_price = live_stop if stop_hit else target
            gross = ((exit_price - entry) if direction == "long" else (entry - exit_price)) / risk
            return gross - COST / 100 * entry / risk
    return None


def late_entry(candles, index, trade, delay):
    # Same signal, stop and target, but entered at the close `delay` candles later; None if the level already traded.
    i = index[trade.signal_t]
    for j in range(i + 1, i + delay + 1):
        if j >= len(candles):
            return None
        c = candles[j]
        if trade.direction == "long" and (c.l <= trade.stop or c.h >= trade.target):
            return None
        if trade.direction == "short" and (c.h >= trade.stop or c.l <= trade.target):
            return None
    entry = candles[i + delay].c
    return simulate(candles, i + delay, trade.direction, entry, trade.stop, trade.target)


def all_signals(symbol, frames):
    # The v4 entry rules evaluated on every candle with no one-position rule; zones are still consumed once.
    candles = frames["5"]
    closes = [c.c for c in candles]
    e9, e20 = sb.ema(closes, 9), sb.ema(closes, 20)
    zones = sb.clone_zones(sb.refined_zones(frames["60"], "60", frames["15"], "15"))
    zones.sort(key=lambda z: z.known_t)
    s4, s1 = sb.StructureLookup(frames["240"], "240"), sb.StructureLookup(frames["D"], "D")
    atr_lookup = sb.SeriesLookup(frames["240"], "240", sb.atr(frames["240"]))
    active, cursor, out = [], 0, []
    for i, candle in enumerate(candles):
        if candle.t > sb.ms(sb.TEST_END):
            break
        while cursor < len(zones) and zones[cursor].known_t <= candle.t:
            active.append(zones[cursor])
            cursor += 1
        for zone in active:
            if zone.invalidated or zone.consumed:
                continue
            if zone.kind == "demand" and candle.c < zone.low or zone.kind == "supply" and candle.c > zone.high:
                zone.invalidated = True
        if candle.t < sb.ms(sb.TEST_START) or i < 20 or None in (e9[i], e20[i], e9[i - 1], e20[i - 1]):
            continue
        bias4h = s4.at(candle.t)
        if e9[i - 1] <= e20[i - 1] and e9[i] > e20[i] and e9[i] > e9[i - 1] and e20[i] > e20[i - 1] and bias4h != "bearish":
            direction, kind = "long", "demand"
        elif e9[i - 1] >= e20[i - 1] and e9[i] < e20[i] and e9[i] < e9[i - 1] and e20[i] < e20[i - 1] and bias4h != "bullish":
            if s1.at(candle.t) not in ("bearish", "range") or not v3.micro_break(candles, i, "short"):
                continue
            direction, kind = "short", "supply"
        else:
            continue
        cands = [z for z in active if z.kind == kind and not z.invalidated and not z.consumed
                 and (z.proximal <= candle.c if direction == "long" else z.proximal >= candle.c)]
        cands.sort(key=lambda z: (abs(candle.c - z.proximal), -z.known_t))
        atr_now = atr_lookup.at(candle.t)
        if not cands or not atr_now:
            continue
        zone, entry = cands[0], candle.c
        stop = zone.low - 0.5 * atr_now if direction == "long" else zone.high + 0.5 * atr_now
        zone.consumed = True
        if direction == "long" and stop >= entry or direction == "short" and stop <= entry:
            continue
        rr, target = sb.choose_rr(entry, stop, direction, [z for z in active if z.kind != kind and not z.invalidated])
        if rr is None:
            continue
        net = simulate(candles, i, direction, entry, stop, target)
        if net is not None:
            out.append((candle.t, net))
    return out


def fmt(label, rs):
    if not rs:
        return f"  {label:46} n=   0"
    wins = sum(1 for r in rs if r > 0)
    return f"  {label:46} n={len(rs):4} win={wins / len(rs) * 100:5.1f}% avgR={sum(rs) / len(rs):7.3f} totalR={sum(rs):8.2f}"


def main():
    rows = []
    for name, (start, end, data_dir) in WINDOWS.items():
        sb.TEST_START, sb.TEST_END = start, end
        v3.DATA_DIR = data_dir
        for group, symbols in (("all coins with data", sorted(p.name.split("_")[0] for p in data_dir.glob("*_5m.json.gz"))),
                               ("core 6 + SOL", CORE)):
            base, late, free_blocked, free_clear = [], {d: [] for d in (1, 3, 6, 12)}, [], []
            for symbol in symbols:
                if not (data_dir / f"{symbol}_5m.json.gz").exists():
                    continue
                frames = v3.load_frames(symbol)
                candles = frames["5"]
                index = {c.t: i for i, c in enumerate(candles)}
                trades = [t for t in v3.run_scalp_v3(symbol, frames, COST, short_gates=True, time_stop=True,
                                                     time_stop_candles=72, time_stop_min_r=-0.3) if t.outcome != "OPEN"]
                base += [t.net_r for t in trades]
                for delay in late:
                    late[delay] += [r for r in (late_entry(candles, index, t, delay) for t in trades) if r is not None]
                spans = [(t.signal_t, t.exit_t) for t in trades]
                for t_sig, net in all_signals(symbol, frames):
                    blocked = any(a < t_sig < b - STEP for a, b in spans)
                    (free_blocked if blocked else free_clear).append(net)
            rows.append(f"{name} - {group}")
            rows.append(fmt("engine as tested (entry at signal close)", base))
            for delay, rs in late.items():
                rows.append(fmt(f"entered {delay} candle(s) late, same SL/TP", rs))
            rows.append(fmt("no one-position rule: all signals", free_blocked + free_clear))
            rows.append(fmt("  of which fired while engine was in a trade", free_blocked))
            rows.append("")
    text = "\n".join(rows)
    print(text)
    (HERE / "results.txt").write_text(text + "\n")


if __name__ == "__main__":
    main()
