<script setup lang="ts">
import { ref } from "vue";
import { CopyTarget, LoadState, type RiskStatus, type ScanResponse, type SignalHistoryEntry } from "../types/analyzer";
import type { INullable } from "../types/common";
import {
  btcEthBadgeClass,
  statusBadgeClass,
  statusLabel,
  trendBadgeClass,
  trendLabel,
} from "../utils/badges";
import LoadingSpinner from "./LoadingSpinner.vue";
import SignalHistoryList from "./SignalHistoryList.vue";

defineProps<{
  scanResult: INullable<ScanResponse>;
  signalHistory: SignalHistoryEntry[];
  risk: INullable<RiskStatus>;
  scanState: LoadState;
  copiedTarget: CopyTarget;
}>();

const emit = defineEmits<{
  selectCoin: [symbol: string, tf?: string];
  copyText: [text: string];
  showTrade: [item: SignalHistoryEntry];
}>();

const showHistory = ref(false);
</script>

<template>
  <section class="shrink-0 rounded-lg border border-border-subtle bg-surface-panel p-3">
    <div class="flex items-center justify-between gap-2">
      <h2 class="text-xs font-semibold uppercase tracking-wide text-ink-primary">Tradeable Signals</h2>
      <div class="flex items-center gap-1.5">
        <button
          type="button"
          class="cursor-pointer rounded border border-border-subtle bg-surface-elevated px-2 py-0.5 text-xs text-ink-secondary transition-all duration-150 hover:text-ink-primary active:scale-95"
          @click="showHistory = !showHistory"
        >
          {{ showHistory ? "Live" : `History (${signalHistory.length})` }}
        </button>
        <span
          v-if="scanResult"
          class="rounded-full px-2 py-0.5 text-xs font-semibold"
          :class="
            risk?.locked
              ? 'bg-accent-bear/20 text-accent-bear'
              : scanResult.tradeable.length > 0
                ? 'bg-accent-bull/20 text-accent-bull'
                : 'bg-surface-elevated text-ink-secondary'
          "
        >
          {{ risk?.locked ? "WATCH ONLY" : `${scanResult.tradeable.length} active` }}
        </span>
      </div>
    </div>

    <div
      v-if="risk?.locked"
      class="mt-2 rounded border border-accent-bear/50 bg-accent-bear/15 px-2 py-1 text-xs font-medium text-accent-bear"
    >
      LOCKED — WATCH ONLY: {{ risk.reasons.join(" · ") }}
    </div>

    <SignalHistoryList
      v-if="showHistory"
      :items="signalHistory"
      :copied-target="copiedTarget"
      @show-trade="(item) => emit('showTrade', item)"
      @copy-text="(text) => emit('copyText', text)"
    />

    <div v-else>
      <div v-if="scanState === LoadState.Loading" class="mt-2">
        <LoadingSpinner label="Scanning coins on live Bybit candles..." />
      </div>

      <div v-if="scanResult && scanResult.tradeable.length > 0" class="mt-2 space-y-2">
      <div
        v-for="item in scanResult.tradeable"
        :key="`${item.symbol}-${item.mode}`"
        class="fade_in_item rounded border p-2 text-xs"
        :class="
          item.status === 'ENGINE_IN_TRADE'
            ? 'border-accent-brand/40 bg-accent-brand/10'
            : item.status === 'LATE_ENTRY'
              ? 'border-accent-warn/40 bg-accent-warn/10'
              : 'border-accent-bull/40 bg-accent-bull/10'
        "
      >
        <div class="flex items-center justify-between gap-1">
          <div class="flex flex-wrap items-center gap-1.5">
            <span
              class="font-semibold"
              :class="
                item.status === 'ENGINE_IN_TRADE'
                  ? 'text-accent-brand'
                  : item.status === 'LATE_ENTRY'
                    ? 'text-accent-warn'
                    : 'text-accent-bull'
              "
            >
              {{ item.symbol }} · {{ item.mode }}
            </span>
            <span class="rounded px-1.5 py-0.5 text-xs font-semibold" :class="statusBadgeClass(item.status)">
              {{ statusLabel(item.status) }}
            </span>
            <span
              v-if="item.zone4hBadge"
              class="rounded bg-accent-warn/20 px-1.5 py-0.5 text-xs font-medium text-accent-warn"
              :title="item.zone4hBadge.zone ? `4H ${item.zone4hBadge.side}: ${item.zone4hBadge.zone.low}-${item.zone4hBadge.zone.high}` : undefined"
            >
              {{ item.zone4hBadge.label }} ({{ item.zone4hBadge.side === "supply" ? "+" : "-" }}{{ item.zone4hBadge.distPct }}%)
            </span>
            <span
              v-if="item.emaBadge"
              class="rounded px-1.5 py-0.5 text-xs font-medium"
              :class="
                item.emaBadge === 'SUPPORTING'
                  ? 'bg-accent-bull/20 text-accent-bull'
                  : item.emaBadge === 'COUNTER'
                    ? 'bg-accent-bear/20 text-accent-bear'
                    : 'bg-surface-elevated text-ink-secondary'
              "
            >
              EMA: {{ item.emaBadge }}
            </span>
            <span class="rounded px-1.5 py-0.5 text-xs font-medium" :class="trendBadgeClass({ trend: item.trend })">
              {{ trendLabel({ trend: item.trend }) }}
            </span>
            <span
              v-if="item.btcEth"
              class="rounded px-1.5 py-0.5 text-xs font-medium"
              :class="btcEthBadgeClass({ btcEth: item.btcEth })"
              title="BTC/ETH 4H structure vs this trade direction (advisory, does not block)"
            >
              BTC/ETH: {{ item.btcEth }}
            </span>
            <span v-if="item.watchOnly" class="rounded bg-accent-warn/20 px-1.5 py-0.5 text-xs font-semibold text-accent-warn">
              WATCH ONLY
            </span>
          </div>
          <div class="flex items-center gap-1">
            <button
              type="button"
              class="cursor-pointer rounded border border-border-subtle bg-surface-panel px-1.5 py-0.5 text-xs text-ink-primary transition-all duration-150 hover:border-accent-brand active:scale-95"
              @click="emit('selectCoin', item.symbol, item.mode === 'Intraday' ? '60' : '15')"
            >
              Chart
            </button>
            <button
              type="button"
              class="cursor-pointer rounded px-2 py-0.5 text-xs font-medium transition-all duration-150 hover:opacity-90 active:scale-95"
              :class="
                item.status === 'ENGINE_IN_TRADE'
                  ? 'bg-accent-brand text-white'
                  : 'bg-accent-bull text-surface-canvas'
              "
              @click="emit('copyText', item.copyText)"
            >
              {{ copiedTarget === CopyTarget.Tradeable ? "Copied!" : "Copy" }}
            </button>
          </div>
        </div>
        <p class="mt-1 text-ink-primary">{{ item.summary }}</p>
        <p v-if="item.watchReasons?.length" class="mt-0.5 text-accent-warn">Capped: {{ item.watchReasons.join(" · ") }}</p>
        <p v-if="item.lowerTier" class="mt-0.5 text-ink-muted">Lower tier: counter-trend scalps tested weaker than with-trend. No sound alert.</p>
      </div>
    </div>

      <p v-else-if="scanResult && scanState !== LoadState.Loading" class="mt-1.5 text-xs text-ink-secondary">
        0 active signals across {{ scanResult.checked.length }} coins right now.
      </p>
    </div>
  </section>
</template>
