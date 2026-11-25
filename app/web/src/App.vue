<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { useAnalyzerStore } from "./stores/useAnalyzerStore";
import { AppView, CopyTarget, LoadState, SidebarTab } from "./types/analyzer";
import type { INullable, RiskPrefillPayload } from "./types/common";
import TopBar from "./components/TopBar.vue";
import TradeableBanner from "./components/TradeableBanner.vue";
import CandleChart from "./components/CandleChart.vue";
import SetupDetail from "./components/SetupDetail.vue";
import MoversPanel from "./components/MoversPanel.vue";
import RiskPanel from "./components/RiskPanel.vue";
import DashboardView from "./components/DashboardView.vue";

const store = useAnalyzerStore();
const activeView = ref<AppView>(AppView.Analyzer);
const sidebarTab = ref<SidebarTab>(SidebarTab.Movers);
const moversCollapsed = ref(false);
const riskCollapsed = ref(false);
const riskPrefill = ref<INullable<RiskPrefillPayload>>(null);

const isBusy = computed(
  () =>
    store.overviewState === LoadState.Loading ||
    store.analyzeState === LoadState.Loading ||
    store.scanState === LoadState.Loading ||
    store.moversState === LoadState.Loading ||
    store.dashboardState === LoadState.Loading
);

function handleSelectCoin(symbol: string, tf?: string) {
  activeView.value = AppView.Analyzer;
  store.analyzeCoin({ symbol, tf });
}

function handleChangeView(view: AppView) {
  activeView.value = view;
  if (view === AppView.Dashboard && !store.dashboard) {
    store.loadDashboard();
  }
}

function handlePrefillRisk(payload: RiskPrefillPayload) {
  riskPrefill.value = payload;
  riskCollapsed.value = false;
  sidebarTab.value = SidebarTab.Risk;
}

let scanTimer: number | null = null;

function restartScanTimer() {
  if (scanTimer !== null) {
    window.clearInterval(scanTimer);
    scanTimer = null;
  }
  const mins = store.autoScanMinutes;
  if (mins > 0) {
    scanTimer = window.setInterval(() => {
      if (store.scanState !== LoadState.Loading) {
        void store.runScan();
      }
      if (store.analyzeState !== LoadState.Loading) {
        void store.analyzeCoin({ symbol: store.selectedSymbol, tf: store.selectedTf });
      }
    }, mins * 60_000);
  }
}

watch(() => store.autoScanMinutes, restartScanTimer);

onMounted(async () => {
  await store.loadOverview();
  await Promise.all([
    store.analyzeCoin({ symbol: store.selectedSymbol }),
    store.runScan(),
    store.loadDashboard(),
  ]);
  restartScanTimer();
});

onBeforeUnmount(() => {
  if (scanTimer !== null) {
    window.clearInterval(scanTimer);
    scanTimer = null;
  }
});
</script>

