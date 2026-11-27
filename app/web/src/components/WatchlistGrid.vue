<script setup lang="ts">
import { computed } from "vue";
import { LoadState } from "../types/analyzer";
import { useWatchlistQuotes } from "../composables/useWatchlistQuotes";
import CoinTable from "./CoinTable.vue";

const props = defineProps<{
  ledgerSymbols: string[];
  tvSymbols: string[];
  selectedSymbol: string;
  moversUpdatedAt: string;
}>();

const emit = defineEmits<{
  selectCoin: [symbol: string];
}>();

const reloadKey = computed(() => [...props.ledgerSymbols, ...props.tvSymbols, props.moversUpdatedAt].join(","));
const { quotes, quotesState } = useWatchlistQuotes({ reloadKey });

const groups = computed(() =>
  [
    { label: "Ledger", symbols: props.ledgerSymbols },
    { label: "From movers sync", symbols: props.tvSymbols },
  ]
    .filter((group) => group.symbols.length)
    .map((group) => ({
      label: group.label,
      rows: group.symbols.map((symbol) => quotes.value[symbol] ?? { symbol }),
    }))
);
</script>

<template>
  <div class="space-y-3 text-xs">
    <p v-if="quotesState === LoadState.Error" class="text-accent-bear">Live quotes unavailable.</p>
    <div v-for="group in groups" :key="group.label">
      <p class="mb-1 text-ink-muted">{{ group.label }}</p>
      <CoinTable
        :rows="group.rows"
        :selected-symbol="selectedSymbol"
        @select-coin="(symbol) => emit('selectCoin', symbol)"
      />
    </div>
  </div>
</template>
