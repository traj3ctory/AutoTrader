<script setup lang="ts">
import { computed, ref } from "vue";
import { CopyTarget, LoadState, type AnalyzeResponse } from "../types/analyzer";
import LoadingSpinner from "./LoadingSpinner.vue";

const props = defineProps<{
  analysis: AnalyzeResponse | null;
  analyzeState: LoadState;
  selectedSymbol: string;
  accountBalance: number;
  copiedTarget: CopyTarget;
}>();

const emit = defineEmits<{
  updateBalance: [value: number];
  copySetup: [text: string];
  copyPine: [];
  prefillRisk: [payload: { coin: string; type: string; entry: number; stop: number }];
}>();

const customEntry = ref("");
const customStop = ref("");
const riskMode = ref<"scalp" | "intraday">("scalp");

const activePlan = computed(() => {
  const a = props.analysis;
  if (!a) return null;
  if (a.scalpZone.position) {
    return { mode: "scalp", entry: a.scalpZone.position.entry, stop: a.scalpZone.position.stop };
  }
  if (a.scalp.position) {
    return { mode: "scalp", entry: a.scalp.position.entry, stop: a.scalp.position.stop };
  }
  if (a.intraday.pending) {
    return { mode: "intraday", entry: a.intraday.pending.entry, stop: a.intraday.pending.stop };
  }
  const refSide = a.scalpZone.short.stop ? a.scalpZone.short : a.scalpZone.long.stop ? a.scalpZone.long : a.scalp.short.zone ? a.scalp.short : a.scalp.long;
  if (refSide.stop) {
    return { mode: "scalp", entry: a.price, stop: refSide.stop };
  }
  return null;
});

function emaBadgeClass(badge: string): string {
  if (badge === "SUPPORTING" || badge === "BULL") {
    return "bg-accent-bull/20 text-accent-bull";
  }
  if (badge === "COUNTER" || badge === "BEAR") {
    return "bg-accent-bear/20 text-accent-bear";
  }
  return "bg-surface-panel text-ink-secondary";
}

const sizingResult = computed(() => {
  const entryNum = Number(customEntry.value) || activePlan.value?.entry || 0;
  const stopNum = Number(customStop.value) || activePlan.value?.stop || 0;
  if (!entryNum || !stopNum || entryNum === stopNum || props.accountBalance <= 0) {
    return null;
  }
  const riskPct = riskMode.value === "scalp" ? 0.5 : 1.0;
  const riskUsd = props.accountBalance * (riskPct / 100);
  const stopPct = Math.abs(entryNum - stopNum) / entryNum;
  const notionalUsd = riskUsd / stopPct;
  const qty = notionalUsd / entryNum;
  return {
    entry: entryNum,
    stop: stopNum,
    riskPct,
    riskUsd,
    stopPct: stopPct * 100,
    notionalUsd,
    qty,
  };
});

function handleBalanceInput(event: Event) {
  const raw = Number((event.target as HTMLInputElement).value);
  if (Number.isFinite(raw) && raw >= 0) {
    emit("updateBalance", raw);
  }
}
</script>