<template>
  <div class="flex min-h-screen flex-col bg-surface-canvas text-ink-primary lg:h-screen lg:overflow-hidden">
    <div class="h-0.5 w-full shrink-0 bg-surface-panel">
      <div v-if="isBusy" class="h-full w-full animate-pulse bg-accent-brand" />
    </div>

    <TopBar
      :overview="store.overview"
      :risk="store.risk"
      :scan-state="store.scanState"
      :ledger-symbols="store.ledgerSymbols"
      :tv-symbols="store.tvSymbols"
      :selected-symbol="store.selectedSymbol"
      :active-view="activeView"
      :sound-enabled="store.soundEnabled"
      :auto-scan-minutes="store.autoScanMinutes"
      @scan="store.runScan()"
      @select-coin="handleSelectCoin"
      @change-view="handleChangeView"
      @toggle-sound="store.toggleSound()"
      @change-auto-scan="(mins) => (store.autoScanMinutes = mins)"
    />

    <div
      v-if="store.errorMessage"
      class="mx-2.5 mt-2 shrink-0 rounded border border-accent-bear/40 bg-accent-bear/10 px-3 py-1.5 text-xs text-accent-bear"
    >
      {{ store.errorMessage }}
    </div>

    <DashboardView
      v-if="activeView === AppView.Dashboard"
      :dashboard="store.dashboard"
      :dashboard-state="store.dashboardState"
      @refresh="store.loadDashboard()"
      @select-coin="handleSelectCoin"
    />

    <main v-else class="grid min-h-0 flex-1 grid-cols-1 gap-2.5 p-2.5 lg:grid-cols-12">
      <div class="flex min-h-0 flex-col gap-2.5 lg:col-span-9">
        <CandleChart
          :analysis="store.analysis"
          :analyze-state="store.analyzeState"
          :selected-symbol="store.selectedSymbol"
          :selected-tf="store.selectedTf"
          @change-tf="(tf) => store.analyzeCoin({ tf })"
        />

        <SetupDetail
          :analysis="store.analysis"
          :analyze-state="store.analyzeState"
          :selected-symbol="store.selectedSymbol"
          :account-balance="store.accountBalance"
          :copied-target="store.copiedTarget"
          @update-balance="(val) => (store.accountBalance = val)"
          @copy-setup="(text) => store.copySetup({ text, target: CopyTarget.Setup })"
          @copy-pine="store.copyCurrentPine({ rebuild: false })"
          @sync-ledger="store.syncToLedger({ symbol: store.selectedSymbol })"
          @prefill-risk="handlePrefillRisk"
        />
      </div>

      <aside class="flex min-h-0 flex-col gap-2.5 lg:col-span-3">
        <TradeableBanner
          :scan-result="store.scanResult"
          :signal-history="store.signalHistory"
          :risk="store.risk"
          :scan-state="store.scanState"
          :copied-target="store.copiedTarget"
          @select-coin="handleSelectCoin"
          @copy-text="(text) => store.copySetup({ text, target: CopyTarget.Tradeable })"
        />

        <div class="grid shrink-0 grid-cols-2 gap-1 rounded-lg border border-border-subtle bg-surface-panel p-1 lg:hidden">
          <button
            type="button"
            class="cursor-pointer rounded py-1.5 text-xs font-medium"
            :class="
              sidebarTab === SidebarTab.Movers
                ? 'bg-accent-brand text-white'
                : 'text-ink-secondary hover:text-ink-primary'
            "
            @click="sidebarTab = SidebarTab.Movers"
          >
            Crypto Movers
          </button>
          <button
            type="button"
            class="cursor-pointer rounded py-1.5 text-xs font-medium"
            :class="
              sidebarTab === SidebarTab.Risk
                ? 'bg-accent-brand text-white'
                : 'text-ink-secondary hover:text-ink-primary'
            "
            @click="sidebarTab = SidebarTab.Risk"
          >
            Risk &amp; Journal ({{ store.risk?.open.length ?? 0 }}/2)
          </button>
        </div>

        <MoversPanel
          :movers="store.movers"
          :movers-state="store.moversState"
          :collapsed="moversCollapsed"
          :class="[
            sidebarTab === SidebarTab.Movers ? 'flex' : 'hidden lg:flex',
            moversCollapsed ? 'lg:flex-none lg:shrink-0' : 'lg:min-h-0 lg:flex-1',
          ]"
          @refresh="store.refreshMovers()"
          @select-coin="handleSelectCoin"
          @toggle-collapse="moversCollapsed = !moversCollapsed"
        />

        <RiskPanel
          :risk="store.risk"
          :trades="store.trades"
          :prefill="riskPrefill"
          :collapsed="riskCollapsed"
          :class="[
            sidebarTab === SidebarTab.Risk ? 'flex' : 'hidden lg:flex',
            riskCollapsed ? 'lg:flex-none lg:shrink-0' : 'lg:min-h-0 lg:flex-1',
          ]"
          @open-trade="(payload) => store.logOpenTrade(payload)"
          @close-trade="(payload) => store.logCloseTrade(payload)"
          @clear-trades="store.clearTrades()"
          @toggle-collapse="riskCollapsed = !riskCollapsed"
        />
      </aside>
    </main>
  </div>
</template>
