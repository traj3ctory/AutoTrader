#!/usr/bin/env python3
# Live read that replays the backtested engines themselves over fresh Bybit candles.
# Usage: python3 scripts/apiAnalyze.py SYMBOL [SYMBOL ...] [--trade-type scalp|intraday|both] [--ledger] [--summary]
import datetime as dt
import gzip
import json
import sys
import time
import urllib.parse
from dataclasses import asdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import strategyBacktest as sb  # noqa: E402
import scalpBacktestV3 as v3  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
CACHE_DIR = ROOT / "backtests" / "live" / "data"
HISTORY_DAYS = 150
WARMUP_DAYS = 61
COST_PCT = 0.14
TIME_STOP_CANDLES = 72
TIME_STOP_MIN_R = -0.3
LATE_ENTRY_CANDLES = 12
DAY_MS = 86_400_000
FIVE_MS = sb.INTERVAL_MS["5"]


def hhmm(t_ms):
    return time.strftime("%m-%d %H:%M", time.gmtime(t_ms / 1000))


def load_history(symbol):
    # Closed 5m candles for the last HISTORY_DAYS, cached on disk and topped up incrementally.
    now_ms = int(time.time() * 1000)
    # Anchor the start to a month boundary so the replay path only shifts once a month, not every run.
    floor = dt.datetime.fromtimestamp((now_ms - HISTORY_DAYS * DAY_MS) / 1000, sb.UTC)
    start_ms = int(floor.replace(day=1, hour=0, minute=0, second=0, microsecond=0).timestamp() * 1000)
    cache_path = CACHE_DIR / f"{symbol}_5m.json.gz"
    rows = {}
    if cache_path.exists():
        with gzip.open(cache_path, "rt", encoding="utf-8") as handle:
            rows = {r["t"]: sb.Candle(**r) for r in json.load(handle) if r["t"] >= start_ms}
    # A cache that starts late was built with a shorter window, so refetch it in full.
    if rows and min(rows) > start_ms + DAY_MS:
        rows = {}
    stop_at = max(rows) if rows else start_ms
    cursor = now_ms
    while cursor >= stop_at:
        query = urllib.parse.urlencode({"category": "linear", "symbol": symbol, "interval": "5",
                                        "limit": 1000, "end": cursor})
        # Bybit intermittently answers "svc error" under load, so retry before giving up.
        for attempt in range(5):
            data = sb.request_json(f"https://api.bybit.com/v5/market/kline?{query}")
            if data.get("retCode") == 0:
                break
            time.sleep(1.5 * (attempt + 1))
        else:
            raise RuntimeError(f"{symbol}: Bybit error {data.get('retMsg')}")
        page = data.get("result", {}).get("list", [])
        if not page:
            break
        oldest = cursor
        for item in page:
            t = int(item[0])
            oldest = min(oldest, t)
            # Skip the still-forming candle: the engines only ever saw closed candles.
            if t >= start_ms and t + FIVE_MS <= now_ms:
                rows[t] = sb.Candle(t=t, o=float(item[1]), h=float(item[2]), l=float(item[3]),
                                    c=float(item[4]), v=float(item[5]))
        if oldest >= cursor or oldest <= stop_at:
            break
        cursor = oldest - 1
        time.sleep(0.05)
    candles = sorted(rows.values(), key=lambda c: c.t)
    if not candles:
        raise RuntimeError(f"{symbol}: no candles returned")
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(cache_path, "wt", encoding="utf-8") as handle:
        json.dump([asdict(c) for c in candles], handle, separators=(",", ":"))
    return candles


def build_frames(five):
    frames = {"5": five}
    for interval in ("15", "60", "240", "D"):
        frames[interval] = sb.aggregate(five, interval)
    # Drop a partial last 15m bucket so the intraday engine never confirms on an unclosed candle.
    if (five[-1].t + FIVE_MS) % sb.INTERVAL_MS["15"] != 0:
        frames["15"] = frames["15"][:-1]
    return frames


