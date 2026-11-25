<script setup lang="ts">
import { computed, ref, watch } from "vue";
import type { RiskStatus, TradeRecord } from "../types/analyzer";
import type { CloseTradePayload, INullable, OpenTradePayload, RiskPrefillPayload } from "../types/common";
import { buildClosePayload, buildOpenPayload } from "../utils/riskForms";
import { findCorrelatedOpenTrades } from "../utils/riskHelpers";

const props = defineProps<{
  risk: INullable<RiskStatus>;
  trades: TradeRecord[];
  prefill: INullable<RiskPrefillPayload>;
  collapsed: boolean;
}>();

const emit = defineEmits<{
  openTrade: [payload: OpenTradePayload];
  closeTrade: [payload: CloseTradePayload];
  clearTrades: [];
  toggleCollapse: [];
}>();

const coin = ref("ZECUSDT.P");
const tradeType = ref("scalp");
const entry = ref("");
const stop = ref("");
const target = ref("");

const closeCoin = ref("");
const closeR = ref("");
const closeFill = ref("");
const riskError = ref("");

watch(
  () => props.prefill,
  (next) => {
    if (!next) return;
    coin.value = next.coin;
    tradeType.value = next.type;
    entry.value = String(next.entry);
    stop.value = String(next.stop);
    target.value = next.target != null ? String(next.target) : "";
  }
);

function submitOpen() {
  const { payload, error } = buildOpenPayload({ coin: coin.value, type: tradeType.value, entry: entry.value, stop: stop.value, target: target.value });
  riskError.value = error ?? "";
  if (!payload) return;
  emit("openTrade", payload);
  entry.value = "";
  stop.value = "";
  target.value = "";
}

function submitClose() {
  const { payload, error } = buildClosePayload({ coin: closeCoin.value, r: closeR.value, fill: closeFill.value });
  riskError.value = error ?? "";
  if (!payload) return;
  emit("closeTrade", payload);
  closeR.value = "";
  closeFill.value = "";
}

function confirmClear() {
  if (window.confirm("Clear older closed trades? (Open trades and today's risk lock stay intact.)")) {
    emit("clearTrades");
  }
}

const correlatedWarning = computed(() =>
  findCorrelatedOpenTrades({
    coin: coin.value,
    entry: Number(entry.value),
    stop: Number(stop.value),
    trades: props.trades,
  })
);
</script>

