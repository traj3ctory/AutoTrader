import { onBeforeUnmount, onMounted, ref, watch, type Ref } from "vue";
import {
  CandlestickSeries,
  LineSeries,
  LineStyle,
  createChart,
  type AutoscaleInfo,
  type IChartApi,
  type IPriceLine,
  type ISeriesApi,
  type UTCTimestamp,
} from "lightweight-charts";
import { BOX_FUTURE_WIDTH_PX, BOX_GAP_PX, CHART_RIGHT_OFFSET_BARS, MAX_SCALP_AGE_CANDLES } from "../constants/analyzer";
import type { AnalyzeResponse } from "../types/analyzer";
import type { ActiveBoxSpec, PositionBoxCoords } from "../types/chart";
import type { INullable } from "../types/common";

/**
 * @function pickActiveBox
 * @description Selects the primary fresh setup box in priority order (Scalp EMA -> Intraday Limit); Scalp Zone is context only.
 */
function pickActiveBox(analysis: AnalyzeResponse): INullable<ActiveBoxSpec> {
  const { scalp, intraday } = analysis;
  const scalpFresh =
    scalp.verdictKind === "VALID" ||
    scalp.verdictKind === "LATE_ENTRY" ||
    (scalp.verdictKind === "ENGINE_IN_TRADE" && (scalp.position?.ageCandles ?? 0) <= MAX_SCALP_AGE_CANDLES);

  if (scalp.position && scalpFresh) {
    return { label: "Scalp", ...scalp.position };
  }
  if (intraday.pending && intraday.verdictKind === "VALID") {
    return { label: "Limit", ...intraday.pending };
  }
  return null;
}

/**
 * @function useCandleChart
 * @description Manages the Lightweight Charts instance, EMA visibility, zone lines, and position box overlay.
 */