def set_window(five):
    # Point the engines' replay window at the live history: warm-up first, then signal replay to now.
    span_days = (five[-1].t - five[0].t) / DAY_MS
    warmup = min(WARMUP_DAYS, span_days * 0.67)
    sb.TEST_START = dt.datetime.fromtimestamp(five[0].t / 1000, sb.UTC) + dt.timedelta(days=warmup)
    sb.TEST_END = dt.datetime.fromtimestamp(five[-1].t / 1000, sb.UTC)
    return span_days, span_days - warmup


def replay_line(trades, replay_days):
    done = [t for t in trades if t.outcome != "OPEN"]
    if not done:
        return f"Engine replay, last {replay_days:.0f}d: 0 closed trades"
    wins = sum(1 for t in done if t.net_r > 0)
    total = sum(t.net_r for t in done)
    last = done[-1]
    return (f"Engine replay, last {replay_days:.0f}d: {len(done)} closed, {wins} won, {total:+.2f}R net of "
            f"{COST_PCT}% cost | last: {last.direction} {last.outcome} {last.net_r:+.2f}R, exit {hhmm(last.exit_t)} UTC")


def unreal_r(position, price):
    risk = abs(position["entry"] - position.get("orig_stop", position["stop"]))
    move = price - position["entry"] if position["direction"] == "long" else position["entry"] - price
    return move / risk if risk else 0.0


def zone_txt(zone):
    if zone is None:
        return "none"
    return f"{zone.low:.6g}-{zone.high:.6g} (FVG {'present' if zone.has_fvg else 'absent'})"


def scalp_reference(direction, active, price, atr_now):
    # The zone, stop and target the engine would use if a valid cross closed at the current price.
    kind = "demand" if direction == "long" else "supply"
    cands = [z for z in active if z.kind == kind and not z.invalidated and not z.consumed
             and (z.proximal <= price if direction == "long" else z.proximal >= price)]
    cands.sort(key=lambda z: (abs(price - z.proximal), -z.known_t))
    if not cands or not atr_now:
        return None, None, None, None
    zone = cands[0]
    stop = zone.low - 0.5 * atr_now if direction == "long" else zone.high + 0.5 * atr_now
    opposite = [z for z in active if z.kind != kind and not z.invalidated]
    rr, target = sb.choose_rr(price, stop, direction, opposite)
    return zone, stop, rr, target


