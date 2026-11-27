import type { IChartApi, ISeriesApi, UTCTimestamp } from "lightweight-charts";
import {
  MIN_ZONE_BAND_PX,
  ZONE_FILL_DEMAND,
  ZONE_FILL_SUPPLY,
  ZONE_FILL_USED_DEMAND,
  ZONE_FILL_USED_SUPPLY,
  ZONE_LABEL_MIN_GAP_PX,
} from "../constants/analyzer";
import type { ZoneInfo } from "../types/analyzer";
import type { ZoneBand } from "../types/chart";
import { mergeZones } from "./mergeZones";

/**
 * @function hideCrowdedLabels
 * @description Blanks a repeated label that would print on top of the same label.
 */
function hideCrowdedLabels(bands: ZoneBand[]): ZoneBand[] {
  return bands.map((band, idx) => {
    const crowded = bands
      .slice(0, idx)
      .some((other) => other.label === band.label && Math.abs(other.top - band.top) < ZONE_LABEL_MIN_GAP_PX);
    return crowded ? { ...band, label: "" } : band;
  });
}

/**
 * @function buildZoneBands
 * @description Maps zones to chart-pixel bands that start at each zone's source candle.
 */
export function buildZoneBands({
  chart,
  series,
  zones,
  candleTimes,
}: {
  chart: IChartApi;
  series: ISeriesApi<"Candlestick">;
  zones: ZoneInfo[];
  candleTimes: number[];
}): ZoneBand[] {
  const bands: ZoneBand[] = [];
  mergeZones({ zones }).forEach((zone, idx) => {
    const yHigh = series.priceToCoordinate(zone.high);
    const yLow = series.priceToCoordinate(zone.low);
    if (yHigh === null || yLow === null) return;
    const demand = zone.kind === "demand";
    const firstTime = candleTimes[0];
    const olderThanChart = zone.timeSec === undefined || firstTime === undefined || zone.timeSec < firstTime;
    const originTime = olderThanChart ? undefined : candleTimes.filter((t) => t <= (zone.timeSec as number)).pop();
    const xOrigin = originTime === undefined ? 0 : chart.timeScale().timeToCoordinate(originTime as UTCTimestamp) ?? 0;
    const used = zone.consumed;
    bands.push({
      key: `${zone.kind}-${zone.low}-${zone.high}-${idx}`,
      kind: zone.kind,
      label: `${demand ? "Demand" : "Supply"} ${zone.tfLabels.join(" + ")}${zone.isTarget ? " - target" : ""}`,
      left: Math.max(0, Math.round(xOrigin)),
      top: Math.min(yHigh, yLow),
      height: Math.max(MIN_ZONE_BAND_PX, Math.abs(yLow - yHigh)),
      consumed: used,
      fill: demand ? (used ? ZONE_FILL_USED_DEMAND : ZONE_FILL_DEMAND) : used ? ZONE_FILL_USED_SUPPLY : ZONE_FILL_SUPPLY,
    });
  });
  // A band wholly above the chart gets no label, or it would be pulled into view.
  return hideCrowdedLabels(bands.map((band) => (band.top + band.height <= 0 ? { ...band, label: "" } : band)));
}