<template>
  <section class="flex-col gap-2 rounded-lg border border-border-subtle bg-surface-panel p-3">
    <div class="flex shrink-0 items-center justify-between gap-2">
      <button
        type="button"
        class="flex cursor-pointer items-center gap-1.5 text-left text-xs font-semibold uppercase tracking-wide text-ink-primary"
        @click="emit('toggleCollapse')"
      >
        <span class="hidden text-ink-muted lg:inline">{{ collapsed ? "▸" : "▾" }}</span>
        <span>Risk Guard &amp; Journal</span>
      </button>
      <span v-if="risk" class="text-xs text-ink-secondary">
        {{ risk.open.length }}/2 · Streak {{ risk.streak }}/2
      </span>
    </div>

    <div class="min-h-0 flex-1 space-y-2 overflow-y-auto" :class="{ 'lg:hidden': collapsed }">
      <p class="text-xs text-ink-muted">Max 2 open · 3% daily cap · 2-loss stop</p>
      <p v-if="riskError" class="text-xs text-accent-bear">{{ riskError }}</p>

      <form
        class="space-y-1.5 rounded border border-border-subtle bg-surface-elevated p-2"
        @submit.prevent="submitOpen"
      >
        <div class="text-xs font-semibold text-ink-primary">Log Open Trade</div>
        <div class="grid grid-cols-2 gap-1.5 text-xs">
          <input
            v-model="coin"
            name="open_coin"
            type="text"
            placeholder="Coin (ZEC)"
            class="rounded border border-border-subtle bg-surface-panel px-2 py-1 text-ink-primary"
          />
          <select
            v-model="tradeType"
            name="open_type"
            class="rounded border border-border-subtle bg-surface-panel px-2 py-1 text-ink-primary"
          >
            <option value="scalp">Scalp (0.5%)</option>
            <option value="intraday">Intraday (1.0%)</option>
          </select>
          <div class="col-span-2 grid grid-cols-3 gap-1.5">
            <input
              v-model="entry"
              name="open_entry"
              type="number"
              step="any"
              placeholder="Entry"
              class="rounded border border-border-subtle bg-surface-panel px-2 py-1 text-ink-primary"
            />
            <input
              v-model="stop"
              name="open_stop"
              type="number"
              step="any"
              placeholder="SL"
              class="rounded border border-border-subtle bg-surface-panel px-2 py-1 text-ink-primary"
            />
            <input
              v-model="target"
              name="open_target"
              type="number"
              step="any"
              placeholder="TP"
              class="rounded border border-border-subtle bg-surface-panel px-2 py-1 text-ink-primary"
            />
          </div>
        </div>
        <button
          type="submit"
          class="w-full cursor-pointer rounded bg-accent-brand px-2.5 py-1 text-xs font-medium text-white transition-all duration-150 hover:opacity-90 active:scale-95"
        >
          Log Open
        </button>
        <p
          v-if="correlatedWarning"
          class="rounded border border-accent-warn/40 bg-accent-warn/10 px-2 py-1 text-xs text-accent-warn"
        >
          {{ correlatedWarning }}
        </p>
      </form>

      <form
        class="space-y-1.5 rounded border border-border-subtle bg-surface-elevated p-2"
        @submit.prevent="submitClose"
      >
        <div class="text-xs font-semibold text-ink-primary">Log Close Trade</div>
        <div class="grid grid-cols-3 gap-1.5 text-xs">
          <input
            v-model="closeCoin"
            name="close_coin"
            type="text"
            placeholder="Coin"
            class="rounded border border-border-subtle bg-surface-panel px-2 py-1 text-ink-primary"
          />
          <input
            v-model="closeR"
            name="close_r"
            type="number"
            step="any"
            placeholder="R"
            class="rounded border border-border-subtle bg-surface-panel px-2 py-1 text-ink-primary"
          />
          <input
            v-model="closeFill"
            name="close_fill"
            type="number"
            step="any"
            placeholder="Fill"
            class="rounded border border-border-subtle bg-surface-panel px-2 py-1 text-ink-primary"
          />
        </div>
        <button
          type="submit"
          class="w-full cursor-pointer rounded border border-border-subtle bg-surface-panel px-2.5 py-1 text-xs font-medium text-ink-primary transition-all duration-150 hover:border-accent-brand active:scale-95"
        >
          Log Close
        </button>
      </form>

      <div>
        <div class="mb-1 flex items-center justify-between">
          <span class="text-xs font-semibold text-ink-secondary">Recent Trades</span>
          <button
            v-if="trades.length > 0"
            type="button"
            class="cursor-pointer rounded border border-border-subtle bg-surface-elevated px-1.5 py-0.5 text-xs text-ink-secondary hover:border-accent-bear hover:text-accent-bear"
            @click="confirmClear"
          >
            Clear
          </button>
        </div>
        <table v-if="trades.length > 0" class="w-full text-left text-xs">
          <thead class="border-b border-border-subtle text-ink-muted">
            <tr>
              <th class="py-1 pr-1">Coin</th>
              <th class="py-1 pr-1">Entry / SL / TP</th>
              <th class="py-1 text-right">Result</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-border-subtle/50">
            <tr v-for="(t, idx) in trades.slice().reverse().slice(0, 10)" :key="idx" class="fade_in_item">
              <td class="py-1 pr-1 font-medium text-ink-primary">{{ t.coin.replace("USDT.P", "") }}</td>
              <td class="py-1 pr-1 text-ink-secondary">
                {{ t.entry }} / {{ t.stop }}{{ t.target != null ? ` / ${t.target}` : "" }}
              </td>
              <td
                class="py-1 text-right font-medium"
                :class="t.closed ? ((t.r || 0) > 0 ? 'text-accent-bull' : (t.r || 0) < 0 ? 'text-accent-bear' : 'text-ink-secondary') : 'text-accent-warn'"
              >
                {{
                  t.closed
                    ? `${(t.r || 0) > 0 ? "WIN " : (t.r || 0) < 0 ? "LOSS " : "BE "}${(t.r || 0) >= 0 ? "+" : ""}${t.r}R`
                    : "OPEN"
                }}
              </td>
            </tr>
          </tbody>
        </table>
        <p v-else class="text-xs text-ink-muted">No logged trades yet.</p>
      </div>
    </div>
  </section>
</template>