def analyze_scalp(symbol, frames, span_days, replay_days, summary):
    c5 = frames["5"]
    state = {}
    trades = v3.run_scalp_v3(symbol, frames, COST_PCT, short_gates=True, time_stop=True,
                             time_stop_candles=TIME_STOP_CANDLES, time_stop_min_r=TIME_STOP_MIN_R,
                             state_out=state)
    active, position = state["active"], state["position"]
    i = len(c5) - 1
    price, now_t = c5[i].c, c5[i].t
    closes = [c.c for c in c5]
    e9, e20 = sb.ema(closes, 9), sb.ema(closes, 20)
    bias4h = sb.StructureLookup(frames["240"], "240").at(now_t)
    bias1d = sb.StructureLookup(frames["D"], "D").at(now_t)
    atr_now = sb.SeriesLookup(frames["240"], "240", sb.atr(frames["240"])).at(now_t)
    vwap = sb.daily_vwap(c5)[i]

    bull_cross = e9[i - 1] <= e20[i - 1] and e9[i] > e20[i]
    bear_cross = e9[i - 1] >= e20[i - 1] and e9[i] < e20[i]
    bull_slope = e9[i] > e9[i - 1] and e20[i] > e20[i - 1]
    bear_slope = e9[i] < e9[i - 1] and e20[i] < e20[i - 1]

    if position is not None:
        age = i - position["entry_index"]
        side = position["direction"].upper()
        levels = (f"entry {position['entry']:.6g}, SL {position['orig_stop']:.6g}, "
                  f"TP {position['target']:.6g}, R:R {position['rr']}")
        if age == 0:
            cost_r = COST_PCT / 100 * position["entry"] / abs(position["entry"] - position["orig_stop"])
            verdict = f"VALID {side} - cross closed {hhmm(position['signal_t'] + FIVE_MS)} UTC: {levels}, cost ~{cost_r:.2f}R"
        else:
            stop_note = " (time-stop moved SL to breakeven)" if position["stop"] != position["orig_stop"] else ""
            tail = ("Late entry with the same SL/TP tested equal up to 12 candles." if age <= LATE_ENTRY_CANDLES
                    else "Too old to enter: only entries within 12 candles were tested.")
            verdict = (f"ENGINE IN TRADE - {side} signalled {hhmm(position['signal_t'] + FIVE_MS)} UTC, {age} candles ago: "
                       f"{levels}{stop_note}; now {unreal_r(position, price):+.2f}R. {tail}")
    else:
        verdict = "NO SIGNAL on the last closed 5m candle"

    if summary:
        print(f"{symbol:14} SCALP    {price:<12.6g} 4H {bias4h:8} 1D {bias1d:8} {verdict}")
        return

    print(f"\n===== {symbol} - LIVE ENGINE READ (Scalp, backtest v4 rules) =====")
    print(f"Last closed 5m candle: {hhmm(now_t + FIVE_MS)} UTC   Price: {price:.6g}   History: {span_days:.0f}d")
    if span_days < HISTORY_DAYS - 2:  # short history means fewer known zones
        print(f"WARNING: only {span_days:.0f}d of history (engine was tested on 150d) - zone state is less reliable")
    print(f"4H structure: {bias4h}   |   1D structure: {bias1d}")
    print(f"Session VWAP (context only, not a gate): {vwap:.6g} ({'price above' if price > vwap else 'price below'})")

    order = "BULL-ordered (9 above 20)" if e9[i] > e20[i] else "BEAR-ordered (9 below 20)"
    flip_txt = "no cross found in history"
    for j in range(i, 0, -1):
        if None in (e9[j], e20[j], e9[j - 1], e20[j - 1]):
            break
        if (e9[j - 1] <= e20[j - 1]) != (e9[j] <= e20[j]):
            flip_dir = "BULLISH" if e9[j] > e20[j] else "BEARISH"
            flip_txt = f"last cross {flip_dir}, closed {hhmm(c5[j].t + FIVE_MS)} UTC ({i - j} candles ago)"
            break
    slope = "UP (both EMAs)" if bull_slope else "DOWN (both EMAs)" if bear_slope else "MIXED"
    print(f"5m EMA 9/20: {order}   slope: {slope}   |   {flip_txt}")

    print(f"\nVERDICT: {verdict}")
    for direction, crossed, sloped in (("long", bull_cross, bull_slope), ("short", bear_cross, bear_slope)):
        against = "bearish" if direction == "long" else "bullish"
        zone, stop, rr, target = scalp_reference(direction, active, price, atr_now)
        blocks = []
        if not crossed:
            blocks.append("no 9/20 cross on the last closed candle")
        if not sloped:
            blocks.append("both EMAs not sloping in direction")
        if bias4h == against:
            blocks.append(f"4H counter-trend (4H reads {bias4h})")
        if direction == "short":
            if bias1d not in ("bearish", "range"):
                blocks.append(f"1D structure gate (1D reads {bias1d})")
            if not v3.micro_break(c5, i, "short"):
                blocks.append("no 5m micro-structure break")
        side_txt = "below" if direction == "long" else "above"
        kind = "demand" if direction == "long" else "supply"
        if zone is None:
            blocks.append(f"no live unused {kind} zone {side_txt} price")
            ref = f"reference {kind} zone: none"
        else:
            if rr is None:
                blocks.append("no room for 1.5R before the next opposing zone")
            plan = f"TP {target:.6g} ({rr}R)" if rr else "no qualifying target"
            ref = f"reference {kind} zone {zone_txt(zone)} -> if a cross closed here: SL {stop:.6g}, {plan}"
        status = "all gates pass" if not blocks else "blocked by: " + "; ".join(blocks)
        print(f"  {direction.upper():5} {status}")
        print(f"        {ref}")
    print(replay_line(trades, replay_days))


