#!/usr/bin/env python3
# Frequent signal scan: replays the backtest engines and reports only signals that are new since the last run.
import json
import subprocess
import sys
import time
from pathlib import Path

import apiAnalyze as live
import riskGuard

sb, v3 = live.sb, live.v3
ROOT = Path(__file__).resolve().parent.parent
STATE_PATH = ROOT / ".signal_state.json"
SCALP_MAX_AGE = 12
INTRADAY_MAX_AGE = 4
STATE_KEEP_MS = 3 * live.DAY_MS
SPAN15 = sb.INTERVAL_MS["15"]


def load_state():
    try:
        return json.loads(STATE_PATH.read_text()).get("reported", {})
    except (OSError, ValueError):
        return {}


def scan_scalp(symbol, frames):
    state = {}
    v3.run_scalp_v3(symbol, frames, live.COST_PCT, state_out=state, **live.LIVE_SCALP_KWARGS)
    position = state["position"]
    c5 = frames["5"]
    if position is None:
        return None
    age = len(c5) - 1 - position["entry_index"]
    if age > SCALP_MAX_AGE:
        return None
    side = position["direction"].upper()
    bias4h = sb.StructureLookup(frames["240"], "240").at(position["signal_t"])
    against = "bearish" if side == "LONG" else "bullish"
    tier = " [LOWER TIER: counter to 4H trend]" if bias4h == against else ""
    drift = live.unreal_r(position, c5[-1].c)
    late = "on the last closed candle" if age == 0 else f"{age} candle(s) ago - late entry with the same SL/TP tested equal up to 12 candles"
    text = (f"{symbol} SCALP {side}{tier} - cross closed {live.hhmm(position['signal_t'] + live.FIVE_MS)} UTC ({late}): "
            f"entry {position['entry']:.6g}, SL {position['orig_stop']:.6g}, TP {position['target']:.6g}, "
            f"R:R {position['rr']}; price now {c5[-1].c:.6g} ({drift:+.2f}R from entry)")
    return f"{symbol}:scalp:{position['signal_t']}", position["signal_t"], text


def scan_intraday(symbol, frames):
    state = {}
    sb.run_intraday(symbol, frames, live.COST_PCT, state_out=state)
    pending = state["pending"]
    if pending is None or state["position"] is not None:
        return None
    last = frames["15"][-1]
    age = (last.t - pending["signal_t"]) // SPAN15
    if age > INTRADAY_MAX_AGE:
        return None
    side = pending["direction"].upper()
    gap = abs(pending["entry"] - last.c) / last.c * 100
    text = (f"{symbol} INTRADAY {side} - {pending['confirmation']} closed {live.hhmm(pending['signal_t'] + SPAN15)} UTC "
            f"({age} candle(s) ago): limit {pending['entry']:.6g} ({gap:.1f}% from price), SL {pending['stop']:.6g}, "
            f"TP {pending['target']:.6g}, R:R {pending['rr']}; cancel if SL trades before the fill")
    return f"{symbol}:intraday:{pending['signal_t']}", pending["signal_t"], text


def main():
    args = sys.argv[1:]
    notify = "--notify" in args
    symbols = [a.upper().replace(".P", "") for a in args if not a.startswith("--")]
    ledger = json.loads((ROOT / "SETUP_LEDGER.json").read_text())
    symbols += [s.replace(".P", "") for s in ledger["setups"] if s.replace(".P", "") not in symbols]

    reported = load_state()
    fresh, failed = [], []
    for symbol in symbols:
        try:
            five = live.load_history(symbol)
            frames = live.build_frames(five)
            live.set_window(five)
            for found in (scan_scalp(symbol, frames), scan_intraday(symbol, frames)):
                if found and found[0] not in reported:
                    reported[found[0]] = found[1]
                    fresh.append(found[2])
        except Exception as exc:
            failed.append(f"{symbol}: {exc}")

    cutoff = int(time.time() * 1000) - STATE_KEEP_MS
    reported = {k: t for k, t in reported.items() if t >= cutoff}
    STATE_PATH.write_text(json.dumps({"reported": reported}, indent=1))

    if fresh:
        print(f"NEW ENGINE SIGNALS ({len(fresh)}):")
        print(f"  {riskGuard.line()}")
        for line in fresh:
            print(f"  {line}")
        if notify:
            body = "; ".join(line.split(":")[0] for line in fresh).replace('"', "")
            subprocess.run(["osascript", "-e", f'display notification "{body}" with title "AutoTrader signal"'],
                           check=False)
    else:
        print("No new signals.")
    if failed:
        print(f"Scan failed for {len(failed)} coin(s): " + " | ".join(failed))
        if len(failed) == len(symbols):
            sys.exit(1)


if __name__ == "__main__":
    main()
