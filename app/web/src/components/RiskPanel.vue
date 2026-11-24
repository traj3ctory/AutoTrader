<script setup lang="ts">
import { ref, watch } from "vue";
import type { RiskStatus, TradeRecord } from "../types/analyzer";

const props = defineProps<{
  risk: RiskStatus | null;
  trades: TradeRecord[];
  prefill: { coin: string; type: string; entry: number; stop: number } | null;
  collapsed: boolean;
}>();

const emit = defineEmits<{
  openTrade: [payload: { coin: string; type: string; entry: number; stop: number }];
  closeTrade: [payload: { coin: string; r: number; fill_price?: number }];
  toggleCollapse: [];
}>();

const coin = ref("ZECUSDT.P");
const tradeType = ref("scalp");
const entry = ref("");
const stop = ref("");

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
  }
);

function submitOpen() {
  riskError.value = "";
  const entryNum = Number(entry.value);
  const stopNum = Number(stop.value);
  if (!coin.value.trim() || !Number.isFinite(entryNum) || !Number.isFinite(stopNum)) {
    riskError.value = "Enter coin, entry, and stop.";
    return;
  }
  emit("openTrade", {
    coin: coin.value.trim(),
    type: tradeType.value,
    entry: entryNum,
    stop: stopNum,
  });
  entry.value = "";
  stop.value = "";
}

function submitClose() {
  riskError.value = "";
  const rNum = Number(closeR.value);
  if (!closeCoin.value.trim() || !Number.isFinite(rNum)) {
    riskError.value = "Enter coin and realized R.";
    return;
  }
  const fillNum = closeFill.value ? Number(closeFill.value) : undefined;
  emit("closeTrade", {
    coin: closeCoin.value.trim(),
    r: rNum,
    fill_price: Number.isFinite(fillNum) ? fillNum : undefined,
  });
  closeR.value = "";
  closeFill.value = "";
}
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
            placeholder="Stop"
            class="rounded border border-border-subtle bg-surface-panel px-2 py-1 text-ink-primary"
          />
        </div>
        <button
          type="submit"
          class="w-full cursor-pointer rounded bg-accent-brand px-2.5 py-1 text-xs font-medium text-white hover:opacity-90"
        >
          Log Open
        </button>
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
          class="w-full cursor-pointer rounded border border-border-subtle bg-surface-panel px-2.5 py-1 text-xs font-medium text-ink-primary hover:border-accent-brand"
        >
          Log Close
        </button>
      </form>

      <div>
        <div class="mb-1 text-xs font-semibold text-ink-secondary">Recent Trades</div>
        <table v-if="trades.length > 0" class="w-full text-left text-xs">
          <thead class="border-b border-border-subtle text-ink-muted">
            <tr>
              <th class="py-1 pr-1">Coin</th>
              <th class="py-1 pr-1">Entry/SL</th>
              <th class="py-1 text-right">R</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-border-subtle/50">
            <tr v-for="(t, idx) in trades.slice().reverse().slice(0, 10)" :key="idx">
              <td class="py-1 pr-1 font-medium text-ink-primary">{{ t.coin.replace("USDT.P", "") }}</td>
              <td class="py-1 pr-1 text-ink-secondary">{{ t.entry }} / {{ t.stop }}</td>
              <td
                class="py-1 text-right font-medium"
                :class="t.closed ? ((t.r || 0) >= 0 ? 'text-accent-bull' : 'text-accent-bear') : 'text-accent-warn'"
              >
                {{ t.closed ? `${(t.r || 0) >= 0 ? "+" : ""}${t.r}R` : "OPEN" }}
              </td>
            </tr>
          </tbody>
        </table>
        <p v-else class="text-xs text-ink-muted">No logged trades yet.</p>
      </div>
    </div>
  </section>
</template>