def analyze_intraday(symbol, frames, span_days, replay_days, summary):
    c15 = frames["15"]
    state = {}
    trades = sb.run_intraday(symbol, frames, COST_PCT, state_out=state)
    active, pending, position = state["active"], state["pending"], state["position"]
    last = c15[-1]
    i = len(c15) - 1
    price, now_t = last.c, last.t
    bias = sb.StructureLookup(frames["D"], "D").at(now_t)
    span15 = sb.INTERVAL_MS["15"]

    if position is not None:
        side = position["direction"].upper()
        verdict = (f"ENGINE IN TRADE - {side} filled {hhmm(position['entry_t'])} UTC: entry {position['entry']:.6g}, "
                   f"SL {position['stop']:.6g}, TP {position['target']:.6g}, R:R {position['rr']}; "
                   f"now {unreal_r(position, price):+.2f}R. A late entry is not the tested trade.")
    elif pending is not None:
        side = pending["direction"].upper()
        age = (now_t - pending["signal_t"]) // span15
        gap = abs(pending["entry"] - price) / price * 100
        label = f"VALID {side}" if age <= 4 else f"ENGINE ORDER STILL RESTING - {side}"
        verdict = (f"{label} - {pending['confirmation']} closed {hhmm(pending['signal_t'] + span15)} UTC "
                   f"({age} candles ago): limit {pending['entry']:.6g} ({gap:.1f}% from price), SL {pending['stop']:.6g}, "
                   f"TP {pending['target']:.6g}, R:R {pending['rr']}; cancel if SL trades before the fill")
    else:
        verdict = "NO SIGNAL on the last closed 15m candle"

    if summary:
        print(f"{symbol:14} INTRADAY {price:<12.6g} 1D {bias:8} {'':11} {verdict}")
        return

    print(f"\n===== {symbol} - LIVE ENGINE READ (Intraday, backtest rules) =====")
    print(f"Last closed 15m candle: {hhmm(now_t + span15)} UTC   Price: {price:.6g}   History: {span_days:.0f}d")
    print(f"1D structure: {bias}")
    print(f"\nVERDICT: {verdict}")
    for direction, kind in (("long", "demand"), ("short", "supply")):
        live = [z for z in active if z.kind == kind and not z.invalidated and not z.consumed]
        live.sort(key=lambda z: abs(price - z.proximal))
        nearest = live[0] if live else None
        blocks = []
        if bias == "range":
            blocks.append("1D structure is range (engine trades neither side)")
        elif (bias == "bullish") != (direction == "long"):
            blocks.append(f"1D structure ({bias}) opposes {direction}")
        touched = [z for z in live if z.touch_index is not None and 0 <= i - z.touch_index <= 4]
        if not touched:
            blocks.append(f"no unused {kind} zone first touched within the last 4 closed 15m candles")
        elif not any(sb.rejection(last, z, direction) or sb.engulfing(c15[-2], last, z, direction) for z in touched):
            blocks.append("touched zone has no rejection/engulfing on the last closed 15m candle")
        status = "all gates pass" if not blocks else "blocked by: " + "; ".join(blocks)
        print(f"  {direction.upper():5} {status}")
        print(f"        nearest unused {kind} zone: {zone_txt(nearest)}")
    print(replay_line(trades, replay_days))


def main():
    args = sys.argv[1:]
    trade_type = "scalp"
    if "--trade-type" in args:
        at = args.index("--trade-type")
        trade_type = args[at + 1].lower()
        del args[at:at + 2]
    summary = "--summary" in args
    symbols = [a.upper().replace(".P", "") for a in args if not a.startswith("--")]
    if "--ledger" in args:
        ledger = json.loads((ROOT / "SETUP_LEDGER.json").read_text())
        symbols += [s.replace(".P", "") for s in ledger["setups"] if s.replace(".P", "") not in symbols]
    if not symbols or trade_type not in ("scalp", "intraday", "both"):
        print("Usage: python3 scripts/apiAnalyze.py SYMBOL [SYMBOL ...] "
              "[--trade-type scalp|intraday|both] [--ledger] [--summary]")
        sys.exit(1)
    for symbol in symbols:
        try:
            five = load_history(symbol)
            frames = build_frames(five)
            span_days, replay_days = set_window(five)
            if trade_type in ("scalp", "both"):
                analyze_scalp(symbol, frames, span_days, replay_days, summary)
            if trade_type in ("intraday", "both"):
                analyze_intraday(symbol, frames, span_days, replay_days, summary)
        except Exception as exc:
            print(f"{symbol}: ANALYSIS FAILED - {exc}")


if __name__ == "__main__":
    main()
