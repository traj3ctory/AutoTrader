<script setup lang="ts">
import { CopyTarget, type SignalHistoryEntry } from "../types/analyzer";
import { historyOutcomeClass, historyOutcomeLabel } from "../utils/badges";
import { historySummary } from "../utils/historyText";
import { formatClosedAt, formatSeenAt } from "../utils/time";

defineProps<{
  items: SignalHistoryEntry[];
  copiedTarget: CopyTarget;
}>();

const emit = defineEmits<{
  showTrade: [item: SignalHistoryEntry];
  copyText: [text: string];
}>();
</script>

<template>
  <div class="mt-2 max-h-60 space-y-1.5 overflow-y-auto text-xs">
    <div v-for="item in items" :key="item.id" class="fade_in_item rounded border border-border-subtle bg-surface-elevated p-2">
      <div class="flex items-center justify-between gap-1">
        <div class="flex flex-wrap items-center gap-1">
          <span class="font-semibold text-ink-primary">{{ item.symbol }} · {{ item.mode }}</span>
          <span class="rounded px-1.5 py-0.5 text-xs font-semibold" :class="historyOutcomeClass(item)">
            {{ historyOutcomeLabel(item) }}
          </span>
          <span v-if="item.emaBadge" class="rounded bg-surface-panel px-1.5 py-0.5 text-xs text-ink-secondary">
            EMA: {{ item.emaBadge }}
          </span>
          <span v-if="item.zone4hBadge" class="rounded bg-accent-warn/20 px-1.5 py-0.5 text-xs font-medium text-accent-warn">
            {{ item.zone4hBadge.label }}
          </span>
        </div>
        <div class="flex items-center gap-1">
          <button
            type="button"
            class="cursor-pointer rounded border border-border-subtle bg-surface-panel px-1.5 py-0.5 text-xs text-ink-primary hover:border-accent-brand"
            @click="emit('showTrade', item)"
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
      <p class="mt-1 text-ink-secondary">{{ historySummary({ item }) }}</p>
      <p class="mt-0.5 text-ink-muted">
        Seen {{ formatSeenAt(item.seenAtUtc) }}<span v-if="item.closedAtUtc"> · Closed {{ formatClosedAt({ closedUtc: item.closedAtUtc, seenIsoUtc: item.seenAtUtc }) }}</span>
      </p>
    </div>
    <p v-if="items.length === 0" class="text-ink-muted">
      No tradeable signals recorded yet. Live triggers will log here automatically.
    </p>
  </div>
</template>
