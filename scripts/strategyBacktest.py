#!/usr/bin/env python3
"""Three-month, no-lookahead backtest of the user's AutoTrader rules.

This is intentionally a conservative mechanical proxy for discretionary
market-structure and hand-drawn supply/demand zones.  It downloads Bybit
linear-perpetual 5-minute candles, aggregates higher timeframes locally, and
emits auditable JSON/CSV outputs for the companion workbook.
"""

from __future__ import annotations

import argparse
import bisect
import csv
import datetime as dt
import gzip
import json
import math
import os
import statistics
import threading
import time
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable, Optional


UTC = dt.timezone.utc
MS_MINUTE = 60_000
INTERVAL_MS = {"5": 5 * MS_MINUTE, "15": 15 * MS_MINUTE, "60": 60 * MS_MINUTE,
               "240": 240 * MS_MINUTE, "D": 1_440 * MS_MINUTE}

TEST_START = dt.datetime(2026, 5, 3, tzinfo=UTC)
TEST_END = dt.datetime(2026, 8, 1, tzinfo=UTC) - dt.timedelta(milliseconds=1)
WARMUP_START = TEST_START - dt.timedelta(days=61)

GROUPS = {
    "Ledger": ["XRPUSDT", "DOGEUSDT", "ZECUSDT", "AVAXUSDT", "JTOUSDT", "LITUSDT"],
    "Core watchlist": ["HYPEUSDT", "XRPUSDT", "DOGEUSDT", "JTOUSDT", "AVAXUSDT", "ZECUSDT"],
    "Tier 2": ["BEATUSDT", "BTWUSDT", "SOONUSDT", "FARTCOINUSDT", "KAITOUSDT",
               "AKEUSDT", "USUSDT", "BNBUSDT", "UNIUSDT", "UAIUSDT"],
}


def unique_symbols() -> list[str]:
    out: list[str] = []
    for symbols in GROUPS.values():
        for symbol in symbols:
            if symbol not in out:
                out.append(symbol)
    return out


def groups_for(symbol: str) -> str:
    return ", ".join(name for name, symbols in GROUPS.items() if symbol in symbols)


def ms(value: dt.datetime) -> int:
    return int(value.timestamp() * 1000)


def iso(value: int) -> str:
    return dt.datetime.fromtimestamp(value / 1000, UTC).isoformat().replace("+00:00", "Z")


@dataclass
class Candle:
    t: int
    o: float
    h: float
    l: float
    c: float
    v: float


@dataclass
class Pivot:
    kind: str
    t: int
    known_t: int
    price: float
    candle_index: int


@dataclass
class Zone:
    id: str
    kind: str
    source_tf: str
    t: int
    known_t: int
    low: float
    high: float
    pivot_price: float
    touch_index: Optional[int] = None
    consumed: bool = False
    invalidated: bool = False
    has_fvg: bool = False  # 2026-08-03: soft/reported-only quality signal, never a
    # gate (see ANALYZE_PROMPT.md) - True if the displacement leg away from this
    # zone (origin candle to the confirming BOS candle, at the zone's own source
    # timeframe) left a 3-candle Fair Value Gap in the zone's direction. Evidence
    # the move was genuinely one-sided, not proof either way - does not affect
    # entry, sizing, or R:R.
    refined: bool = False  # True only when a lower-timeframe zone narrowed this box (display label).

    @property
    def proximal(self) -> float:
        return self.high if self.kind == "demand" else self.low

    @property
    def distal(self) -> float:
        return self.low if self.kind == "demand" else self.high


@dataclass
class Trade:
    strategy: str
    symbol: str
    groups: str
    direction: str
    signal_t: int
    entry_t: int
    exit_t: int
    entry: float
    stop: float
    target: float
    planned_rr: float
    exit_price: float
    outcome: str
    gross_r: float
    net_r: float
    risk_pct: float
    fee_slippage_pct: float
    zone_tf: str
    confirmation: str
    accepted: bool = True
    portfolio_skip_reason: str = ""

    def row(self) -> dict[str, Any]:
        data = asdict(self)
        for key in ("signal_t", "entry_t", "exit_t"):
            data[key.replace("_t", "_time_utc")] = iso(data.pop(key))
        return data


def request_json(url: str, retries: int = 5) -> dict[str, Any]:
    last: Optional[Exception] = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "AutoTrader-backtest/1.0"})
            with urllib.request.urlopen(req, timeout=30) as response:
                return json.load(response)
        except Exception as exc:  # network retries are deliberate and bounded
            last = exc
            time.sleep(min(8, 1.5 ** attempt))
    raise RuntimeError(f"Request failed after {retries} attempts: {url}: {last}")


def write_gz_json_atomic(path: Path, payload) -> None:
    # Write to a temp file then rename, so a concurrent reader never sees a half-written gzip.
    tmp = path.with_name(f"{path.name}.{os.getpid()}.{threading.get_ident()}.tmp")
    with gzip.open(tmp, "wt", encoding="utf-8") as handle:
        json.dump(payload, handle, separators=(",", ":"))
    os.replace(tmp, path)


