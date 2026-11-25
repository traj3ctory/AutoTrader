<script setup lang="ts">
import { CopyTarget, LoadState, type AnalyzeResponse } from "../types/analyzer";
import type { INullable, RiskPrefillPayload } from "../types/common";
import { emaBadgeClass } from "../utils/badges";
import LoadingSpinner from "./LoadingSpinner.vue";
import PositionSizer from "./PositionSizer.vue";

defineProps<{
  analysis: INullable<AnalyzeResponse>;
  analyzeState: LoadState;
  selectedSymbol: string;
  accountBalance: number;
  copiedTarget: CopyTarget;
}>();

const emit = defineEmits<{
  updateBalance: [value: number];
  copySetup: [text: string];
  copyPine: [];
  syncLedger: [];
  prefillRisk: [payload: RiskPrefillPayload];
}>();
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
          <span title="Reported context only, never a gate (backtests rejected a hard VWAP gate)">
            · VWAP {{ analysis.vwap }} ({{ analysis.price >= analysis.vwap ? "price above" : "price below" }})
          </span>
          <span v-if="analysis.atr4hPct"> · ATR {{ analysis.atr4hPct }}%</span>
        </span>
        <span
          v-if="analysis.zone4hBadge"
          class="rounded bg-accent-warn/20 px-1.5 py-0.5 font-medium text-accent-warn"
          :title="analysis.zone4hBadge.zone ? `4H ${analysis.zone4hBadge.side}: ${analysis.zone4hBadge.zone.low}-${analysis.zone4hBadge.zone.high}` : undefined"
        >
          {{ analysis.zone4hBadge.label }} ({{ analysis.zone4hBadge.side === "supply" ? "+" : "-" }}{{ analysis.zone4hBadge.distPct }}%)
        </span>
        <LoadingSpinner v-if="analyzeState === LoadState.Loading" label="Updating..." />
      </div>

      <div class="flex items-center gap-1.5">
        <button
          type="button"
          class="cursor-pointer rounded border border-border-subtle bg-surface-elevated px-2.5 py-1 text-xs font-medium text-ink-primary transition-all duration-150 hover:border-accent-brand active:scale-95"
          @click="emit('copySetup', analysis.copyText)"
        >
          {{ copiedTarget === CopyTarget.Setup ? "Setup Copied!" : "Copy Setup" }}
        </button>
        <button
          type="button"
          class="cursor-pointer rounded border border-border-subtle bg-surface-elevated px-2.5 py-1 text-xs font-medium text-ink-primary transition-all duration-150 hover:border-accent-brand active:scale-95"
          @click="emit('copyPine')"
        >
          {{ copiedTarget === CopyTarget.Pine ? "Pine Copied!" : "Copy Pine" }}
        </button>
        <button
          type="button"
          class="cursor-pointer rounded border border-border-subtle bg-surface-elevated px-2.5 py-1 text-xs font-medium text-ink-primary transition-all duration-150 hover:border-accent-brand active:scale-95"
          @click="emit('syncLedger')"
        >
          {{ copiedTarget === CopyTarget.Ledger ? "Ledger Synced!" : "Sync Ledger" }}
        </button>
      </div>
    </div>

    <div class="grid gap-2 md:grid-cols-2">
      <div class="rounded border border-border-subtle bg-surface-elevated p-2 text-xs transition-colors duration-150">
        <div class="flex flex-wrap items-center justify-between gap-1.5">
          <span class="font-semibold text-ink-secondary">SCALP v4 EMA (5m)</span>
          <span
            class="rounded px-1.5 py-0.5 font-semibold"
            :class="analysis.scalp.tradeable ? 'bg-accent-bull/20 text-accent-bull' : 'bg-surface-panel text-ink-secondary'"
          >
            {{ analysis.scalp.verdictKind }}
          </span>
        </div>
        <p class="mt-1 leading-relaxed text-ink-primary">{{ analysis.scalp.verdictText }}</p>
        <div
          v-if="analysis.scalp.position?.targets?.length"
          class="mt-1 space-y-0.5 rounded bg-surface-panel/70 px-2 py-1 text-xs"
        >
          <div
            v-for="tp in analysis.scalp.position.targets"
            :key="tp.label"
            class="flex flex-wrap items-center justify-between gap-1"
          >
            <span class="font-medium text-accent-bull">{{ tp.label }} {{ tp.price }} ({{ tp.rr }}R)</span>
            <span class="text-ink-muted">{{ tp.note }}</span>
          </div>
        </div>
        <div class="mt-1 space-y-0.5 leading-relaxed text-ink-secondary">
          <div>
            <span class="font-semibold text-accent-bull">L:</span> {{ analysis.scalp.long.status }}
            <span v-if="analysis.scalp.long.zone" class="text-ink-primary">
              · {{ analysis.scalp.long.zone.low }}–{{ analysis.scalp.long.zone.high }}
              <template v-if="analysis.scalp.long.stop"> (SL {{ analysis.scalp.long.stop }})</template>
            </span>
          </div>
          <div>
            <span class="font-semibold text-accent-bear">S:</span> {{ analysis.scalp.short.status }}
            <span v-if="analysis.scalp.short.zone" class="text-ink-primary">
              · {{ analysis.scalp.short.zone.low }}–{{ analysis.scalp.short.zone.high }}
              <template v-if="analysis.scalp.short.stop"> (SL {{ analysis.scalp.short.stop }})</template>
            </span>
          </div>
          <div class="border-t border-border-subtle/60 pt-1 text-ink-muted">
            <span class="font-medium">Scalp Zone [CONTEXT ONLY, untested, not a signal]:</span>
            <span class="ml-1 rounded px-1 py-0.5 text-xs" :class="emaBadgeClass(analysis.scalpZone.emaBadge)">
              EMA: {{ analysis.scalpZone.emaBadge }}
            </span>
            <span class="ml-1 text-ink-secondary">{{ analysis.scalpZone.verdictKind }}</span>
            <template v-if="analysis.scalpZone.position"> · {{ analysis.scalpZone.verdictText }}</template>
          </div>
        </div>
      </div>

      <div class="rounded border border-border-subtle bg-surface-elevated p-2 text-xs transition-colors duration-150">
        <div class="flex items-center justify-between">
          <span class="font-semibold text-ink-secondary">INTRADAY (15m)</span>
          <span
            class="rounded px-1.5 py-0.5 font-semibold"
            :class="analysis.intraday.tradeable ? 'bg-accent-bull/20 text-accent-bull' : 'bg-surface-panel text-ink-secondary'"
          >
            {{ analysis.intraday.verdictKind }}
          </span>
        </div>
        <p class="mt-1 leading-relaxed text-ink-primary">{{ analysis.intraday.verdictText }}</p>
        <div
          v-if="(analysis.intraday.position?.targets || analysis.intraday.pending?.targets)?.length"
          class="mt-1 space-y-0.5 rounded bg-surface-panel/70 px-2 py-1 text-xs"
        >
          <div
            v-for="tp in analysis.intraday.position?.targets || analysis.intraday.pending?.targets || []"
            :key="tp.label"
            class="flex flex-wrap items-center justify-between gap-1"
          >
            <span class="font-medium text-accent-bull">{{ tp.label }} {{ tp.price }} ({{ tp.rr }}R)</span>
            <span class="text-ink-muted">{{ tp.note }}</span>
          </div>
        </div>
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

    <PositionSizer
      :analysis="analysis"
      :account-balance="accountBalance"
      @update-balance="(val) => emit('updateBalance', val)"
      @prefill-risk="(payload) => emit('prefillRisk', payload)"
    />
  </section>
</template>
