<script setup lang="ts">
import { computed, ref } from "vue";
import { AppView, LoadState, type OverviewResponse, type RiskStatus } from "../types/analyzer";
import LoadingSpinner from "./LoadingSpinner.vue";

const props = defineProps<{
  overview: OverviewResponse | null;
  risk: RiskStatus | null;
  scanState: LoadState;
  activeView: AppView;
  soundEnabled: boolean;
  autoScanMinutes: number;
}>();

const emit = defineEmits<{
  scan: [];
  selectCoin: [symbol: string];
  changeView: [view: AppView];
  toggleSound: [];
  changeAutoScan: [minutes: number];
}>();

const customSymbol = ref("");
const btcContext = computed(() => props.overview?.contextWatch?.["BTCUSDT.P"]);

function submitSearch() {
  const sym = customSymbol.value.trim();
  if (!sym) return;
  emit("selectCoin", sym);
  customSymbol.value = "";
}

function handleAutoScanChange(event: Event) {
  const minutes = Number((event.target as HTMLSelectElement).value);
  if (Number.isFinite(minutes)) {
    emit("changeAutoScan", minutes);
  }
}
</script>

<template>
  <header class="w-full shrink-0 border-b border-border-subtle bg-surface-panel px-3 py-1.5">
    <div class="flex flex-wrap items-center justify-between gap-2 lg:flex-nowrap">
      <div class="flex flex-wrap items-center gap-2 lg:shrink-0 lg:flex-nowrap">
        <span class="text-sm font-semibold tracking-tight text-ink-primary">AutoTrader</span>

        <div class="flex items-center rounded border border-border-subtle bg-surface-elevated p-0.5 text-xs">
          <button
            type="button"
            class="cursor-pointer rounded px-2 py-0.5 font-medium"
            :class="activeView === AppView.Analyzer ? 'bg-accent-brand text-white' : 'text-ink-secondary hover:text-ink-primary'"
            @click="emit('changeView', AppView.Analyzer)"
          >
            Analyzer
          </button>
          <button
            type="button"
            class="cursor-pointer rounded px-2 py-0.5 font-medium"
            :class="activeView === AppView.Dashboard ? 'bg-accent-brand text-white' : 'text-ink-secondary hover:text-ink-primary'"
            @click="emit('changeView', AppView.Dashboard)"
          >
            Dashboard
          </button>
        </div>

        <div
          v-if="btcContext"
          class="hidden rounded border border-border-subtle bg-surface-elevated px-2 py-0.5 text-xs text-ink-secondary xl:block"
        >
          BTC
          <span class="text-ink-primary">
            {{ btcContext.key_support?.low }}–{{ btcContext.key_support?.high }}
          </span>
          /
          <span class="text-ink-primary">
            {{ btcContext.key_resistance?.low }}–{{ btcContext.key_resistance?.high }}
          </span>
        </div>

        <span
          v-if="risk"
          class="rounded-full px-2 py-0.5 text-xs font-medium whitespace-nowrap"
          :class="
            risk.locked
              ? 'border border-accent-bear/40 bg-accent-bear/20 text-accent-bear'
              : 'border border-accent-bull/40 bg-accent-bull/20 text-accent-bull'
          "
        >
          {{ risk.locked ? "LOCKED" : "RISK OK" }} · {{ risk.open.length }}/2 ·
          {{ risk.daily_pct >= 0 ? "+" : "" }}{{ risk.daily_pct.toFixed(2) }}%
        </span>
      </div>

      <div class="flex flex-wrap items-center gap-1.5 lg:shrink-0 lg:flex-nowrap">
        <form class="flex items-center gap-1" @submit.prevent="submitSearch">
          <input
            v-model="customSymbol"
            name="symbol_search"
            type="text"
            placeholder="Coin (e.g. AKE)"
            class="w-24 rounded border border-border-subtle bg-surface-elevated px-2 py-1 text-xs text-ink-primary placeholder:text-ink-muted"
          />
          <button
            type="submit"
            class="cursor-pointer rounded bg-surface-elevated px-2 py-1 text-xs font-medium text-ink-primary hover:bg-accent-brand hover:text-white"
          >
            Go
          </button>
        </form>

        <select
          name="auto_scan_interval"
          :value="autoScanMinutes"
          title="Periodic signal scan interval"
          class="cursor-pointer rounded border border-border-subtle bg-surface-elevated px-2 py-1 text-xs text-ink-primary"
          @change="handleAutoScanChange"
        >
          <option :value="0">Auto: Off</option>
          <option :value="5">Auto: 5m</option>
          <option :value="15">Auto: 15m</option>
          <option :value="30">Auto: 30m</option>
        </select>

        <button
          type="button"
          class="cursor-pointer rounded border px-2 py-1 text-xs font-medium whitespace-nowrap"
          :class="
            soundEnabled
              ? 'border-accent-bull/40 bg-accent-bull/15 text-accent-bull'
              : 'border-border-subtle bg-surface-elevated text-ink-secondary'
          "
          title="Toggle & test sound alert for new tradeable signals"
          @click="emit('toggleSound')"
        >
          {{ soundEnabled ? "Sound: On" : "Sound: Off" }}
        </button>

        <button
          type="button"
          class="inline-flex cursor-pointer items-center gap-1.5 rounded border border-border-subtle bg-surface-elevated px-2.5 py-1 text-xs font-medium whitespace-nowrap text-ink-primary hover:border-accent-brand disabled:opacity-50"
          :disabled="scanState === LoadState.Loading"
          @click="emit('scan')"
        >
          <LoadingSpinner v-if="scanState === LoadState.Loading" label="Scanning..." />
          <span v-else>Scan All</span>
        </button>
      </div>
    </div>
  </header>
</template>
