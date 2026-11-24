<script setup lang="ts">
withDefaults(
  defineProps<{
    size?: "sm" | "md";
    label?: string;
  }>(),
  {
    size: "sm",
    label: "",
  }
);
</script>

<template>
  <span class="inline-flex items-center gap-2">
    <span
      class="inline-block animate-spin rounded-full border-2 border-accent-brand/30 border-t-accent-brand"
      :class="size === 'md' ? 'h-5 w-5' : 'h-3.5 w-3.5'"
    />
    <span v-if="label" class="text-xs font-medium text-ink-secondary">{{ label }}</span>
  </span>
</template>
