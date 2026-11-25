<script setup lang="ts">
import { ref } from "vue";
import { TIMEFRAMES } from "../constants/analyzer";
import { useCandleChart } from "../composables/useCandleChart";
import { LoadState, type AnalyzeResponse } from "../types/analyzer";
import type { INullable } from "../types/common";
import LoadingSpinner from "./LoadingSpinner.vue";
import PositionBoxOverlay from "./PositionBoxOverlay.vue";

const props = defineProps<{
  analysis: INullable<AnalyzeResponse>;
  analyzeState: LoadState;
  selectedSymbol: string;
  selectedTf: string;
}>();

const emit = defineEmits<{
  changeTf: [tf: string];
}>();

const containerRef = ref<INullable<HTMLElement>>(null);
const { showEma, toggleEma, positionBox, updatePositionBox } = useCandleChart({
  containerRef,
  analysis: () => props.analysis,
  selectedTf: () => props.selectedTf,
});
</script>

<template>
  <section class="flex min-h-0 flex-1 flex-col rounded-lg border border-border-subtle bg-surface-panel p-3 transition-colors duration-200">
    <div class="mb-2 flex shrink-0 flex-wrap items-center justify-between gap-2">
      <div class="flex items-center gap-2">
        <h2 class="text-xs font-semibold text-ink-primary">
          {{ analysis ? `${analysis.ticker} · ${analysis.price}` : "Chart" }}
        </h2>
        <span
          v-if="analysis"
          class="rounded px-1.5 py-0.5 text-xs transition-colors duration-150"
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
          class="rounded px-1.5 py-0.5 text-xs transition-colors duration-150"
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
        <span class="hidden text-xs text-ink-muted xl:inline">Zones</span>
      </div>

      <div class="flex items-center gap-1">
        <button
          type="button"
          class="mr-1 cursor-pointer rounded px-2 py-0.5 text-xs font-medium transition-all duration-150 active:scale-95"
          :class="
            showEma
              ? 'border border-accent-brand/40 bg-accent-brand/20 text-accent-brand'
              : 'bg-surface-elevated text-ink-secondary hover:text-ink-primary'
          "
          @click="toggleEma"
        >
          EMA 9/20
        </button>
        <button
          v-for="tf in TIMEFRAMES"
          :key="tf.value"
          type="button"
          class="cursor-pointer rounded px-2 py-0.5 text-xs font-medium transition-all duration-150 active:scale-95"
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

    <div
      class="relative min-h-56 w-full flex-1 overflow-hidden rounded border border-border-subtle"
      @wheel.passive="updatePositionBox"
      @pointermove="updatePositionBox"
      @pointerup="updatePositionBox"
    >
      <div ref="containerRef" class="h-full w-full" />
      <PositionBoxOverlay :box="positionBox" />
      <div
        v-if="analyzeState === LoadState.Loading"
        class="absolute inset-0 z-20 flex items-center justify-center bg-surface-panel/75 transition-opacity duration-200"
      >
        <div class="rounded-lg border border-border-subtle bg-surface-elevated px-4 py-2.5 shadow-lg">
          <LoadingSpinner size="md" :label="`Analyzing ${selectedSymbol} (${selectedTf === '60' ? '1H' : selectedTf === '240' ? '4H' : selectedTf + 'm'})...`" />
        </div>
      </div>
    </div>
  </section>
</template>