export function useCandleChart({
  containerRef,
  analysis,
  selectedTf,
}: {
  containerRef: Ref<INullable<HTMLElement>>;
  analysis: () => INullable<AnalyzeResponse>;
  selectedTf: () => string;
}) {
  const showEma = ref(selectedTf() === "5");
  const positionBox = ref<INullable<PositionBoxCoords>>(null);
  let activeBox: INullable<ActiveBoxSpec> = null;
  let lastCandleTime: INullable<UTCTimestamp> = null;
  let candleTimes: number[] = [];
  let chart: INullable<IChartApi> = null;
  let candleSeries: INullable<ISeriesApi<"Candlestick">> = null;
  let ema9Series: INullable<ISeriesApi<"Line">> = null;
  let ema20Series: INullable<ISeriesApi<"Line">> = null;
  let priceLines: IPriceLine[] = [];
  let linePrices: number[] = [];
  let resizeObserver: INullable<ResizeObserver> = null;

  function applyEmaVisibility() {
    ema9Series?.applyOptions({ visible: showEma.value });
    ema20Series?.applyOptions({ visible: showEma.value });
  }

  function toggleEma() {
    showEma.value = !showEma.value;
    applyEmaVisibility();
  }

  function clearPriceLines() {
    linePrices = [];
    if (!candleSeries) {
      priceLines = [];
      return;
    }
    for (const line of priceLines) {
      candleSeries.removePriceLine(line);
    }
    priceLines = [];
  }

  function addZoneLine({ price, title, color }: { price: number; title: string; color: string }) {
    if (!candleSeries || !Number.isFinite(price)) return;
    priceLines.push(
      candleSeries.createPriceLine({
        price,
        color,
        lineWidth: 1,
        lineStyle: LineStyle.Dashed,
        axisLabelVisible: true,
        title,
      })
    );
  }

  function updatePositionBox() {
    if (!chart || !candleSeries || !activeBox) {
      positionBox.value = null;
      return;
    }
    const yEntry = candleSeries.priceToCoordinate(activeBox.entry);
    const yStop = candleSeries.priceToCoordinate(activeBox.stop);
    const yTarget = candleSeries.priceToCoordinate(activeBox.target);
    const xEdge = lastCandleTime !== null ? chart.timeScale().timeToCoordinate(lastCandleTime) : null;
    if (yEntry === null || yStop === null || yTarget === null || xEdge === null) {
      positionBox.value = null;
      return;
    }
    positionBox.value = {
      ...activeBox,
      rewardTop: Math.min(yEntry, yTarget),
      rewardHeight: Math.max(2, Math.abs(yEntry - yTarget)),
      riskTop: Math.min(yEntry, yStop),
      riskHeight: Math.max(2, Math.abs(yStop - yEntry)),
      entryTop: yEntry,
      left: Math.round(xEdge) + BOX_GAP_PX,
      width: BOX_FUTURE_WIDTH_PX,
    };
  }

  function renderData() {
    const current = analysis();
    if (!chart || !candleSeries || !ema9Series || !ema20Series || !current) return;
    const candles = current.candles || [];
    candleTimes = candles.map((c) => c.time);
    lastCandleTime = candles.length > 0 ? (candles[candles.length - 1].time as UTCTimestamp) : null;
    candleSeries.setData(
      candles.map((c) => ({ time: c.time as UTCTimestamp, open: c.open, high: c.high, low: c.low, close: c.close }))
    );
    ema9Series.setData(
      candles.filter((c) => c.ema9 !== null).map((c) => ({ time: c.time as UTCTimestamp, value: c.ema9 as number }))
    );
    ema20Series.setData(
      candles.filter((c) => c.ema20 !== null).map((c) => ({ time: c.time as UTCTimestamp, value: c.ema20 as number }))
    );

    clearPriceLines();
    activeBox = pickActiveBox(current);
    if (activeBox) {
      linePrices.push(activeBox.entry, activeBox.stop, activeBox.target);
    }
    if (current.intraday.long.nearestZone) {
      addZoneLine({ price: current.intraday.long.nearestZone.low, title: "Demand Low", color: "#22c55e" });
      addZoneLine({ price: current.intraday.long.nearestZone.high, title: "Demand High", color: "#22c55e" });
    }
    if (current.intraday.short.nearestZone) {
      addZoneLine({ price: current.intraday.short.nearestZone.low, title: "Supply Low", color: "#ef4444" });
      addZoneLine({ price: current.intraday.short.nearestZone.high, title: "Supply High", color: "#ef4444" });
    }
    chart.priceScale("right").applyOptions({ autoScale: true });
    chart.timeScale().fitContent();
    updatePositionBox();
    window.requestAnimationFrame(updatePositionBox);
  }

  onMounted(() => {
    if (!containerRef.value) return;
    chart = createChart(containerRef.value, {
      layout: { background: { color: "#111827" }, textColor: "#9ca3af" },
      grid: { vertLines: { color: "#1f2937" }, horzLines: { color: "#1f2937" } },
      rightPriceScale: { borderColor: "#243047" },
      timeScale: { borderColor: "#243047", timeVisible: true, rightOffset: CHART_RIGHT_OFFSET_BARS },
      width: containerRef.value.clientWidth,
      height: containerRef.value.clientHeight,
    });
    const priceFormat = { type: "price" as const, precision: 4, minMove: 0.0001 };
    candleSeries = chart.addSeries(CandlestickSeries, {
      upColor: "#22c55e",
      downColor: "#ef4444",
      borderVisible: false,
      wickUpColor: "#22c55e",
      wickDownColor: "#ef4444",
      priceFormat,
      autoscaleInfoProvider: (original: () => INullable<AutoscaleInfo>) => {
        const res = original();
        if (!res || !res.priceRange || linePrices.length === 0) return res;
        return {
          priceRange: {
            minValue: Math.min(res.priceRange.minValue, ...linePrices),
            maxValue: Math.max(res.priceRange.maxValue, ...linePrices),
          },
          margins: res.margins,
        };
      },
    });
    ema9Series = chart.addSeries(LineSeries, {
      color: "#38bdf8",
      lineWidth: 1,
      visible: showEma.value,
      priceLineVisible: false,
      lastValueVisible: false,
      priceFormat,
    });
    ema20Series = chart.addSeries(LineSeries, {
      color: "#f59e0b",
      lineWidth: 1,
      visible: showEma.value,
      priceLineVisible: false,
      lastValueVisible: false,
      priceFormat,
    });
    resizeObserver = new ResizeObserver((entries) => {
      const entry = entries[0];
      if (entry && chart) {
        chart.applyOptions({
          width: Math.floor(entry.contentRect.width),
          height: Math.floor(entry.contentRect.height),
        });
        updatePositionBox();
      }
    });
    resizeObserver.observe(containerRef.value);
    chart.timeScale().subscribeVisibleLogicalRangeChange(updatePositionBox);
    renderData();
  });

  watch(analysis, renderData);
  watch(selectedTf, (tf) => {
    showEma.value = tf === "5";
    applyEmaVisibility();
  });

  onBeforeUnmount(() => {
    resizeObserver?.disconnect();
    chart?.remove();
    chart = null;
  });

  return { showEma, toggleEma, positionBox, updatePositionBox };
}