def fetch_5m(symbol: str, start_ms: int, end_ms: int, cache_path: Path) -> list[Candle]:
    if cache_path.exists():
        with gzip.open(cache_path, "rt", encoding="utf-8") as handle:
            rows = json.load(handle)
        return [Candle(**row) for row in rows]

    cursor = end_ms
    rows: dict[int, Candle] = {}
    pages = 0
    while cursor >= start_ms:
        query = urllib.parse.urlencode({
            "category": "linear", "symbol": symbol, "interval": "5",
            "limit": 1000, "end": cursor,
        })
        data = request_json(f"https://api.bybit.com/v5/market/kline?{query}")
        if data.get("retCode") != 0:
            raise RuntimeError(f"{symbol}: Bybit error {data.get('retMsg')}")
        page = data.get("result", {}).get("list", [])
        if not page:
            break
        oldest = cursor
        for item in page:
            candle = Candle(t=int(item[0]), o=float(item[1]), h=float(item[2]),
                            l=float(item[3]), c=float(item[4]), v=float(item[5]))
            if start_ms <= candle.t <= end_ms:
                rows[candle.t] = candle
            oldest = min(oldest, candle.t)
        pages += 1
        if oldest >= cursor or oldest <= start_ms:
            break
        cursor = oldest - 1
        time.sleep(0.06)

    candles = sorted(rows.values(), key=lambda c: c.t)
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    write_gz_json_atomic(cache_path, [asdict(c) for c in candles])
    print(f"{symbol}: downloaded {len(candles):,} 5m candles in {pages} pages", flush=True)
    return candles


