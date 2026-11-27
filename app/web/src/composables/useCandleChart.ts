import { onBeforeUnmount, onMounted, ref, watch, type Ref } from "vue";
import {
  CandlestickSeries,
  LineSeries,
  LineStyle,
  createChart,
  createSeriesMarkers,
  type AutoscaleInfo,
  type IChartApi,
  type IPriceLine,
  type ISeriesApi,
  type ISeriesMarkersPluginApi,
  type Time,
  type UTCTimestamp,
} from "lightweight-charts";
import {
  CHART_RIGHT_OFFSET_BARS,
  INITIAL_VISIBLE_BARS,
  ORIGIN_PADDING_BARS,
  PAST_TRADE_PADDING_BARS,
} from "../constants/analyzer";
import { buildZoneBands } from "../utils/zoneBands";
import type { AnalyzeResponse, SignalHistoryEntry, ZoneInfo } from "../types/analyzer";
import type { ActiveBoxSpec, PositionBoxCoords, ZoneBand } from "../types/chart";
import type { INullable } from "../types/common";
import { chartPriceFormat } from "../utils/price";
import { pickActiveBox, pickChartZones } from "../utils/activeBox";
import { buildPositionBox } from "../utils/positionBox";
import { candleAt, tradeBox, tradeMarkers } from "../utils/tradeReplay";

/**
 * @function useCandleChart
 * @description Manages the Lightweight Charts instance, EMA visibility, zone lines, and position box overlay.
 */
