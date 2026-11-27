import type { SeriesMarker, UTCTimestamp } from "lightweight-charts";
import { CHART_CANDLE_LIMIT, TF_MINUTES } from "../constants/analyzer";
import { MS_PER_MINUTE } from "../constants/time";
import type { SignalHistoryEntry } from "../types/analyzer";
import type { ActiveBoxSpec } from "../types/chart";
import type { INullable } from "../types/common";
import { SignalOutcome } from "../types/enums";
import { historyExitPrice } from "./historyText";
import { parseEngineStamp } from "./time";

/**
 * @function pickTradeTf
 * @description The preferred timeframe, or the next one up whose loaded candles still reach the signal.
 */
export function pickTradeTf({ item }: { item: SignalHistoryEntry }): string {
  const preferred = item.mode === "Intraday" ? "60" : "15";
  if (!item.startMs) return preferred;
  const age = Date.now() - item.startMs;
  const covering = [preferred, "60", "240"].find((tf) => age < TF_MINUTES[tf] * CHART_CANDLE_LIMIT * MS_PER_MINUTE);
  return covering ?? "240";
}

/**
 * @function tradeBox
 * @description Box spec for a recorded signal, ending at its exit when it has one.
 */
export function tradeBox({ item }: { item: SignalHistoryEntry }): INullable<ActiveBoxSpec> {
  const { direction, entry, stop, target, startMs, closedAtUtc, seenAtUtc } = item;
  if (!direction || entry === undefined || stop === undefined || target === undefined || !startMs) return null;
  const closed = closedAtUtc ? parseEngineStamp({ stampUtc: closedAtUtc, seenIsoUtc: seenAtUtc }) : null;
  return {
    label: "Past",
    direction,
    entry,
    stop,
    target,
    rr: Number((Math.abs(target - entry) / Math.abs(entry - stop)).toFixed(2)),
    // One millisecond back lands on the candle that closed at the stamp.
    entryTimeSec: Math.floor((startMs - 1) / 1000),
    exitTimeSec: closed ? Math.floor((closed.getTime() - 1) / 1000) : null,
  };
}

/**
 * @function candleAt
 * @description Open time of the loaded candle that contains a moment, if the chart reaches back that far.
 */
export function candleAt({ candleTimes, timeSec }: { candleTimes: number[]; timeSec: number }): INullable<number> {
  return candleTimes.filter((time) => time <= timeSec).pop() ?? null;
}

export function tradeMarkers({
  item,
  box,
  candleTimes,
}: {
  item: SignalHistoryEntry;
  box: ActiveBoxSpec;
  candleTimes: number[];
}): SeriesMarker<UTCTimestamp>[] {
  const long = box.direction === "long";
  const markers: SeriesMarker<UTCTimestamp>[] = [];
  const entryTime = candleAt({ candleTimes, timeSec: box.entryTimeSec });
  if (entryTime !== null) {
    markers.push({
      time: entryTime as UTCTimestamp,
      position: long ? "belowBar" : "aboveBar",
      shape: long ? "arrowUp" : "arrowDown",
      color: "#38bdf8",
      text: "Signal",
    });
  }
  const exitTime = box.exitTimeSec ? candleAt({ candleTimes, timeSec: box.exitTimeSec }) : null;
  if (exitTime !== null && historyExitPrice({ item }) !== null) {
    const won = item.outcome === SignalOutcome.Win;
    markers.push({
      time: exitTime as UTCTimestamp,
      position: won === long ? "aboveBar" : "belowBar",
      shape: "circle",
      color: won ? "#22c55e" : "#ef4444",
      text: won ? "Target hit" : "Stop hit",
    });
  }
  return markers;
}
