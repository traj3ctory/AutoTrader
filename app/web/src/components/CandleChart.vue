<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from "vue";
import {
  CandlestickSeries,
  LineSeries,
  LineStyle,
  createChart,
  type IChartApi,
  type IPriceLine,
  type ISeriesApi,
  type UTCTimestamp,
} from "lightweight-charts";
import { LoadState, type AnalyzeResponse } from "../types/analyzer";
import LoadingSpinner from "./LoadingSpinner.vue";

const props = defineProps<{
  analysis: AnalyzeResponse | null;
  analyzeState: LoadState;
  selectedSymbol: string;
  selectedTf: string;
}>();

const emit = defineEmits<{
  changeTf: [tf: string];
}>();

const TIMEFRAMES = [
  { value: "5", label: "5m" },
  { value: "15", label: "15m" },
  { value: "60", label: "1H" },
  { value: "240", label: "4H" },
];

const containerRef = ref<HTMLElement | null>(null);
let chart: IChartApi | null = null;
let candleSeries: ISeriesApi<"Candlestick"> | null = null;
let ema9Series: ISeriesApi<"Line"> | null = null;
let ema20Series: ISeriesApi<"Line"> | null = null;
let priceLines: IPriceLine[] = [];
let resizeObserver: ResizeObserver | null = null;

function clearPriceLines() {
  if (!candleSeries) {
    priceLines = [];
    return;
  }
  for (const line of priceLines) {
    candleSeries.removePriceLine(line);
  }
  priceLines = [];
}

function addZoneLine({
  price,
  title,
  color,
  dashed = false,
}: {
  price: number;
  title: string;
  color: string;
  dashed?: boolean;
}) {
  if (!candleSeries || !Number.isFinite(price)) return;
  const line = candleSeries.createPriceLine({
    price,
    color,
    lineWidth: dashed ? 1 : 2,
    lineStyle: dashed ? LineStyle.Dashed : LineStyle.Solid,
    axisLabelVisible: true,
    title,
  });
  priceLines.push(line);
}

function renderData() {
  if (!chart || !candleSeries || !ema9Series || !ema20Series || !props.analysis) {
    return;
  }
  const candles = props.analysis.candles || [];
  candleSeries.setData(
    candles.map((c) => ({
      time: c.time as UTCTimestamp,
      open: c.open,
      high: c.high,
      low: c.low,
      close: c.close,
    }))
  );

  ema9Series.setData(
    candles
      .filter((c) => c.ema9 !== null)
      .map((c) => ({ time: c.time as UTCTimestamp, value: c.ema9 as number }))
  );
  ema20Series.setData(
    candles
      .filter((c) => c.ema20 !== null)
      .map((c) => ({ time: c.time as UTCTimestamp, value: c.ema20 as number }))
  );

  clearPriceLines();
  const { scalpZone, scalp, intraday } = props.analysis;
  if (scalpZone.position) {
    addZoneLine({ price: scalpZone.position.entry, title: "Zone Entry", color: "#3b82f6" });
    addZoneLine({ price: scalpZone.position.stop, title: "Zone SL", color: "#ef4444" });
    addZoneLine({ price: scalpZone.position.target, title: "Zone TP", color: "#22c55e" });
  }
  if (scalp.position) {
    addZoneLine({ price: scalp.position.entry, title: "Scalp Entry", color: "#3b82f6" });
    addZoneLine({ price: scalp.position.stop, title: "Scalp SL", color: "#ef4444" });
    addZoneLine({ price: scalp.position.target, title: "Scalp TP", color: "#22c55e" });
  }
  if (intraday.position) {
    addZoneLine({ price: intraday.position.entry, title: "Intraday Entry", color: "#3b82f6" });
    addZoneLine({ price: intraday.position.stop, title: "Intraday SL", color: "#ef4444" });
    addZoneLine({ price: intraday.position.target, title: "Intraday TP", color: "#22c55e" });
  }
  if (intraday.pending) {
    addZoneLine({ price: intraday.pending.entry, title: "Intraday Limit", color: "#3b82f6" });
    addZoneLine({ price: intraday.pending.stop, title: "Intraday SL", color: "#ef4444" });
    addZoneLine({ price: intraday.pending.target, title: "Intraday TP", color: "#22c55e" });
  }
  if (intraday.long.nearestZone) {
    addZoneLine({
      price: intraday.long.nearestZone.low,
      title: "Demand Low",
      color: "#22c55e",
      dashed: true,
    });
    addZoneLine({
      price: intraday.long.nearestZone.high,
      title: "Demand High",
      color: "#22c55e",
      dashed: true,
    });
  }
  if (intraday.short.nearestZone) {
    addZoneLine({
      price: intraday.short.nearestZone.low,
      title: "Supply Low",
      color: "#ef4444",
      dashed: true,
    });
    addZoneLine({
      price: intraday.short.nearestZone.high,
      title: "Supply High",
      color: "#ef4444",
      dashed: true,
    });
  }

  chart.timeScale().fitContent();
}