export function useCandleChart({
  containerRef,
  analysis,
  selectedTf,
  trade,
}: {
  containerRef: Ref<INullable<HTMLElement>>;
  analysis: () => INullable<AnalyzeResponse>;
  selectedTf: () => string;
  trade: () => INullable<SignalHistoryEntry>;
}) {
  const showEma = ref(selectedTf() === "5");
  const positionBox = ref<INullable<PositionBoxCoords>>(null);
  const zoneBands = ref<ZoneBand[]>([]);
  let activeBox: INullable<ActiveBoxSpec> = null;
  let chartZones: ZoneInfo[] = [];
  let candleTimes: number[] = [];
  let chart: INullable<IChartApi> = null;
  let candleSeries: INullable<ISeriesApi<"Candlestick">> = null;
  let ema9Series: INullable<ISeriesApi<"Line">> = null;
  let ema20Series: INullable<ISeriesApi<"Line">> = null;
  let priceLines: IPriceLine[] = [];
  let linePrices: number[] = [];
  let markers: INullable<ISeriesMarkersPluginApi<Time>> = null;
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

  function updatePositionBox() {
    if (chart && candleSeries) {
      zoneBands.value = buildZoneBands({ chart, series: candleSeries, zones: chartZones, candleTimes });
    }
    if (!chart || !candleSeries || !activeBox) {
      positionBox.value = null;
      return;
    }
    positionBox.value = buildPositionBox({ chart, series: candleSeries, box: activeBox, candleTimes });
  }

  /**
   * @function showRecentBars
   * @description Shows the latest bars, widened to include a loaded target zone's origin candle.
   */
  function showRecentBars() {
    let from = Math.max(0, candleTimes.length - INITIAL_VISIBLE_BARS);
    for (const zone of chartZones) {
      if (!zone.isTarget || zone.timeSec === undefined || zone.timeSec < candleTimes[0]) continue;
      const originIndex = candleTimes.filter((t) => t <= (zone.timeSec as number)).length - 1;
      from = Math.max(0, Math.min(from, originIndex - ORIGIN_PADDING_BARS));
    }
    chart?.timeScale().setVisibleLogicalRange({ from, to: candleTimes.length - 1 + CHART_RIGHT_OFFSET_BARS });
  }

  function showTradeBars(box: ActiveBoxSpec) {
    const indexOf = (timeSec: number) => candleTimes.indexOf(candleAt({ candleTimes, timeSec }) ?? candleTimes[0]);
    const end = box.exitTimeSec ? indexOf(box.exitTimeSec) : candleTimes.length - 1;
    chart?.timeScale().setVisibleLogicalRange({
      from: indexOf(box.entryTimeSec) - PAST_TRADE_PADDING_BARS,
      to: end + PAST_TRADE_PADDING_BARS,
    });
  }

  /**
   * @function scheduleOverlayUpdate
   * @description Redraws overlays after the chart has painted its new price scale.
   */
  function scheduleOverlayUpdate() {
    window.requestAnimationFrame(() => window.requestAnimationFrame(updatePositionBox));
  }

  function renderData() {
    const current = analysis();
    if (!chart || !candleSeries || !ema9Series || !ema20Series || !current) return;
    const candles = current.candles || [];
    candleTimes = candles.map((c) => c.time);
    candleSeries.setData(
      candles.map((c) => ({ time: c.time as UTCTimestamp, open: c.open, high: c.high, low: c.low, close: c.close }))
    );
    ema9Series.setData(
      candles.filter((c) => c.ema9 !== null).map((c) => ({ time: c.time as UTCTimestamp, value: c.ema9 as number }))
    );
    ema20Series.setData(
      candles.filter((c) => c.ema20 !== null).map((c) => ({ time: c.time as UTCTimestamp, value: c.ema20 as number }))
    );

    const priceFormat = chartPriceFormat({ price: current.price });
    [candleSeries, ema9Series, ema20Series].forEach((series) => series?.applyOptions({ priceFormat }));

    clearPriceLines();
    const focused = trade();
    // A past trade replaces the live setup and hides today's zones, which did not exist in that form then.
    const past = focused && focused.symbol === current.symbol ? focused : null;
    const pastBox = past ? tradeBox({ item: past }) : null;
    activeBox = past ? pastBox : pickActiveBox({ analysis: current });
    if (activeBox) {
      linePrices.push(activeBox.entry, activeBox.stop, activeBox.target);
    }
    markers?.setMarkers(past && pastBox ? tradeMarkers({ item: past, box: pastBox, candleTimes }) : []);
    chartZones = past ? [] : pickChartZones({ analysis: current, box: activeBox });
    chart.priceScale("right").applyOptions({ autoScale: true });
    if (pastBox) showTradeBars(pastBox);
    else showRecentBars();
    scheduleOverlayUpdate();
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
    candleSeries = chart.addSeries(CandlestickSeries, {
      upColor: "#22c55e",
      downColor: "#ef4444",
      borderVisible: false,
      wickUpColor: "#22c55e",
      wickDownColor: "#ef4444",
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
    markers = createSeriesMarkers(candleSeries, []);
    ema9Series = chart.addSeries(LineSeries, {
      color: "#38bdf8",
      lineWidth: 1,
      visible: showEma.value,
      priceLineVisible: false,
      lastValueVisible: false,
    });
    ema20Series = chart.addSeries(LineSeries, {
      color: "#f59e0b",
      lineWidth: 1,
      visible: showEma.value,
      priceLineVisible: false,
      lastValueVisible: false,
    });
    resizeObserver = new ResizeObserver((entries) => {
      const entry = entries[0];
      if (entry && chart) {
        chart.applyOptions({
          width: Math.floor(entry.contentRect.width),
          height: Math.floor(entry.contentRect.height),
        });
        scheduleOverlayUpdate();
      }
    });
    resizeObserver.observe(containerRef.value);
    chart.timeScale().subscribeVisibleLogicalRangeChange(scheduleOverlayUpdate);
    renderData();
  });

  watch([analysis, trade], renderData);
  watch(selectedTf, (tf) => {
    showEma.value = tf === "5";
    applyEmaVisibility();
  });

  onBeforeUnmount(() => {
    resizeObserver?.disconnect();
    chart?.remove();
    chart = null;
  });

  return { showEma, toggleEma, positionBox, zoneBands, updatePositionBox };
}