def aggregate(candles: list[Candle], interval: str) -> list[Candle]:
    bucket_ms = INTERVAL_MS[interval]
    out: list[Candle] = []
    current: Optional[Candle] = None
    for candle in candles:
        bucket = (candle.t // bucket_ms) * bucket_ms
        if current is None or current.t != bucket:
            if current is not None:
                out.append(current)
            current = Candle(bucket, candle.o, candle.h, candle.l, candle.c, candle.v)
        else:
            current.h = max(current.h, candle.h)
            current.l = min(current.l, candle.l)
            current.c = candle.c
            current.v += candle.v
    if current is not None:
        out.append(current)
    return out


def ema(values: list[float], period: int) -> list[Optional[float]]:
    out: list[Optional[float]] = [None] * len(values)
    if len(values) < period:
        return out
    value = sum(values[:period]) / period
    out[period - 1] = value
    alpha = 2 / (period + 1)
    for i in range(period, len(values)):
        value = values[i] * alpha + value * (1 - alpha)
        out[i] = value
    return out


def atr(candles: list[Candle], period: int = 14) -> list[Optional[float]]:
    out: list[Optional[float]] = [None] * len(candles)
    trs: list[float] = []
    for i, candle in enumerate(candles):
        if i == 0:
            tr = candle.h - candle.l
        else:
            prior = candles[i - 1].c
            tr = max(candle.h - candle.l, abs(candle.h - prior), abs(candle.l - prior))
        trs.append(tr)
        if i >= period - 1:
            out[i] = sum(trs[i - period + 1:i + 1]) / period
    return out


def pivots(candles: list[Candle], interval: str, left: int = 2, right: int = 2) -> list[Pivot]:
    out: list[Pivot] = []
    span = INTERVAL_MS[interval]
    for i in range(left, len(candles) - right):
        window = candles[i - left:i + right + 1]
        candle = candles[i]
        if candle.h == max(x.h for x in window) and sum(x.h == candle.h for x in window) == 1:
            out.append(Pivot("high", candle.t, candles[i + right].t + span, candle.h, i))
        if candle.l == min(x.l for x in window) and sum(x.l == candle.l for x in window) == 1:
            out.append(Pivot("low", candle.t, candles[i + right].t + span, candle.l, i))
    return sorted(out, key=lambda p: (p.known_t, p.t, p.kind))


def leg_has_fvg(candles: list[Candle], start_index: int, end_index: int, kind: str) -> bool:
    """Scan the displacement leg (origin candle to the confirming BOS candle,
    inclusive) for a 3-candle Fair Value Gap in the zone's direction: candle
    i's high below candle i+2's low (demand/bullish), or candle i's low above
    candle i+2's high (supply/bearish). Reported-only quality signal - see
    Zone.has_fvg."""
    for i in range(start_index, min(end_index, len(candles) - 3) + 1):
        c1, c3 = candles[i], candles[i + 2]
        if kind == "demand" and c1.h < c3.l:
            return True
        if kind == "supply" and c1.l > c3.h:
            return True
    return False


def source_zones(candles: list[Candle], interval: str) -> list[Zone]:
    """Build source-candle zones after a confirmed break of structure.

    Demand is the lower wick of the last red candle before a rise. Supply is
    the full range of the last green candle before a fall. A rise/fall is
    meaningful when it closes beyond the latest confirmed swing. The zone is
    not usable until that break-of-structure candle closes.
    """
    span = INTERVAL_MS[interval]
    ps = pivots(candles, interval)
    highs = [p for p in ps if p.kind == "high"]
    lows = [p for p in ps if p.kind == "low"]
    high_known = [p.known_t for p in highs]
    low_known = [p.known_t for p in lows]
    zones: list[Zone] = []
    seen: set[tuple[str, int]] = set()
    for j, confirming in enumerate(candles):
        hi = bisect.bisect_right(high_known, confirming.t) - 1
        lo = bisect.bisect_right(low_known, confirming.t) - 1
        kind: Optional[str] = None
        pivot_price: Optional[float] = None
        if hi >= 0 and confirming.c > highs[hi].price:
            kind, pivot_price = "demand", highs[hi].price
        elif lo >= 0 and confirming.c < lows[lo].price:
            kind, pivot_price = "supply", lows[lo].price
        if kind is None:
            continue
        source_index: Optional[int] = None
        for i in range(j - 1, max(-1, j - 4), -1):
            candle = candles[i]
            if kind == "demand" and candle.c < candle.o:
                source_index = i
                break
            if kind == "supply" and candle.c > candle.o:
                source_index = i
                break
        if source_index is None:
            continue
        source = candles[source_index]
        identity = (kind, source.t)
        if identity in seen:
            continue
        seen.add(identity)
        if kind == "demand":
            low, high, pivot_price = source.l, source.c, source.l
        else:
            low, high, pivot_price = source.l, source.h, source.h
        if high <= low:
            continue
        known_t = confirming.t + span
        fvg = leg_has_fvg(candles, source_index, j, kind)
        zones.append(Zone(
            id=f"{interval}-{kind}-{source_index}-{source.t}", kind=kind,
            source_tf=interval, t=source.t, known_t=known_t,
            low=low, high=high, pivot_price=pivot_price, has_fvg=fvg,
        ))
    return zones


def refined_zones(high_candles: list[Candle], high_tf: str,
                  low_candles: list[Candle], low_tf: str) -> list[Zone]:
    high_zones = source_zones(high_candles, high_tf)
    low_zones = source_zones(low_candles, low_tf)
    high_span = INTERVAL_MS[high_tf]
    zones: list[Zone] = []
    for number, parent in enumerate(high_zones):
        candidates = [z for z in low_zones
                      if z.kind == parent.kind
                      and parent.t <= z.t < parent.t + high_span
                      and z.known_t <= parent.known_t
                      and z.low <= parent.high and z.high >= parent.low]
        refined = max(candidates, key=lambda z: (z.t, z.known_t)) if candidates else parent
        low = max(parent.low, refined.low) if candidates else parent.low
        high = min(parent.high, refined.high) if candidates else parent.high
        if high <= low:
            low, high = parent.low, parent.high
        zones.append(Zone(
            id=f"{high_tf}-{low_tf}-{parent.kind}-{number}-{parent.t}",
            kind=parent.kind, source_tf=f"{high_tf}->{low_tf}", t=parent.t,
            known_t=parent.known_t, low=low, high=high,
            pivot_price=parent.pivot_price,
            refined=bool(candidates),
            has_fvg=parent.has_fvg,  # FVG quality is checked at the zone's own
            # origin timeframe (the high_tf parent), not the low_tf refinement -
            # per the timeframe-matching rule (check FVG where the zone was born).
        ))
    return zones


class StructureLookup:
    def __init__(self, candles: list[Candle], interval: str):
        ps = pivots(candles, interval)
        self.highs = [p for p in ps if p.kind == "high"]
        self.lows = [p for p in ps if p.kind == "low"]
        self.high_known = [p.known_t for p in self.highs]
        self.low_known = [p.known_t for p in self.lows]

    def at(self, timestamp: int) -> str:
        hi = bisect.bisect_right(self.high_known, timestamp)
        lo = bisect.bisect_right(self.low_known, timestamp)
        if hi < 2 or lo < 2:
            return "range"
        h1, h2 = self.highs[hi - 2], self.highs[hi - 1]
        l1, l2 = self.lows[lo - 2], self.lows[lo - 1]
        if h2.price > h1.price and l2.price > l1.price:
            return "bullish"
        if h2.price < h1.price and l2.price < l1.price:
            return "bearish"
        return "range"


class SeriesLookup:
    def __init__(self, candles: list[Candle], interval: str, values: list[Optional[float]]):
        self.known = [c.t + INTERVAL_MS[interval] for c in candles]
        self.values = values

    def at(self, timestamp: int) -> Optional[float]:
        index = bisect.bisect_right(self.known, timestamp) - 1
        return self.values[index] if index >= 0 else None


def clone_zones(zones: Iterable[Zone]) -> list[Zone]:
    return [Zone(**asdict(zone)) for zone in zones]


def overlaps(candle: Candle, zone: Zone) -> bool:
    return candle.l <= zone.high and candle.h >= zone.low


def rejection(candle: Candle, zone: Zone, direction: str) -> bool:
    body = abs(candle.c - candle.o)
    body = max(body, max(candle.h - candle.l, 1e-12) * 0.05)
    if direction == "long":
        lower_wick = min(candle.o, candle.c) - candle.l
        return candle.c > candle.o and min(candle.o, candle.c) > zone.high \
            and candle.l <= zone.high and lower_wick >= body
    upper_wick = candle.h - max(candle.o, candle.c)
    return candle.c < candle.o and max(candle.o, candle.c) < zone.low \
        and candle.h >= zone.low and upper_wick >= body


def engulfing(previous: Candle, candle: Candle, zone: Zone, direction: str) -> bool:
    if direction == "long":
        return previous.c < previous.o and candle.c > candle.o \
            and candle.o <= previous.c and candle.c >= previous.o \
            and overlaps(candle, zone) and candle.c > zone.high
    return previous.c > previous.o and candle.c < candle.o \
        and candle.o >= previous.c and candle.c <= previous.o \
        and overlaps(candle, zone) and candle.c < zone.low


def build_tp_ladder(
    entry: float,
    stop: float,
    direction: str,
    opposite: list[Zone],
    min_rr: float = 1.5,
) -> list[dict[str, Any]]:
    risk = abs(entry - stop)
    if risk <= 0:
        return []
    if direction == "long":
        raw_edges = sorted(z.low for z in opposite if not z.invalidated and z.low > entry)
    else:
        raw_edges = sorted((z.high for z in opposite if not z.invalidated and z.high < entry), reverse=True)
    edges: list[float] = []
    for edge in raw_edges:
        if not edges or abs(edge - edges[-1]) > 0.05 * risk:
            edges.append(edge)
    if edges:
        if abs(edges[0] - entry) / risk < min_rr:
            return []
        notes = [
            "1st opposing zone edge",
            "Conditional — after TP1 zone breaks",
            "Conditional — after TP2 zone breaks",
        ]
        return [
            {
                "label": f"TP{idx + 1}",
                "price": edge,
                "rr": round(abs(edge - entry) / risk, 2),
                "source": "zone",
                "note": notes[idx],
            }
            for idx, edge in enumerate(edges[:3])
        ]
    return [
        {
            "label": "TP1",
            "price": entry + 2.0 * risk if direction == "long" else entry - 2.0 * risk,
            "rr": 2.0,
            "source": "r_multiple",
            "note": "No opposing zone - price discovery, full exit at 2R",
        },
    ]


def choose_rr(entry: float, stop: float, direction: str, opposite: list[Zone]) -> tuple[Optional[float], Optional[float]]:
    ladder = build_tp_ladder(entry, stop, direction, opposite)
    if not ladder:
        return None, None
    if ladder[0]["source"] == "zone":
        return float(ladder[0]["rr"]), float(ladder[0]["price"])
    return 2.0, float(ladder[-1]["price"])


def outcome_from_exit(direction: str, entry: float, stop: float, exit_price: float) -> float:
    risk = abs(entry - stop)
    return ((exit_price - entry) if direction == "long" else (entry - exit_price)) / risk


def daily_vwap(candles: list[Candle]) -> list[float]:
    out: list[float] = []
    current_day: Optional[dt.date] = None
    numerator = denominator = 0.0
    for candle in candles:
        day = dt.datetime.fromtimestamp(candle.t / 1000, UTC).date()
        if day != current_day:
            current_day = day
            numerator = denominator = 0.0
        typical = (candle.h + candle.l + candle.c) / 3
        numerator += typical * candle.v
        denominator += candle.v
        out.append(numerator / denominator if denominator else candle.c)
    return out


def make_trade(strategy: str, symbol: str, direction: str, signal_t: int,
               entry_t: int, exit_t: int, entry: float, stop: float, target: float,
               planned_rr: float, exit_price: float, outcome: str, gross_r: float,
               risk_pct: float, cost_pct: float, zone_tf: str, confirmation: str) -> Trade:
    cost_r = (cost_pct / 100.0) * entry / abs(entry - stop)
    return Trade(strategy, symbol, groups_for(symbol), direction, signal_t, entry_t,
                 exit_t, entry, stop, target, planned_rr, exit_price, outcome,
                 gross_r, gross_r - cost_r, risk_pct, cost_pct, zone_tf, confirmation)


def run_intraday(symbol: str, frames: dict[str, list[Candle]], cost_pct: float,
                 state_out: Optional[dict] = None, pending_expiry_candles: Optional[int] = None) -> list[Trade]:
    candles = frames["15"]
    zones = clone_zones(refined_zones(frames["240"], "240", frames["60"], "60"))
    zones.sort(key=lambda z: z.known_t)
    structure = StructureLookup(frames["D"], "D")
    atr_lookup = SeriesLookup(frames["240"], "240", atr(frames["240"]))
    active: list[Zone] = []
    zone_cursor = 0
    trades: list[Trade] = []
    pending: Optional[dict[str, Any]] = None
    position: Optional[dict[str, Any]] = None

    for i, candle in enumerate(candles):
        if candle.t > ms(TEST_END):
            break
        in_test = candle.t >= ms(TEST_START)
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
            elif overlaps(candle, zone):
                if zone.touch_index is None:
                    zone.touch_index = i
            if zone.touch_index is not None and i - zone.touch_index > 4:
                zone.consumed = True

        # Replay the warm-up window to age, consume, and invalidate zones, but
        # never allow it to create a trade included in the requested period.
        if not in_test:
            continue

        if position is not None:
            direction = position["direction"]
            stop_hit = candle.l <= position["stop"] if direction == "long" else candle.h >= position["stop"]
            target_hit = candle.h >= position["target"] if direction == "long" else candle.l <= position["target"]
            if stop_hit or target_hit:
                # Conservative resolution when both occur in one candle.
                if stop_hit:
                    exit_price, outcome, gross_r = position["stop"], "SL", -1.0
                else:
                    exit_price, outcome, gross_r = position["target"], "TP", position["rr"]
                trades.append(make_trade("Intraday", symbol, direction, position["signal_t"],
                                         position["entry_t"], candle.t + INTERVAL_MS["15"], position["entry"],
                                         position["stop"], position["target"], position["rr"], exit_price,
                                         outcome, gross_r, 1.0, cost_pct, position["zone_tf"], position["confirmation"]))
                position = None
            continue

        if pending is not None:
            zone = pending["zone"]
            invalid = candle.l <= pending["stop"] if pending["direction"] == "long" else candle.h >= pending["stop"]
            filled = candle.l <= pending["entry"] <= candle.h
            # Backtest switch only: the live engine passes no expiry.
            expired = (pending_expiry_candles is not None
                       and candle.t - pending["signal_t"] > pending_expiry_candles * INTERVAL_MS["15"])
            if invalid or expired:
                pending = None
            elif filled:
                position = {**pending, "entry_t": candle.t}
                pending = None
                # Resolve fill-bar ambiguity conservatively.
                direction = position["direction"]
                stop_hit = candle.l <= position["stop"] if direction == "long" else candle.h >= position["stop"]
                target_hit = candle.h >= position["target"] if direction == "long" else candle.l <= position["target"]
                if stop_hit or target_hit:
                    if stop_hit:
                        exit_price, result, gross_r = position["stop"], "SL", -1.0
                    else:
                        exit_price, result, gross_r = position["target"], "TP", position["rr"]
                    trades.append(make_trade("Intraday", symbol, direction, position["signal_t"], candle.t,
                                             candle.t + INTERVAL_MS["15"], position["entry"], position["stop"],
                                             position["target"], position["rr"], exit_price, result, gross_r,
                                             1.0, cost_pct, position["zone_tf"], position["confirmation"]))
                    position = None
            continue

        bias = structure.at(candle.t)
        if bias == "range" or i == 0:
            continue
        direction = "long" if bias == "bullish" else "short"
        kind = "demand" if direction == "long" else "supply"
        candidates = [z for z in active if z.kind == kind and not z.invalidated and not z.consumed
                      and z.touch_index is not None and 0 <= i - z.touch_index <= 4]
        candidates.sort(key=lambda z: (abs(candle.c - z.proximal), -z.known_t))
        for zone in candidates:
            confirmation = "Rejection" if rejection(candle, zone, direction) else \
                           "Engulfing" if engulfing(candles[i - 1], candle, zone, direction) else ""
            if not confirmation:
                continue
            current_atr = atr_lookup.at(candle.t)
            if not current_atr:
                continue
            entry = zone.proximal
            stop = zone.low - 0.50 * current_atr if direction == "long" else zone.high + 0.50 * current_atr
            opposite = [z for z in active if z.kind != kind and z.known_t <= candle.t and not z.invalidated]
            rr, target = choose_rr(entry, stop, direction, opposite)
            zone.consumed = True
            if rr is None or target is None:
                break
            pending = {"direction": direction, "signal_t": candle.t, "entry": entry, "stop": stop,
                       "target": target, "rr": rr, "zone_tf": zone.source_tf,
                       "confirmation": confirmation, "zone": zone}
            break

    # Live-read hook: exposes end-of-replay zone, pending-order and position state.
    if state_out is not None:
        state_out.update(active=active, pending=pending, position=position)

    if position is not None and candles:
        final = next((c for c in reversed(candles) if c.t <= ms(TEST_END)), candles[-1])
        trades.append(make_trade("Intraday", symbol, position["direction"], position["signal_t"],
                                 position["entry_t"], final.t + INTERVAL_MS["15"], position["entry"],
                                 position["stop"], position["target"], position["rr"], final.c,
                                 "OPEN", 0.0, 1.0, 0.0, position["zone_tf"], position["confirmation"]))
    return trades


def run_scalp(symbol: str, frames: dict[str, list[Candle]], cost_pct: float) -> list[Trade]:
    candles = frames["5"]
    closes = [c.c for c in candles]
    e9, e20 = ema(closes, 9), ema(closes, 20)
    vwaps = daily_vwap(candles)
    zones = clone_zones(refined_zones(frames["60"], "60", frames["15"], "15"))
    zones.sort(key=lambda z: z.known_t)
    structure = StructureLookup(frames["240"], "240")
    atr_lookup = SeriesLookup(frames["240"], "240", atr(frames["240"]))
    active: list[Zone] = []
    zone_cursor = 0
    trades: list[Trade] = []
    position: Optional[dict[str, Any]] = None

    for i, candle in enumerate(candles):
        if candle.t > ms(TEST_END):
            break
        in_test = candle.t >= ms(TEST_START)
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

        # Replay warm-up candles so pre-period zones are not falsely treated as
        # untouched on the first test day.
        if not in_test:
            continue

        if position is not None:
            direction = position["direction"]
            stop_hit = candle.l <= position["stop"] if direction == "long" else candle.h >= position["stop"]
            target_hit = candle.h >= position["target"] if direction == "long" else candle.l <= position["target"]
            if stop_hit or target_hit:
                if stop_hit:
                    exit_price, result, gross_r = position["stop"], "SL", -1.0
                elif target_hit:
                    exit_price, result, gross_r = position["target"], "TP", position["rr"]
                trades.append(make_trade("Scalp", symbol, direction, position["signal_t"], position["entry_t"],
                                         candle.t + INTERVAL_MS["5"], position["entry"], position["stop"],
                                         position["target"], position["rr"], exit_price, result, gross_r,
                                         0.5, cost_pct, position["zone_tf"], "EMA+VWAP+zone"))
                position = None
            continue

        if i < 20 or e9[i] is None or e20[i] is None or e9[i - 1] is None or e20[i - 1] is None:
            continue
        bull_cross = e9[i - 1] <= e20[i - 1] and e9[i] > e20[i]
        bear_cross = e9[i - 1] >= e20[i - 1] and e9[i] < e20[i]
        bull_slope = e9[i] > e9[i - 1] and e20[i] > e20[i - 1]
        bear_slope = e9[i] < e9[i - 1] and e20[i] < e20[i - 1]
        bias = structure.at(candle.t)
        if bull_cross and bull_slope and candle.c > vwaps[i] and bias == "bullish":
            direction, kind = "long", "demand"
        elif bear_cross and bear_slope and candle.c < vwaps[i] and bias == "bearish":
            direction, kind = "short", "supply"
        else:
            continue
        candidates = [z for z in active if z.kind == kind and not z.invalidated and not z.consumed
                      and (z.proximal <= candle.c if direction == "long" else z.proximal >= candle.c)]
        candidates.sort(key=lambda z: (abs(candle.c - z.proximal), -z.known_t))
        if not candidates:
            continue
        zone = candidates[0]
        current_atr = atr_lookup.at(candle.t)
        if not current_atr:
            continue
        entry = candle.c
        stop = zone.low - 0.50 * current_atr if direction == "long" else zone.high + 0.50 * current_atr
        if direction == "long" and stop >= entry or direction == "short" and stop <= entry:
            zone.consumed = True
            continue
        opposite = [z for z in active if z.kind != kind and z.known_t <= candle.t and not z.invalidated]
        rr, target = choose_rr(entry, stop, direction, opposite)
        zone.consumed = True
        if rr is None or target is None:
            continue
        position = {"direction": direction, "signal_t": candle.t, "entry_t": candle.t + INTERVAL_MS["5"],
                    "entry_index": i, "entry": entry, "stop": stop, "target": target,
                    "rr": rr, "zone_tf": zone.source_tf}

    if position is not None and candles:
        final = next((c for c in reversed(candles) if c.t <= ms(TEST_END)), candles[-1])
        trades.append(make_trade("Scalp", symbol, position["direction"], position["signal_t"],
                                 position["entry_t"], final.t + INTERVAL_MS["5"], position["entry"],
                                 position["stop"], position["target"], position["rr"], final.c,
                                 "OPEN", 0.0, 0.5, 0.0, position["zone_tf"], "EMA+VWAP+zone"))
    return trades


def apply_portfolio_limits(trades: list[Trade], max_daily_loss_pct: float = 3.0,
                           max_open_risk_pct: float = 3.0) -> list[Trade]:
    accepted: list[Trade] = []
    daily_realized: dict[str, float] = {}
    for trade in sorted(trades, key=lambda t: (t.entry_t, t.symbol, t.strategy)):
        entry_day = dt.datetime.fromtimestamp(trade.entry_t / 1000, UTC).date().isoformat()
        # Realize prior accepted exits before testing the new entry.
        for prior in accepted:
            key = f"{prior.strategy}:{prior.exit_t}"
            if getattr(prior, "_limit_realized", False):
                continue
            if prior.exit_t <= trade.entry_t:
                exit_day = dt.datetime.fromtimestamp(prior.exit_t / 1000, UTC).date().isoformat()
                daily_realized[exit_day] = daily_realized.get(exit_day, 0.0) + prior.net_r * prior.risk_pct
                setattr(prior, "_limit_realized", True)
        open_risk = sum(t.risk_pct for t in accepted if t.entry_t <= trade.entry_t < t.exit_t)
        if daily_realized.get(entry_day, 0.0) <= -max_daily_loss_pct:
            trade.accepted = False
            trade.portfolio_skip_reason = "3% daily realized-loss cap"
        elif open_risk + trade.risk_pct > max_open_risk_pct + 1e-9:
            trade.accepted = False
            trade.portfolio_skip_reason = "3% simultaneous open-risk cap"
        else:
            accepted.append(trade)
    # Clean temporary attributes from accepted trades.
    for trade in accepted:
        if hasattr(trade, "_limit_realized"):
            delattr(trade, "_limit_realized")
    return trades


def stats(trades: list[Trade], accepted_only: bool = True) -> dict[str, Any]:
    selected = [t for t in trades if t.accepted or not accepted_only]
    open_trades = [t for t in selected if t.outcome == "OPEN"]
    resolved = [t for t in selected if t.outcome != "OPEN"]
    wins = [t for t in resolved if t.net_r > 0]
    losses = [t for t in resolved if t.net_r < 0]
    flats = [t for t in resolved if abs(t.net_r) < 1e-12]
    tp = [t for t in resolved if t.outcome == "TP"]
    sl = [t for t in resolved if t.outcome == "SL"]
    net = [t.net_r for t in resolved]
    gross_profit = sum(x for x in net if x > 0)
    gross_loss = -sum(x for x in net if x < 0)
    equity = peak = drawdown = 0.0
    for trade in sorted(resolved, key=lambda t: t.exit_t):
        equity += trade.net_r * trade.risk_pct
        peak = max(peak, equity)
        drawdown = max(drawdown, peak - equity)
    count = len(resolved)
    return {
        "trades": count, "open_trades": len(open_trades), "wins": len(wins), "losses": len(losses), "flats": len(flats),
        "success_rate": len(wins) / count if count else None,
        "failure_rate": len(losses) / count if count else None,
        "tp_rate": len(tp) / count if count else None,
        "sl_rate": len(sl) / count if count else None,
        "avg_net_r": statistics.fmean(net) if net else None,
        "median_net_r": statistics.median(net) if net else None,
        "total_net_r": sum(net),
        "portfolio_return_pct": sum(t.net_r * t.risk_pct for t in resolved),
        "profit_factor": gross_profit / gross_loss if gross_loss else None,
        "max_drawdown_pct": drawdown,
        "skipped_by_limits": sum(1 for t in trades if not t.accepted),
    }


def coverage(symbol: str, candles: list[Candle]) -> dict[str, Any]:
    test = [c for c in candles if ms(TEST_START) <= c.t <= ms(TEST_END)]
    if not test:
        return {"symbol": symbol, "first_utc": None, "last_utc": None, "bars_5m": 0,
                "coverage_days": 0.0, "gap_count": 0, "coverage_pct": 0.0}
    gaps = sum(1 for a, b in zip(test, test[1:]) if b.t - a.t > INTERVAL_MS["5"])
    expected = max(1, int((min(ms(TEST_END), test[-1].t) - max(ms(TEST_START), test[0].t)) /
                          INTERVAL_MS["5"]) + 1)
    return {"symbol": symbol, "first_utc": iso(test[0].t), "last_utc": iso(test[-1].t),
            "bars_5m": len(test), "coverage_days": (test[-1].t - test[0].t) / 86_400_000,
            "gap_count": gaps, "coverage_pct": len(test) / expected if expected else None}


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        return
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="backtests/2026-08-01-strategy-rerun")
    parser.add_argument("--symbols", nargs="*", default=unique_symbols())
    parser.add_argument("--intraday-cost-pct", type=float, default=0.0,
                        help="Round-trip fees + slippage as percent of notional")
    parser.add_argument("--scalp-cost-pct", type=float, default=0.0,
                        help="Round-trip fees + slippage as percent of notional")
    args = parser.parse_args()
    output = Path(args.output)
    cache = output / "data"
    all_trades: dict[str, list[Trade]] = {"Intraday": [], "Scalp": []}
    coverages: list[dict[str, Any]] = []

    for symbol in args.symbols:
        try:
            five = fetch_5m(symbol, ms(WARMUP_START), ms(TEST_END), cache / f"{symbol}_5m.json.gz")
        except Exception as exc:
            print(f"{symbol}: DATA ERROR: {exc}", flush=True)
            coverages.append({"symbol": symbol, "first_utc": None, "last_utc": None, "bars_5m": 0,
                              "coverage_days": 0.0, "gap_count": 0, "coverage_pct": 0.0,
                              "error": str(exc)})
            continue
        coverages.append(coverage(symbol, five))
        frames = {"5": five}
        for interval in ("15", "60", "240", "D"):
            frames[interval] = aggregate(five, interval)
        intraday = run_intraday(symbol, frames, args.intraday_cost_pct)
        scalp = run_scalp(symbol, frames, args.scalp_cost_pct)
        all_trades["Intraday"].extend(intraday)
        all_trades["Scalp"].extend(scalp)
        print(f"{symbol}: intraday={len(intraday)} scalp={len(scalp)}", flush=True)

    for strategy in ("Intraday", "Scalp"):
        apply_portfolio_limits(all_trades[strategy])

    detail = [trade.row() for strategy in ("Intraday", "Scalp") for trade in all_trades[strategy]]
    per_coin: list[dict[str, Any]] = []
    for symbol in args.symbols:
        for strategy in ("Intraday", "Scalp"):
            subset = [t for t in all_trades[strategy] if t.symbol == symbol]
            row = {"symbol": symbol, "groups": groups_for(symbol), "strategy": strategy, **stats(subset)}
            per_coin.append(row)
    portfolio = []
    for strategy in ("Intraday", "Scalp"):
        portfolio.append({"strategy": strategy, **stats(all_trades[strategy])})

    assumptions = {
        "test_start_utc": TEST_START.isoformat(), "test_end_utc": TEST_END.isoformat(),
        "warmup_start_utc": WARMUP_START.isoformat(), "source": "Bybit public linear kline API",
        "source_url": "https://api.bybit.com/v5/market/kline",
        "symbols": args.symbols, "excluded": ["BTCUSDT (ledger context-only)"],
        "intraday": {
            "structure": "1D last two confirmed fractal highs/lows (2 left, 2 right)",
            "zones": "Last red 4H source candle before a bullish close above the latest confirmed swing high (lower-wick demand), or last green candle before a bearish close below the latest confirmed swing low (full-range supply), refined to a matching 1H source candle",
            "confirmation": "15m directional rejection or body-engulfing candle at first retest",
            "entry": "limit at proximal/entry line until filled or zone invalidation",
            "stop": "beyond distal/exit line by 0.50 x prior completed 4H ATR(14)",
            "target": "first opposing zone edge if >= 1.5R; 2R when no zone ahead; otherwise skip",
            "risk": "1% per trade; 3% daily/open-risk portfolio caps",
            "exit": "TP or SL only; positions still open at test end are unresolved",
            "cost_pct_round_trip": args.intraday_cost_pct,
        },
        "scalp": {
            "structure": "4H last two confirmed fractal highs/lows (2 left, 2 right)",
            "zones": "Last red 1H source candle before a bullish close above the latest confirmed swing high (lower-wick demand), or last green candle before a bearish close below the latest confirmed swing low (full-range supply), refined to a matching 15m source candle",
            "confirmation": "5m 9/20 EMA cross; both EMA slopes agree; daily UTC VWAP reported as context only; 4H trend agrees; nearest valid 15m-refined zone provides stop context",
            "entry": "market at crossover candle close",
            "stop": "beyond 15m-refined distal line by 0.50 x prior completed 4H ATR(14)",
            "target": "first opposing zone edge if >= 1.5R; 2R when no zone ahead; otherwise skip",
            "risk": "0.5% per trade; 3% daily/open-risk portfolio caps",
            "vwap_reset": "00:00 UTC daily",
            "max_hold": "None; TP or SL only; positions still open at test end are unresolved",
            "cost_pct_round_trip": args.scalp_cost_pct,
        },
        "conservative_rules": [
            "No lookahead: a source zone becomes available only after its displacement-confirmation candle closes",
            "A zone is consumed after its first retest/confirmation window",
            "If stop and target touch within the same candle, stop is counted first",
            "Only one position per symbol per strategy; global 3% simultaneous risk cap",
            "No forced time exits; unresolved positions are excluded from success/failure and return",
            "Liquidation is not modelled because leverage and margin mode were not specified; the stop is assumed to execute first",
            "Trading costs are ignored at the user's request",
        ],
    }
    output.mkdir(parents=True, exist_ok=True)
    write_csv(output / "trade_detail.csv", detail)
    write_csv(output / "per_coin_summary.csv", per_coin)
    write_csv(output / "data_coverage.csv", coverages)
    with (output / "backtest_results.json").open("w", encoding="utf-8") as handle:
        json.dump({"assumptions": assumptions, "portfolio": portfolio, "per_coin": per_coin,
                   "coverage": coverages, "trades": detail}, handle, indent=2)
    print(json.dumps({"portfolio": portfolio, "trade_count": len(detail)}, indent=2), flush=True)


if __name__ == "__main__":
    main()
