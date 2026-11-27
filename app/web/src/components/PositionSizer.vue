<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { TIGHT_STOP_PCT } from "../constants/analyzer";
import type { AnalyzeResponse } from "../types/analyzer";
import type { RiskPrefillPayload } from "../types/common";
import { RiskMode } from "../types/enums";
import { calculatePositionSize } from "../utils/sizing";
import { buildSizerPlan } from "../utils/sizerPlan";

const props = defineProps<{
  analysis: AnalyzeResponse;
  accountBalance: number;
}>();

const emit = defineEmits<{
  updateBalance: [value: number];
  prefillRisk: [payload: RiskPrefillPayload];
}>();

const customEntry = ref("");
const customStop = ref("");
const activePlan = computed(() => buildSizerPlan({ analysis: props.analysis }));
const riskMode = ref(RiskMode.Scalp);

// A manual risk choice lasts only while the same coin and mode are on screen.
watch(
  () => `${props.analysis.symbol}:${activePlan.value?.mode}`,
  () => (riskMode.value = activePlan.value?.mode ?? RiskMode.Scalp),
  { immediate: true }
);

const sizingResult = computed(() =>
  calculatePositionSize({
    entry: Number(customEntry.value) || activePlan.value?.entry || 0,
    stop: Number(customStop.value) || activePlan.value?.stop || 0,
    balance: props.accountBalance,
    riskMode: riskMode.value,
  })
);

function handleBalanceInput(event: Event) {
  const raw = Number((event.target as HTMLInputElement).value);
  if (Number.isFinite(raw) && raw >= 0) {
    emit("updateBalance", raw);
  }
}
</script>

<template>
  <div class="flex flex-wrap items-center justify-between gap-2 rounded border border-border-subtle bg-surface-elevated px-2.5 py-2 text-xs">
    <div class="flex flex-wrap items-center gap-2">
      <span class="font-semibold text-ink-primary">Sizer</span>
      <label class="inline-flex items-center gap-1 text-ink-muted">
        <span>Bal $</span>
        <input
          name="account_balance"
          type="number"
          :value="accountBalance"
          placeholder="1000"
          class="w-20 rounded border border-border-subtle bg-surface-panel px-1.5 py-1 text-ink-primary transition-colors duration-150 focus:border-accent-brand focus:outline-none"
          @input="handleBalanceInput"
        />
      </label>
      <label class="inline-flex items-center gap-1 text-ink-muted">
        <span>Risk</span>
        <select
          v-model="riskMode"
          name="sizer_mode"
          class="rounded border border-border-subtle bg-surface-panel px-1.5 py-1 text-ink-primary transition-colors duration-150 focus:border-accent-brand focus:outline-none"
        >
          <option :value="RiskMode.Scalp">0.5%</option>
          <option :value="RiskMode.Intraday">1.0%</option>
        </select>
      </label>
      <label class="inline-flex items-center gap-1 text-ink-muted">
        <span>Entry</span>
        <input
          v-model="customEntry"
          name="sizer_entry"
          type="number"
          step="any"
          :placeholder="activePlan ? String(activePlan.entry) : 'Entry'"
          class="w-20 rounded border border-border-subtle bg-surface-panel px-1.5 py-1 text-ink-primary transition-colors duration-150 focus:border-accent-brand focus:outline-none"
        />
      </label>
      <label class="inline-flex items-center gap-1 text-ink-muted">
        <span>SL</span>
        <input
          v-model="customStop"
          name="sizer_stop"
          type="number"
          step="any"
          :placeholder="activePlan ? String(activePlan.stop) : 'SL'"
          class="w-20 rounded border border-border-subtle bg-surface-panel px-1.5 py-1 text-ink-primary transition-colors duration-150 focus:border-accent-brand focus:outline-none"
        />
      </label>
    </div>

    <div class="flex items-center gap-2">
      <span v-if="sizingResult" class="text-ink-secondary">
        Risk <strong class="text-ink-primary">${{ sizingResult.riskUsd.toFixed(2) }}</strong> · Notional
        <strong class="text-accent-bull">${{ sizingResult.notionalUsd.toFixed(2) }}</strong> · Qty
        <strong class="text-ink-primary">{{ sizingResult.qty.toFixed(3) }}</strong> · Max Lev
        <strong class="text-accent-warn">{{ sizingResult.maxSafeLev }}x</strong>
        <span
          v-if="sizingResult.stopPct < TIGHT_STOP_PCT"
          class="ml-1 rounded bg-accent-warn/20 px-1.5 py-0.5 text-xs text-accent-warn"
          title="Stop under 1% incurs >14% round-trip fee drag on 1R; prefer Post-Only limits"
        >
          Tight SL ({{ sizingResult.stopPct.toFixed(2) }}%)
        </span>
      </span>
      <span v-else class="text-ink-muted">Enter Entry &amp; Stop</span>

      <button
        v-if="sizingResult"
        type="button"
        class="cursor-pointer rounded bg-accent-brand px-2 py-1 text-xs font-medium text-white transition-all duration-150 hover:opacity-90 active:scale-95"
        @click="
          emit('prefillRisk', {
            coin: analysis.ticker,
            type: riskMode,
            entry: sizingResult.entry,
            stop: sizingResult.stop,
            target: activePlan?.target ?? null,
          })
        "
      >
        → Risk Log
      </button>
    </div>
  </div>
</template>
