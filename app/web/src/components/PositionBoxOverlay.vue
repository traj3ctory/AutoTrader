<script setup lang="ts">
import type { PositionBoxCoords } from "../types/chart";
import type { INullable } from "../types/common";

defineProps<{
  box: INullable<PositionBoxCoords>;
}>();
</script>

<template>
  <div
    v-if="box"
    class="pointer-events-none absolute inset-y-0 left-0 right-16 z-10 overflow-hidden"
  >
    <div
      class="absolute inset-y-0 transition-all duration-150"
      :style="{ left: `${box.left}px`, width: `${box.width}px` }"
    >
      <div
        class="absolute inset-x-0 border border-accent-bull/60 bg-accent-bull/10 transition-all duration-150"
        :style="{ top: `${box.rewardTop}px`, height: `${box.rewardHeight}px` }"
      >
        <span
          class="absolute right-1 rounded bg-accent-bull/90 px-1 text-xs font-semibold text-surface-canvas"
          :class="box.direction === 'long' ? 'top-0.5' : 'bottom-0.5'"
        >
          TP1 {{ box.target }} ({{ box.rr }}R)
        </span>
      </div>
      <div
        class="absolute inset-x-0 border border-accent-bear/60 bg-accent-bear/10 transition-all duration-150"
        :style="{ top: `${box.riskTop}px`, height: `${box.riskHeight}px` }"
      >
        <span
          class="absolute right-1 rounded bg-accent-bear/90 px-1 text-xs font-semibold text-white"
          :class="box.direction === 'long' ? 'bottom-0.5' : 'top-0.5'"
        >
          SL {{ box.stop }}
        </span>
      </div>
      <div
        class="absolute inset-x-0 -translate-y-1/2 border-t border-accent-brand transition-all duration-150"
        :style="{ top: `${box.entryTop}px` }"
      >
        <span class="inline-block rounded bg-accent-brand/80 px-1 text-xs font-semibold text-white">
          {{ box.direction.toUpperCase() }} {{ box.entry }} · {{ box.rr }}R
        </span>
      </div>
    </div>
  </div>
</template>