onMounted(() => {
  if (!containerRef.value) return;
  chart = createChart(containerRef.value, {
    layout: {
      background: { color: "#111827" },
      textColor: "#9ca3af",
    },
    grid: {
      vertLines: { color: "#1f2937" },
      horzLines: { color: "#1f2937" },
    },
    rightPriceScale: {
      borderColor: "#243047",
    },
    timeScale: {
      borderColor: "#243047",
      timeVisible: true,
    },
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
  });
  ema9Series = chart.addSeries(LineSeries, {
    color: "#38bdf8",
    lineWidth: 1,
    priceLineVisible: false,
    lastValueVisible: false,
    priceFormat,
  });
  ema20Series = chart.addSeries(LineSeries, {
    color: "#f59e0b",
    lineWidth: 1,
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
    }
  });
  resizeObserver.observe(containerRef.value);

  renderData();
});

watch(() => props.analysis, renderData);

onBeforeUnmount(() => {
  resizeObserver?.disconnect();
  chart?.remove();
  chart = null;
});
</script>

<template>
  <section class="flex min-h-0 flex-1 flex-col rounded-lg border border-border-subtle bg-surface-panel p-3">
    <div class="mb-2 flex shrink-0 flex-wrap items-center justify-between gap-2">
      <div class="flex items-center gap-2">
        <h2 class="text-xs font-semibold text-ink-primary">
          {{ analysis ? `${analysis.ticker} · ${analysis.price}` : "Chart" }}
        </h2>
        <span
          v-if="analysis"
          class="rounded px-1.5 py-0.5 text-xs"
          :class="
            analysis.structure4h === 'bullish'
              ? 'bg-accent-bull/20 text-accent-bull'
              : analysis.structure4h === 'bearish'
                ? 'bg-accent-bear/20 text-accent-bear'
                : 'bg-surface-elevated text-ink-secondary'
          "
        >
          4H {{ analysis.structure4h }}
        </span>
        <span
          v-if="analysis"
          class="rounded px-1.5 py-0.5 text-xs"
          :class="
            analysis.structure1d === 'bullish'
              ? 'bg-accent-bull/20 text-accent-bull'
              : analysis.structure1d === 'bearish'
                ? 'bg-accent-bear/20 text-accent-bear'
                : 'bg-surface-elevated text-ink-secondary'
          "
        >
          1D {{ analysis.structure1d }}
        </span>
        <span class="hidden text-xs text-ink-muted xl:inline">EMA 9/20 + Zones</span>
      </div>

      <div class="flex items-center gap-1">
        <button
          v-for="tf in TIMEFRAMES"
          :key="tf.value"
          type="button"
          class="cursor-pointer rounded px-2 py-0.5 text-xs font-medium"
          :class="
            selectedTf === tf.value
              ? 'bg-accent-brand text-white'
              : 'bg-surface-elevated text-ink-secondary hover:text-ink-primary'
          "
          :disabled="analyzeState === LoadState.Loading"
          @click="emit('changeTf', tf.value)"
        >
          {{ tf.label }}
        </button>
      </div>
    </div>

    <div class="relative min-h-56 w-full flex-1 overflow-hidden rounded border border-border-subtle">
      <div ref="containerRef" class="h-full w-full" />
      <div
        v-if="analyzeState === LoadState.Loading"
        class="absolute inset-0 z-10 flex items-center justify-center bg-surface-panel/75"
      >
        <div class="rounded-lg border border-border-subtle bg-surface-elevated px-4 py-2.5 shadow-lg">
          <LoadingSpinner size="md" :label="`Analyzing ${selectedSymbol} (${selectedTf === '60' ? '1H' : selectedTf === '240' ? '4H' : selectedTf + 'm'})...`" />
        </div>
      </div>
    </div>
  </section>
</template>
