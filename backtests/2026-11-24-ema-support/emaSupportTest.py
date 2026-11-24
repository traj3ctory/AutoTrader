#!/usr/bin/env python3
"""A/B backtest: current v4 (EMA cross hard gate) vs Zone-Entry (EMA as support only, not a gate)."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import apiAnalyze as live  # noqa: E402
import scalpBacktestV3 as v3  # noqa: E402
import strategyBacktest as sb  # noqa: E402

DATA_DIR = ROOT / "backtests" / "live" / "data"
CORE_7 = {"XRPUSDT", "HYPEUSDT", "DOGEUSDT", "JTOUSDT", "AVAXUSDT", "ZECUSDT", "SOLUSDT"}
EXCLUDE = {"BTCUSDT", "ETHUSDT", "SNXXUSDT"}
COST_PCT = live.COST_PCT


def run_zone_entry(symbol: str, frames: dict, cost_pct: float, *, require_ema_support: bool = False):
    candles = frames["5"]
    closes = [c.c for c in candles]
    e9, e20 = sb.ema(closes, 9), sb.ema(closes, 20)
    zones = sb.clone_zones(sb.refined_zones(frames["60"], "60", frames["15"], "15"))
    zones.sort(key=lambda z: z.known_t)
    structure_4h = sb.StructureLookup(frames["240"], "240")
    structure_1d = sb.StructureLookup(frames["D"], "D")
    atr_lookup = sb.SeriesLookup(frames["240"], "240", sb.atr(frames["240"]))

    active = []
    zone_cursor = 0
    trades = []
    position = None

    for i, candle in enumerate(candles):
        if candle.t > sb.ms(sb.TEST_END):
            break
        in_test = candle.t >= sb.ms(sb.TEST_START)
        while zone_cursor < len(zones) and zones[zone_cursor].known_t <= candle.t:
            active.append(zones[zone_cursor])
            zone_cursor += 1
        for zone in active:
            if zone.invalidated or zone.consumed:
                continue
            if zone.kind == "demand" and candle.c < zone.low:
                zone.invalidated = True
            elif zone.kind == "supply" and candle.c > zone.high:
                zone.invalidated = True
            elif sb.overlaps(candle, zone):
                if zone.touch_index is None:
                    zone.touch_index = i
            if zone.touch_index is not None and i - zone.touch_index > 4:
                zone.consumed = True

        if not in_test:
            continue

        if position is not None:
            direction = position["direction"]
            if not position.get("breakeven_applied") and i - position["entry_index"] >= live.TIME_STOP_CANDLES:
                risk = abs(position["entry"] - position["orig_stop"])
                unreal = ((candle.c - position["entry"]) if direction == "long" else (position["entry"] - candle.c)) / risk if risk else 0.0
                if unreal < live.TIME_STOP_MIN_R:
                    position["stop"] = position["entry"]
                position["breakeven_applied"] = True
            stop_hit = candle.l <= position["stop"] if direction == "long" else candle.h >= position["stop"]
            target_hit = candle.h >= position["target"] if direction == "long" else candle.l <= position["target"]
            if stop_hit or target_hit:
                if stop_hit:
                    exit_price = position["stop"]
                    gross_r = sb.outcome_from_exit(direction, position["entry"], position["orig_stop"], exit_price)
                    result = "SL" if exit_price != position["entry"] else "BE"
                else:
                    exit_price, result, gross_r = position["target"], "TP", position["rr"]
                t = sb.make_trade(
                    "ScalpZone", symbol, direction, position["signal_t"], position["entry_t"],
                    candle.t + sb.INTERVAL_MS["5"], position["entry"], position["orig_stop"],
                    position["target"], position["rr"], exit_price, result, gross_r,
                    0.5, cost_pct, position["zone_tf"], position["confirmation"],
                )
                trades.append(t)
                position = None
            continue

        if i < 20 or e9[i] is None or e20[i] is None or e9[i - 1] is None or e20[i - 1] is None:
            continue

        bias4h = structure_4h.at(candle.t)
        bias1d = structure_1d.at(candle.t)
        current_atr = atr_lookup.at(candle.t)
        if not current_atr:
            continue

        prev = candles[i - 1]
        for direction, kind in (("long", "demand"), ("short", "supply")):
            if direction == "long" and bias4h == "bearish":
                continue
            if direction == "short" and (bias4h == "bullish" or bias1d not in ("bearish", "range")):
                continue
            ema_ok = (e9[i] > e20[i] and e9[i] > e9[i - 1]) if direction == "long" else (e9[i] < e20[i] and e9[i] < e9[i - 1])
            if require_ema_support and not ema_ok:
                continue

            cands = [z for z in active if z.kind == kind and not z.invalidated and not z.consumed
                     and z.touch_index is not None and 0 <= i - z.touch_index <= 4]
            if not cands:
                continue
            picked = None
            for z in cands:
                if sb.rejection(candle, z, direction) or sb.engulfing(prev, candle, z, direction):
                    picked = z
                    break
            if picked is None:
                continue

            entry = candle.c
            stop = picked.low - 0.50 * current_atr if direction == "long" else picked.high + 0.50 * current_atr
            if (direction == "long" and stop >= entry) or (direction == "short" and stop <= entry):
                picked.consumed = True
                continue
            opposite = [z for z in active if z.kind != kind and z.known_t <= candle.t and not z.invalidated]
            rr, target = sb.choose_rr(entry, stop, direction, opposite)
            picked.consumed = True
            if rr is None or target is None:
                continue
            tag = "EMA_SUPPORT" if ema_ok else "EMA_NEUTRAL"
            position = {
                "direction": direction,
                "signal_t": candle.t,
                "entry_t": candle.t + sb.INTERVAL_MS["5"],
                "entry_index": i,
                "entry": entry,
                "stop": stop,
                "orig_stop": stop,
                "target": target,
                "rr": rr,
                "zone_tf": picked.source_tf,
                "confirmation": tag,
                "breakeven_applied": False,
            }
            break

    return trades


def summarize(label: str, trades: list) -> str:
    closed = [t for t in trades if t.outcome != "OPEN"]
    if not closed:
        return f"{label:42} n=  0"
    wins = sum(1 for t in closed if t.net_r > 0)
    total = sum(t.net_r for t in closed)
    avg = total / len(closed)
    return f"{label:42} n={len(closed):3d} win={wins / len(closed) * 100:5.1f}% avgR={avg:+7.3f} totalR={total:+7.2f}"


def main():
    symbols = sorted(p.name.replace("_5m.json.gz", "") for p in DATA_DIR.glob("*_5m.json.gz"))
    symbols = [s for s in symbols if s not in EXCLUDE]

    base_all, zone_all, zone_ema_all = [], [], []
    base_core, zone_core, zone_ema_core = [], [], []

    for sym in symbols:
        five = live.load_history(sym) if False else None  # read cached gzip directly (offline-safe)
        import gzip, json
        with gzip.open(DATA_DIR / f"{sym}_5m.json.gz", "rt", encoding="utf-8") as h:
            five = [sb.Candle(**r) for r in json.load(h)]
        if len(five) < 10000:
            continue
        frames = live.build_frames(five)
        live.set_window(five)

        t_base = v3.run_scalp_v3(sym, frames, COST_PCT, short_gates=True, time_stop=True,
                                 time_stop_candles=live.TIME_STOP_CANDLES, time_stop_min_r=live.TIME_STOP_MIN_R)
        t_zone = run_zone_entry(sym, frames, COST_PCT, require_ema_support=False)
        t_zema = run_zone_entry(sym, frames, COST_PCT, require_ema_support=True)

        base_all.extend(t_base)
        zone_all.extend(t_zone)
        zone_ema_all.extend(t_zema)
        if sym in CORE_7:
            base_core.extend(t_base)
            zone_core.extend(t_zone)
            zone_ema_core.extend(t_zema)

    lines = [
        f"Backtest window: cached ~90d out-of-warmup across {len(symbols)} symbols (cost {COST_PCT}% round-trip)",
        "",
        "=== ALL CACHED CRYPTO SYMBOLS ===",
        summarize("1. Baseline v4 (EMA cross hard gate)", base_all),
        summarize("2. Zone-Entry (5m rej/eng, EMA ignored)", zone_all),
        summarize("   -> slice: EMA supporting", [t for t in zone_all if t.confirmation == "EMA_SUPPORT"]),
        summarize("   -> slice: EMA not supporting", [t for t in zone_all if t.confirmation == "EMA_NEUTRAL"]),
        summarize("3. Zone-Entry + EMA aligned gate", zone_ema_all),
        "",
        "=== CORE 7 LEDGER COINS (XRP,HYPE,DOGE,JTO,AVAX,ZEC,SOL) ===",
        summarize("1. Baseline v4 (EMA cross hard gate)", base_core),
        summarize("2. Zone-Entry (5m rej/eng, EMA ignored)", zone_core),
        summarize("   -> slice: EMA supporting", [t for t in zone_core if t.confirmation == "EMA_SUPPORT"]),
        summarize("   -> slice: EMA not supporting", [t for t in zone_core if t.confirmation == "EMA_NEUTRAL"]),
        summarize("3. Zone-Entry + EMA aligned gate", zone_ema_core),
    ]
    out = "\n".join(lines)
    print(out)
    out_path = Path(__file__).resolve().parent / "results.txt"
    out_path.write_text(out + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
