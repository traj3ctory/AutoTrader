<script setup lang="ts">
import { historySummary } from "../utils/historyText";
import { formatSeenAt } from "../utils/time";
import { ref } from "vue";
import { AUTOMATION_GATE_GOAL } from "../constants/analyzer";
import { useDashboardStats } from "../composables/useDashboardStats";
import { LoadState, type DashboardResponse } from "../types/analyzer";
import LoadingSpinner from "./LoadingSpinner.vue";

const props = defineProps<{
  dashboard: DashboardResponse | null;
  dashboardState: LoadState;
}>();

const emit = defineEmits<{
  refresh: [];
  selectCoin: [symbol: string];
}>();

const searchQuery = ref("");

const { scorecardStats, mistakeTags, filteredRecords } = useDashboardStats({
  dashboard: () => props.dashboard,
  searchQuery,
});
</script>

<template>
  <div class="flex min-h-0 flex-1 flex-col gap-2.5 overflow-y-auto p-2.5">
    <div class="shrink-0 space-y-2.5 rounded-lg border border-border-subtle bg-surface-panel p-3">
      <div class="flex flex-wrap items-center justify-between gap-2">
        <div class="flex flex-wrap items-center gap-3">
          <div>
            <h2 class="text-sm font-semibold text-ink-primary">Scorecard, Journal &amp; Backtest Analysis</h2>
            <p class="text-xs text-ink-secondary">
              Scorecard updated {{ dashboard?.scorecard.last_updated || "—" }} · Consolidated review &amp; edge tracking
            </p>
          </div>

          <div class="flex flex-wrap items-center gap-2 text-xs">
            <div class="rounded border border-border-subtle bg-surface-elevated px-2.5 py-1">
              Reviewed: <strong class="text-ink-primary">{{ scorecardStats.reviewed }}</strong>
            </div>
            <div class="rounded border border-border-subtle bg-surface-elevated px-2.5 py-1">
              Correct: <strong class="text-accent-bull">{{ scorecardStats.correct }}</strong>
            </div>
            <div class="rounded border border-border-subtle bg-surface-elevated px-2.5 py-1">
              Invalidated: <strong class="text-accent-warn">{{ scorecardStats.invalidated }}</strong>
            </div>
            <div class="rounded border border-border-subtle bg-surface-elevated px-2.5 py-1">
              Accuracy: <strong class="text-accent-brand">{{ scorecardStats.accuracyPct }}%</strong>
            </div>
            <div class="rounded border border-border-subtle bg-surface-elevated px-2.5 py-1">
              Trades: <strong class="text-ink-primary">{{ scorecardStats.taken }}</strong>
              ({{ scorecardStats.wins }}W / {{ scorecardStats.losses }}L)
            </div>
          </div>
        </div>

        <button
          type="button"
          class="inline-flex cursor-pointer items-center gap-1.5 rounded border border-border-subtle bg-surface-elevated px-2.5 py-1 text-xs font-medium text-ink-primary hover:border-accent-brand disabled:opacity-50"
          :disabled="dashboardState === LoadState.Loading"
          @click="emit('refresh')"
        >
          <LoadingSpinner v-if="dashboardState === LoadState.Loading" label="Loading..." />
          <span v-else>Refresh</span>
        </button>
      </div>

      <div class="flex flex-wrap items-center justify-between gap-3 rounded border border-border-subtle bg-surface-elevated px-3 py-2 text-xs">
        <div class="flex min-w-64 flex-1 items-center gap-3">
          <span class="whitespace-nowrap text-ink-secondary">
            Automation Gate:
            <strong class="text-ink-primary">{{ scorecardStats.qualifying }} / {{ AUTOMATION_GATE_GOAL }}</strong>
            ({{ scorecardStats.gatePct }}%)
          </span>
          <div class="h-2 flex-1 overflow-hidden rounded-full bg-surface-panel">
            <div
              class="h-full bg-accent-brand transition-all"
              :style="{ width: `${scorecardStats.gatePct}%` }"
            />
          </div>
        </div>

        <div class="flex flex-wrap items-center gap-1.5">
          <span
            v-for="[tag, count] in mistakeTags.slice(0, 6)"
            :key="tag"
            class="rounded border border-border-subtle bg-surface-panel px-2 py-0.5 text-xs text-ink-secondary"
          >
            {{ tag }} <strong class="text-accent-brand">{{ count }}</strong>
          </span>
        </div>
      </div>
    </div>

    <div class="grid min-h-0 flex-1 grid-cols-1 gap-2.5 lg:grid-cols-12">
      <div class="flex min-h-0 flex-col gap-2.5 lg:col-span-7">
        <section class="flex min-h-0 flex-1 flex-col rounded-lg border border-border-subtle bg-surface-panel p-3">
          <div class="mb-2 flex shrink-0 flex-wrap items-center justify-between gap-2">
            <h3 class="text-xs font-semibold uppercase tracking-wide text-ink-primary">
              Scorecard History ({{ filteredRecords.length }})
            </h3>
            <input
              v-model="searchQuery"
              name="scorecard_search"
              type="text"
              placeholder="Filter coin, type, outcome..."
              class="w-56 rounded border border-border-subtle bg-surface-elevated px-2.5 py-1 text-xs text-ink-primary placeholder:text-ink-muted"
            />
          </div>
          <div class="min-h-0 flex-1 overflow-y-auto">
            <table class="w-full text-left text-xs">
              <thead class="border-b border-border-subtle text-ink-muted">
                <tr>
                  <th class="py-1.5 pr-2">Date</th>
                  <th class="py-1.5 pr-2">Coin</th>
                  <th class="py-1.5 pr-2">Type</th>
                  <th class="py-1.5 pr-2">Outcome</th>
                  <th class="py-1.5 pr-2">Trade</th>
                  <th class="py-1.5">Note</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-border-subtle/50">
                <tr v-for="rec in filteredRecords" :key="rec.id">
                  <td class="py-1.5 pr-2 whitespace-nowrap text-ink-secondary">{{ rec.date }}</td>
                  <td class="py-1.5 pr-2 whitespace-nowrap font-medium">
                    <button
                      type="button"
                      class="cursor-pointer text-accent-brand hover:underline"
                      @click="emit('selectCoin', rec.coin.replace('.P', ''))"
                    >
                      {{ rec.coin.replace("USDT.P", "") }}
                    </button>
                  </td>
                  <td class="py-1.5 pr-2 whitespace-nowrap text-ink-secondary">
                    {{ rec.trade_type }} · {{ rec.direction }}
                  </td>
                  <td
                    class="py-1.5 pr-2 whitespace-nowrap font-medium"
                    :class="rec.outcome.includes('Correct') ? 'text-accent-bull' : 'text-accent-bear'"
                  >
                    {{ rec.outcome }}
                  </td>
                  <td class="py-1.5 pr-2 whitespace-nowrap text-ink-secondary">{{ rec.trade_result }}</td>
                  <td class="py-1.5 text-ink-secondary">{{ rec.review_note }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>

        <section class="flex min-h-0 flex-1 flex-col rounded-lg border border-border-subtle bg-surface-panel p-3">
          <h3 class="mb-2 shrink-0 text-xs font-semibold uppercase tracking-wide text-ink-primary">
            Ledger Lessons &amp; Mistake Tags
          </h3>
          <div class="min-h-0 flex-1 space-y-2 overflow-y-auto text-xs">
            <div
              v-for="(item, idx) in (dashboard?.journal || []).slice(0, 12)"
              :key="idx"
              class="rounded border border-border-subtle bg-surface-elevated p-2"
            >
              <div class="flex flex-wrap items-center justify-between gap-2">
                <span class="font-semibold text-ink-primary">
                  {{ item.coin.replace("USDT.P", "") }} · {{ item.date }}
                </span>
                <span class="rounded bg-surface-panel px-2 py-0.5 text-xs text-accent-warn">
                  {{ item.mistake_tag }}
                </span>
              </div>
              <p class="mt-1 text-ink-primary">{{ item.result }}</p>
              <p class="mt-0.5 text-ink-secondary">{{ item.note }}</p>
            </div>
          </div>
        </section>
      </div>

      <div class="flex min-h-0 flex-col gap-2.5 lg:col-span-5">
        <section class="rounded-lg border border-border-subtle bg-surface-panel p-3">
          <h3 class="mb-2 text-xs font-semibold uppercase tracking-wide text-ink-primary">
            Recent Tradeable Signals ({{ (dashboard?.signalHistory || []).length }})
          </h3>
          <div v-if="(dashboard?.signalHistory || []).length > 0" class="max-h-40 space-y-1.5 overflow-y-auto text-xs">
            <div
              v-for="sig in (dashboard?.signalHistory || []).slice(0, 12)"
              :key="sig.id"
              class="rounded border border-border-subtle bg-surface-elevated p-2"
            >
              <div class="flex items-center justify-between gap-2">
                <button
                  type="button"
                  class="cursor-pointer font-semibold text-accent-brand hover:underline"
                  @click="emit('selectCoin', sig.symbol)"
                >
                  {{ sig.symbol }} · {{ sig.mode }}
                </button>
                <span class="text-ink-muted">{{ formatSeenAt(sig.seenAtUtc) }}</span>
              </div>
              <p class="mt-0.5 text-ink-secondary">{{ historySummary({ item: sig }) }}</p>
            </div>
          </div>
          <p v-else class="text-xs text-ink-muted">No tradeable signals recorded yet.</p>
        </section>

        <section class="rounded-lg border border-border-subtle bg-surface-panel p-3">
          <h3 class="mb-2 text-xs font-semibold uppercase tracking-wide text-ink-primary">
            Out-of-Sample Backtest (Aug 1 – Nov 15, 2026)
          </h3>
          <pre class="overflow-x-auto whitespace-pre-wrap rounded border border-border-subtle bg-surface-elevated p-2.5 text-xs leading-relaxed text-ink-secondary">{{ dashboard?.backtests.oos || "No OOS results found." }}</pre>
        </section>

        <section class="min-h-0 flex-1 overflow-y-auto rounded-lg border border-border-subtle bg-surface-panel p-3">
          <h3 class="mb-2 text-xs font-semibold uppercase tracking-wide text-ink-primary">
            Edge Decay &amp; Slice Breakdown (2026-11-17)
          </h3>
          <pre class="overflow-x-auto whitespace-pre-wrap rounded border border-border-subtle bg-surface-elevated p-2.5 text-xs leading-relaxed text-ink-secondary">{{ dashboard?.backtests.edgeDecay || "No edge-decay results found." }}</pre>
        </section>
      </div>
    </div>
  </div>
</template>
