<script setup lang="ts">
import { ref } from "vue";
import { LoadState, type MoversPayload } from "../types/analyzer";
import LoadingSpinner from "./LoadingSpinner.vue";

defineProps<{
  movers: MoversPayload | null;
  moversState: LoadState;
  collapsed: boolean;
}>();

const emit = defineEmits<{
  refresh: [];
  selectCoin: [symbol: string];
  toggleCollapse: [];
}>();

const activeTab = ref<"gainers" | "losers" | "range">("losers");
</script>

<template>
  <section class="flex-col rounded-lg border border-border-subtle bg-surface-panel p-3">
    <div class="flex shrink-0 items-center justify-between gap-2">
      <button
        type="button"
        class="flex cursor-pointer items-center gap-1.5 text-left text-xs font-semibold uppercase tracking-wide text-ink-primary"
        @click="emit('toggleCollapse')"
      >
        <span class="hidden text-ink-muted lg:inline">{{ collapsed ? "▸" : "▾" }}</span>
        <span>Crypto Movers</span>
      </button>

      <div class="flex items-center gap-1" :class="{ 'lg:hidden': collapsed }">
        <button
          type="button"
          class="cursor-pointer rounded px-1.5 py-0.5 text-xs"
          :class="activeTab === 'losers' ? 'bg-accent-brand text-white' : 'bg-surface-elevated text-ink-secondary'"
          @click="activeTab = 'losers'"
        >
          Losers
        </button>
        <button
          type="button"
          class="cursor-pointer rounded px-1.5 py-0.5 text-xs"
          :class="activeTab === 'gainers' ? 'bg-accent-brand text-white' : 'bg-surface-elevated text-ink-secondary'"
          @click="activeTab = 'gainers'"
        >
          Gainers
        </button>
        <button
          type="button"
          class="cursor-pointer rounded px-1.5 py-0.5 text-xs"
          :class="activeTab === 'range' ? 'bg-accent-brand text-white' : 'bg-surface-elevated text-ink-secondary'"
          @click="activeTab = 'range'"
        >
          Range
        </button>
        <button
          type="button"
          class="inline-flex cursor-pointer items-center rounded border border-border-subtle bg-surface-elevated px-2 py-0.5 text-xs text-ink-primary hover:border-accent-brand disabled:opacity-50"
          :disabled="moversState === LoadState.Loading"
          @click="emit('refresh')"
        >
          <LoadingSpinner v-if="moversState === LoadState.Loading" />
          <span v-else>↻</span>
        </button>
      </div>
    </div>

    <div class="mt-2 min-h-0 flex-1 overflow-y-auto" :class="{ 'lg:hidden': collapsed }">
      <table class="w-full text-left text-xs">
        <thead class="border-b border-border-subtle text-ink-muted">
          <tr>
            <th class="py-1 pr-1">Coin</th>
            <th class="py-1 pr-1">{{ activeTab === "range" ? "Range" : "24h" }}</th>
            <th class="py-1 pr-1">Vol</th>
            <th class="py-1 text-right">Read</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-border-subtle/50">
          <tr
            v-for="row in activeTab === 'gainers'
              ? movers?.gainers || []
              : activeTab === 'losers'
                ? movers?.losers || []
                : movers?.rangeMovers || []"
            :key="row.ticker"
          >
            <td class="py-1 pr-1 font-medium text-ink-primary">
              {{ row.symbol.replace("USDT", "") }}
              <span v-if="row.inLedger" class="text-accent-brand">★</span>
            </td>
            <td
              class="py-1 pr-1"
              :class="row.pct >= 0 ? 'text-accent-bull' : 'text-accent-bear'"
            >
              <template v-if="activeTab === 'range'">
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