<template>
  <section
    v-if="!analysis && analyzeState === LoadState.Loading"
    class="flex shrink-0 items-center justify-center rounded-lg border border-border-subtle bg-surface-panel p-6"
  >
    <LoadingSpinner size="md" :label="`Loading ${selectedSymbol} engine read...`" />
  </section>

  <section v-else-if="analysis" class="shrink-0 space-y-2 rounded-lg border border-border-subtle bg-surface-panel p-3">
    <div class="flex flex-wrap items-center justify-between gap-2">
      <div class="flex flex-wrap items-center gap-2 text-xs text-ink-secondary">
        <span>
          <span class="font-semibold text-ink-primary">5m EMA:</span> {{ analysis.emaOrder }} ({{ analysis.emaSlope }}) ·
          {{ analysis.lastCross.summary }}
          <span v-if="analysis.atr4hPct"> · ATR {{ analysis.atr4hPct }}%</span>
        </span>
        <LoadingSpinner v-if="analyzeState === LoadState.Loading" label="Updating..." />
      </div>

      <div class="flex items-center gap-1.5">
        <button
          type="button"
          class="cursor-pointer rounded border border-border-subtle bg-surface-elevated px-2.5 py-1 text-xs font-medium text-ink-primary hover:border-accent-brand"
          @click="emit('copySetup', analysis.copyText)"
        >
          {{ copiedTarget === CopyTarget.Setup ? "Setup Copied!" : "Copy Setup" }}
        </button>
        <button
          type="button"
          class="cursor-pointer rounded border border-border-subtle bg-surface-elevated px-2.5 py-1 text-xs font-medium text-ink-primary hover:border-accent-brand"
          @click="emit('copyPine')"
        >
          {{ copiedTarget === CopyTarget.Pine ? "Pine Copied!" : "Copy Pine" }}
        </button>
      </div>
    </div>

    <div class="grid gap-2 md:grid-cols-2">
      <div class="rounded border border-border-subtle bg-surface-elevated p-2 text-xs">
        <div class="flex flex-wrap items-center justify-between gap-1.5">
          <div class="flex items-center gap-1.5">
            <span class="font-semibold text-ink-secondary">SCALP ZONE (5m)</span>
            <span
              class="rounded px-1.5 py-0.5 text-xs font-medium"
              :class="emaBadgeClass(analysis.scalpZone.emaBadge)"
              title="EMA 9/20 is supporting context only (not a hard gate)"
            >
              EMA: {{ analysis.scalpZone.emaBadge }}
            </span>
          </div>
          <span
            class="rounded px-1.5 py-0.5 font-semibold"
            :class="
              analysis.scalpZone.tradeable
                ? 'bg-accent-bull/20 text-accent-bull'
                : 'bg-surface-panel text-ink-secondary'
            "
          >
            {{ analysis.scalpZone.verdictKind }}
          </span>
        </div>
        <p class="mt-1 leading-relaxed text-ink-primary">
          {{ analysis.scalpZone.verdictText }}
        </p>
        <div class="mt-1 space-y-0.5 leading-relaxed text-ink-secondary">
          <div>
            <span class="font-semibold text-accent-bull">L:</span> {{ analysis.scalpZone.long.status }}
            <span v-if="analysis.scalpZone.long.zone" class="text-ink-primary">
              · {{ analysis.scalpZone.long.zone.low }}–{{ analysis.scalpZone.long.zone.high }}
              <template v-if="analysis.scalpZone.long.stop"> (SL {{ analysis.scalpZone.long.stop }})</template>
            </span>
          </div>
          <div>
            <span class="font-semibold text-accent-bear">S:</span> {{ analysis.scalpZone.short.status }}
            <span v-if="analysis.scalpZone.short.zone" class="text-ink-primary">
              · {{ analysis.scalpZone.short.zone.low }}–{{ analysis.scalpZone.short.zone.high }}
              <template v-if="analysis.scalpZone.short.stop"> (SL {{ analysis.scalpZone.short.stop }})</template>
            </span>
          </div>
          <div class="border-t border-border-subtle/60 pt-1 text-ink-muted">
            v4 EMA Cross: <span class="text-ink-secondary">{{ analysis.scalp.verdictKind }}</span>
            <template v-if="analysis.scalp.position"> · {{ analysis.scalp.verdictText }}</template>
          </div>
        </div>
      </div>

      <div class="rounded border border-border-subtle bg-surface-elevated p-2 text-xs">
        <div class="flex items-center justify-between">
          <span class="font-semibold text-ink-secondary">INTRADAY (15m)</span>
          <span
            class="rounded px-1.5 py-0.5 font-semibold"
            :class="
              analysis.intraday.tradeable
                ? 'bg-accent-bull/20 text-accent-bull'
                : 'bg-surface-panel text-ink-secondary'
            "
          >
            {{ analysis.intraday.verdictKind }}
          </span>
        </div>
        <p class="mt-1 leading-relaxed text-ink-primary">
          {{ analysis.intraday.verdictText }}
        </p>
        <div class="mt-1 space-y-0.5 leading-relaxed text-ink-secondary">
          <div>
            <span class="font-semibold text-accent-bull">L:</span>
            <span class="text-ink-primary">
              {{
                analysis.intraday.long.nearestZone
                  ? `${analysis.intraday.long.nearestZone.low}–${analysis.intraday.long.nearestZone.high}`
                  : "none"
              }}
            </span>
            · {{ analysis.intraday.long.status }}
          </div>
          <div>
            <span class="font-semibold text-accent-bear">S:</span>
            <span class="text-ink-primary">
              {{
                analysis.intraday.short.nearestZone
                  ? `${analysis.intraday.short.nearestZone.low}–${analysis.intraday.short.nearestZone.high}`
                  : "none"
              }}
            </span>
            · {{ analysis.intraday.short.status }}
          </div>
        </div>
      </div>
    </div>

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
            class="w-20 rounded border border-border-subtle bg-surface-panel px-1.5 py-1 text-ink-primary"
            @input="handleBalanceInput"
          />
        </label>
        <label class="inline-flex items-center gap-1 text-ink-muted">
          <span>Risk</span>
          <select
            v-model="riskMode"
            name="sizer_mode"
            class="rounded border border-border-subtle bg-surface-panel px-1.5 py-1 text-ink-primary"
          >
            <option value="scalp">0.5%</option>
            <option value="intraday">1.0%</option>
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
            class="w-20 rounded border border-border-subtle bg-surface-panel px-1.5 py-1 text-ink-primary"
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
            class="w-20 rounded border border-border-subtle bg-surface-panel px-1.5 py-1 text-ink-primary"
          />
        </label>
      </div>

      <div class="flex items-center gap-2">
        <span v-if="sizingResult" class="text-ink-secondary">
          Risk <strong class="text-ink-primary">${{ sizingResult.riskUsd.toFixed(2) }}</strong> · Notional
          <strong class="text-accent-bull">${{ sizingResult.notionalUsd.toFixed(2) }}</strong> · Qty
          <strong class="text-ink-primary">{{ sizingResult.qty.toFixed(3) }}</strong>
        </span>
        <span v-else class="text-ink-muted">Enter Entry &amp; Stop</span>

        <button
          v-if="sizingResult"
          type="button"
          class="cursor-pointer rounded bg-accent-brand px-2 py-1 text-xs font-medium text-white hover:opacity-90"
          @click="
            emit('prefillRisk', {
              coin: analysis.ticker,
              type: riskMode,
              entry: sizingResult.entry,
              stop: sizingResult.stop,
            })
          "
        >
          → Risk Log
        </button>
      </div>
    </div>
  </section>
</template>
