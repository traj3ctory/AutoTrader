<script setup lang="ts">
import { ref } from "vue";
import { CopyTarget, LoadState, type ScanResponse, type SignalHistoryEntry } from "../types/analyzer";
import LoadingSpinner from "./LoadingSpinner.vue";

defineProps<{
  scanResult: ScanResponse | null;
  signalHistory: SignalHistoryEntry[];
  scanState: LoadState;
  copiedTarget: CopyTarget;
}>();

const emit = defineEmits<{
  selectCoin: [symbol: string];
  copyText: [text: string];
}>();

const showHistory = ref(false);
</script>

<template>
  <section class="shrink-0 rounded-lg border border-border-subtle bg-surface-panel p-3">
    <div class="flex items-center justify-between gap-2">
      <h2 class="text-xs font-semibold uppercase tracking-wide text-ink-primary">Tradeable Signals</h2>
      <div class="flex items-center gap-1.5">
        <button
          type="button"
          class="cursor-pointer rounded border border-border-subtle bg-surface-elevated px-2 py-0.5 text-xs text-ink-secondary hover:text-ink-primary"
          @click="showHistory = !showHistory"
        >
          {{ showHistory ? "Live" : `History (${signalHistory.length})` }}
        </button>
        <span
          v-if="scanResult"
          class="rounded-full px-2 py-0.5 text-xs font-semibold"
          :class="
            scanResult.tradeable.length > 0
              ? 'bg-accent-bull/20 text-accent-bull'
              : 'bg-surface-elevated text-ink-secondary'
          "
        >
          {{ scanResult.tradeable.length }} tradeable
        </span>
      </div>
    </div>

    <div v-if="showHistory" class="mt-2 max-h-48 space-y-1.5 overflow-y-auto text-xs">
      <div
        v-for="item in signalHistory"
        :key="item.id"
        class="rounded border border-border-subtle bg-surface-elevated p-2"
      >
        <div class="flex items-center justify-between gap-1">
          <div class="flex flex-wrap items-center gap-1">
            <span class="font-semibold text-ink-primary">{{ item.symbol }} · {{ item.mode }}</span>
            <span v-if="item.emaBadge" class="rounded bg-surface-panel px-1.5 py-0.5 text-xs text-ink-secondary">
              EMA: {{ item.emaBadge }}
            </span>
          </div>
          <div class="flex items-center gap-1">
            <button
              type="button"
              class="cursor-pointer rounded border border-border-subtle bg-surface-panel px-1.5 py-0.5 text-xs text-ink-primary hover:border-accent-brand"
              @click="emit('selectCoin', item.symbol)"
            >
              Chart
            </button>
            <button
              type="button"
              class="cursor-pointer rounded bg-surface-panel px-1.5 py-0.5 text-xs text-ink-primary hover:bg-accent-brand hover:text-white"
              @click="emit('copyText', item.copyText)"
            >
              {{ copiedTarget === CopyTarget.Tradeable ? "Copied!" : "Copy" }}
            </button>
          </div>
        </div>
        <p class="mt-1 text-ink-secondary">{{ item.summary }}</p>
        <p class="mt-0.5 text-ink-muted">Seen {{ item.seenAtUtc }}</p>
      </div>
      <p v-if="signalHistory.length === 0" class="text-ink-muted">
        No tradeable signals recorded yet. Live triggers will log here automatically.
      </p>
    </div>

    <div v-else-if="scanState === LoadState.Loading" class="mt-2">
      <LoadingSpinner label="Scanning coins on live Bybit candles..." />
    </div>

    <div v-else-if="scanResult && scanResult.tradeable.length > 0" class="mt-2 space-y-2">
      <div
        v-for="item in scanResult.tradeable"
        :key="`${item.symbol}-${item.mode}`"
        class="rounded border border-accent-bull/40 bg-accent-bull/10 p-2 text-xs"
      >
        <div class="flex items-center justify-between gap-1">
          <div class="flex flex-wrap items-center gap-1.5">
            <span class="font-semibold text-accent-bull">{{ item.symbol }} · {{ item.mode }}</span>
            <span
              v-if="item.emaBadge"
              class="rounded px-1.5 py-0.5 text-xs font-medium"
              :class="
                item.emaBadge === 'SUPPORTING'
                  ? 'bg-accent-bull/20 text-accent-bull'
                  : item.emaBadge === 'COUNTER'
                    ? 'bg-accent-bear/20 text-accent-bear'
                    : 'bg-surface-elevated text-ink-secondary'
              "
            >
              EMA: {{ item.emaBadge }}
            </span>
          </div>
          <div class="flex items-center gap-1">
            <button
              type="button"
              class="cursor-pointer rounded border border-border-subtle bg-surface-panel px-1.5 py-0.5 text-xs text-ink-primary hover:border-accent-brand"
              @click="emit('selectCoin', item.symbol)"
            >
              Chart
            </button>
            <button
              type="button"
              class="cursor-pointer rounded bg-accent-bull px-2 py-0.5 text-xs font-medium text-surface-canvas"
              @click="emit('copyText', item.copyText)"
            >
              {{ copiedTarget === CopyTarget.Tradeable ? "Copied!" : "Copy" }}
            </button>
          </div>
        </div>
        <p class="mt-1 text-ink-primary">{{ item.summary }}</p>
      </div>
    </div>

    <p v-else-if="scanResult" class="mt-1.5 text-xs text-ink-secondary">
      0 VALID signals across {{ scanResult.checked.length }} coins right now.
    </p>
  </section>
</template>
