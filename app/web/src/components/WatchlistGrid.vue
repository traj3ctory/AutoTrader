<script setup lang="ts">
defineProps<{
  ledgerSymbols: string[];
  tvSymbols: string[];
  selectedSymbol: string;
}>();

const emit = defineEmits<{
  selectCoin: [symbol: string];
}>();
</script>

<template>
  <div class="space-y-2 text-xs">
    <div>
      <p class="mb-1 text-ink-muted">Ledger</p>
      <div class="flex flex-wrap gap-1">
        <button
          v-for="sym in ledgerSymbols"
          :key="sym"
          type="button"
          class="cursor-pointer rounded px-2 py-1 font-medium"
          :class="selectedSymbol === sym ? 'bg-accent-brand text-white' : 'bg-surface-elevated text-ink-secondary hover:text-ink-primary'"
          @click="emit('selectCoin', sym)"
        >
          {{ sym.replace("USDT", "") }}
        </button>
      </div>
    </div>
    <div v-if="tvSymbols.length">
      <p class="mb-1 text-ink-muted">From movers sync</p>
      <div class="flex flex-wrap gap-1">
        <button
          v-for="sym in tvSymbols"
          :key="sym"
          type="button"
          class="cursor-pointer rounded px-2 py-1 font-medium"
          :class="selectedSymbol === sym ? 'bg-accent-brand text-white' : 'bg-surface-elevated text-ink-muted hover:text-ink-primary'"
          @click="emit('selectCoin', sym)"
        >
          {{ sym.replace("USDT", "") }}
        </button>
      </div>
    </div>
  </div>
</template>
