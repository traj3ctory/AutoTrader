<script setup lang="ts">
import type { CoinQuote } from "../types/market";
import { formatPct, formatRange, formatTurnover, pctClass } from "../utils/quotes";

defineProps<{
  rows: CoinQuote[];
  showRange?: boolean;
  selectedSymbol: string;
}>();

const emit = defineEmits<{
  selectCoin: [symbol: string];
}>();
</script>

<template>
  <table class="w-full table-fixed text-left text-xs">
    <thead class="border-b border-border-subtle text-ink-muted">
      <tr>
        <th class="w-2/5 py-1 pr-1">Coin</th>
        <th class="w-1/5 py-1 pr-1">{{ showRange ? "Range" : "24h" }}</th>
        <th class="w-1/5 py-1 pr-1">Vol</th>
        <th class="w-1/5 py-1 text-right">Read</th>
      </tr>
    </thead>
    <tbody class="divide-y divide-border-subtle/50">
      <tr
        v-for="row in rows"
        :key="row.symbol"
        class="fade_in_item"
        :class="{ 'bg-surface-elevated': selectedSymbol === row.symbol }"
      >
        <td class="truncate py-1 pr-1 font-medium text-ink-primary">
          {{ row.symbol.replace("USDT", "") }}
          <span v-if="row.inLedger" class="text-accent-brand">★</span>
        </td>
        <td class="py-1 pr-1" :class="pctClass(row.pct)">
          {{ showRange ? formatRange(row.rangePct) : formatPct(row.pct) }}
        </td>
        <td class="py-1 pr-1 text-ink-secondary">{{ formatTurnover(row.turnoverM) }}</td>
        <td class="py-1 text-right">
          <button
            type="button"
            class="cursor-pointer rounded px-1.5 py-0.5 text-xs hover:bg-accent-brand hover:text-white"
            :class="selectedSymbol === row.symbol ? 'bg-accent-brand text-white' : 'bg-surface-elevated text-ink-primary'"
            @click="emit('selectCoin', row.symbol)"
          >
            Open
          </button>
        </td>
      </tr>
    </tbody>
  </table>
</template>
