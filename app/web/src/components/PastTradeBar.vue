<script setup lang="ts">
import type { SignalHistoryEntry } from "../types/analyzer";
import { historyOutcomeClass, historyOutcomeLabel } from "../utils/badges";
import { historySummary } from "../utils/historyText";
import { formatSeenAt } from "../utils/time";

defineProps<{
  item: SignalHistoryEntry;
}>();

const emit = defineEmits<{
  backToLive: [];
}>();
</script>

<template>
  <div class="mb-2 flex shrink-0 flex-wrap items-center justify-between gap-2 rounded border border-accent-brand/40 bg-accent-brand/10 px-2 py-1 text-xs">
    <div class="flex flex-wrap items-center gap-1.5">
      <span class="font-semibold text-ink-primary">Recorded signal · {{ item.symbol }} · {{ item.mode }}</span>
      <span class="rounded px-1.5 py-0.5 font-semibold" :class="historyOutcomeClass(item)">{{ historyOutcomeLabel(item) }}</span>
      <span class="text-ink-secondary">{{ historySummary({ item }) }}</span>
      <span class="text-ink-muted">Seen {{ formatSeenAt(item.seenAtUtc) }}. Zones hidden.</span>
    </div>
    <button
      type="button"
      class="cursor-pointer rounded border border-border-subtle bg-surface-panel px-1.5 py-0.5 text-ink-primary hover:border-accent-brand"
      @click="emit('backToLive')"
    >
      Back to live
    </button>
  </div>
</template>
