import type { IChartApi, ISeriesApi, UTCTimestamp } from "lightweight-charts";
import { BOX_FUTURE_WIDTH_PX, BOX_GAP_PX, PAST_TRADE_MIN_BOX_PX } from "../constants/analyzer";
import type { ActiveBoxSpec, PositionBoxCoords } from "../types/chart";
import type { INullable } from "../types/common";
import { candleAt } from "./tradeReplay";

// A live setup sits right of the latest candle; a past trade spans signal to exit.
function horizontalSpan({ chart, box, candleTimes }: { chart: IChartApi; box: ActiveBoxSpec; candleTimes: number[] }) {
  const xOf = (time: INullable<number>) => (time === null || time === undefined ? null : chart.timeScale().timeToCoordinate(time as UTCTimestamp));
  const lastX = xOf(candleTimes[candleTimes.length - 1]);
  if (box.label !== "Past") {
    return lastX === null ? null : { left: Math.round(lastX) + BOX_GAP_PX, width: BOX_FUTURE_WIDTH_PX };
  }
  const startX = xOf(candleAt({ candleTimes, timeSec: box.entryTimeSec }));
  const endX = box.exitTimeSec ? xOf(candleAt({ candleTimes, timeSec: box.exitTimeSec })) : lastX;
  if (startX === null || endX === null) return null;
  return { left: Math.round(startX), width: Math.max(PAST_TRADE_MIN_BOX_PX, Math.round(endX - startX)) };
}

/**
 * @function buildPositionBox
 * @description Converts a box spec into chart pixel coordinates.
 */
export function buildPositionBox({
  chart,
  series,
  box,
  candleTimes,
}: {
  chart: IChartApi;
  series: ISeriesApi<"Candlestick">;
  box: ActiveBoxSpec;
  candleTimes: number[];
}): INullable<PositionBoxCoords> {
  const yEntry = series.priceToCoordinate(box.entry);
  const yStop = series.priceToCoordinate(box.stop);
  const yTarget = series.priceToCoordinate(box.target);
  const span = horizontalSpan({ chart, box, candleTimes });
  if (yEntry === null || yStop === null || yTarget === null || !span) return null;
  return {
    ...box,
    ...span,
    rewardTop: Math.min(yEntry, yTarget),
    rewardHeight: Math.max(2, Math.abs(yEntry - yTarget)),
    riskTop: Math.min(yEntry, yStop),
    riskHeight: Math.max(2, Math.abs(yStop - yEntry)),
    entryTop: yEntry,
  };
}
