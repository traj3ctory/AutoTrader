<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { LoadState, type MoversPayload } from "../types/analyzer";
import { MoverTab } from "../types/enums";
import { MOVER_TABS } from "../constants/movers";
import { STORAGE_KEYS } from "../constants/analyzer";
import { readStoredNumber, writeStoredNumber } from "../utils/storage";
import LoadingSpinner from "./LoadingSpinner.vue";
import WatchlistGrid from "./WatchlistGrid.vue";

const props = defineProps<{
  ledgerSymbols: string[];
  tvSymbols: string[];
  selectedSymbol: string;
  movers: MoversPayload | null;
  moversState: LoadState;
  collapsed: boolean;
}>();

const emit = defineEmits<{
  refresh: [];
  selectCoin: [symbol: string];
  toggleCollapse: [];
}>();

const activeTab = ref<MoverTab>(readStoredNumber({ key: STORAGE_KEYS.moverTab, fallback: MoverTab.Watchlist }));
watch(activeTab, (value) => writeStoredNumber({ key: STORAGE_KEYS.moverTab, value }));

const rows = computed(() => {
  if (activeTab.value === MoverTab.Gainers) return props.movers?.gainers || [];
  if (activeTab.value === MoverTab.Range) return props.movers?.rangeMovers || [];
  return props.movers?.losers || [];
});
</script>

<template>
  <section class="flex-col rounded-lg border border-border-subtle bg-surface-panel p-3">
    <div class="flex shrink-0 flex-wrap items-center justify-between gap-2">
      <button
        type="button"
        class="flex cursor-pointer items-center gap-1.5 text-left text-xs font-semibold uppercase tracking-wide text-ink-primary"
        @click="emit('toggleCollapse')"
      >
        <span class="hidden text-ink-muted lg:inline">{{ collapsed ? "▸" : "▾" }}</span>
        <span>Crypto Movers</span>
      </button>

      <div class="flex flex-wrap items-center gap-1" :class="{ 'lg:hidden': collapsed }">
        <button
          v-for="tab in MOVER_TABS"
          :key="tab.value"
          type="button"
          :title="tab.hint"
          class="cursor-pointer rounded px-1.5 py-0.5 text-xs"
          :class="activeTab === tab.value ? 'bg-accent-brand text-white' : 'bg-surface-elevated text-ink-secondary'"
          @click="activeTab = tab.value"
        >
          {{ tab.label }}
        </button>
        <button
          type="button"
          title="Run mover scan & sync top 3 focus coins"
          class="inline-flex cursor-pointer items-center rounded border border-border-subtle bg-surface-elevated px-2 py-0.5 text-xs text-ink-primary hover:border-accent-brand disabled:opacity-50"
          :disabled="moversState === LoadState.Loading"
          @click="emit('refresh')"
        >
          <LoadingSpinner v-if="moversState === LoadState.Loading" />
          <span v-else>↻</span>
        </button>
      </div>
    </div>

    <div
      v-if="movers?.schedule?.times?.length"
      class="mt-1 flex shrink-0 items-center justify-between text-xs text-ink-muted"
      :class="{ 'lg:hidden': collapsed }"
    >
      <span>Auto: {{ movers.schedule.times.join(" · ") }} UTC{{ movers.schedule.tzOffsetHours >= 0 ? "+" : "" }}{{ movers.schedule.tzOffsetHours }}</span>
      <span v-if="movers.tvWatchlist?.length">Synced: {{ movers.tvWatchlist.map((s) => s.replace("USDT.P", "")).join(", ") }}</span>
    </div>

    <div class="mt-2 min-h-0 flex-1 overflow-y-auto" :class="{ 'lg:hidden': collapsed }">
      <WatchlistGrid
        v-if="activeTab === MoverTab.Watchlist"
        :ledger-symbols="ledgerSymbols"
        :tv-symbols="tvSymbols"
        :selected-symbol="selectedSymbol"
        @select-coin="(symbol) => emit('selectCoin', symbol)"
      />
      <table v-else class="w-full text-left text-xs">
        <thead class="border-b border-border-subtle text-ink-muted">
          <tr>
            <th class="py-1 pr-1">Coin</th>
            <th class="py-1 pr-1">{{ activeTab === MoverTab.Range ? "Range" : "24h" }}</th>
            <th class="py-1 pr-1">Vol</th>
            <th class="py-1 text-right">Read</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-border-subtle/50">
          <tr
            v-for="row in rows"
            :key="row.ticker"
            class="fade_in_item"
          >
            <td class="py-1 pr-1 font-medium text-ink-primary">
              {{ row.symbol.replace("USDT", "") }}
              <span v-if="row.inLedger" class="text-accent-brand">★</span>
            </td>
            <td
              class="py-1 pr-1"
              :class="row.pct >= 0 ? 'text-accent-bull' : 'text-accent-bear'"
            >
              <template v-if="activeTab === MoverTab.Range">
                {{ row.rangePct }}%
              </template>
              <template v-else>
                {{ row.pct >= 0 ? "+" : "" }}{{ row.pct }}%
              </template>
            </td>
            <td class="py-1 pr-1 text-ink-secondary">${{ row.turnoverM }}M</td>
            <td class="py-1 text-right">
              <button
                type="button"
                class="cursor-pointer rounded bg-surface-elevated px-1.5 py-0.5 text-xs text-ink-primary hover:bg-accent-brand hover:text-white"
                @click="emit('selectCoin', row.symbol)"
              >
                Open
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </section>
</template>
