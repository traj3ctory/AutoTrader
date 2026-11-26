<script setup lang="ts">
import type { ZoneBand } from "../types/chart";

defineProps<{
  bands: ZoneBand[];
}>();
</script>

<template>
  <div class="pointer-events-none absolute inset-y-0 left-0 right-16 z-5 overflow-hidden">
    <div
      v-for="band in bands"
      :key="band.key"
      class="absolute right-0 border-y"
      :class="band.kind === 'demand' ? 'border-accent-bull/50' : 'border-accent-bear/50'"
      :style="{ left: `${band.left}px`, top: `${band.top}px`, height: `${band.height}px`, backgroundColor: band.fill }"
    >
      <span
        class="absolute -top-5 left-1 rounded px-1 text-xs font-medium"
        :class="band.kind === 'demand' ? 'text-accent-bull' : 'text-accent-bear'"
      >
        {{ band.label }}
      </span>
    </div>
  </div>
</template>
