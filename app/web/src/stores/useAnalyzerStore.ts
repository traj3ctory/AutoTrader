import { computed, ref, watch } from "vue";
import { defineStore } from "pinia";
import {
  DEFAULT_AUTO_SCAN_MINUTES,
  DEFAULT_BALANCE_USD,
  SCAN_TIMEOUT_MS,
  STORAGE_KEYS,
} from "../constants/analyzer";
import { useCopyFeedback } from "../composables/useCopyFeedback";
import { useRiskActions } from "../composables/useRiskActions";
import { useScanAlerts } from "../composables/useScanAlerts";
import { appRequest } from "../utils/appRequest";
import { readStoredNumber, readStoredString, writeStoredNumber, writeStoredString } from "../utils/storage";
import {
  CopyTarget,
  LoadState,
  type AnalyzeResponse,
  type DashboardResponse,
  type MoversPayload,
  type OverviewResponse,
  type RiskStatus,
  type ScanResponse,
  type SignalHistoryEntry,
  type TradeRecord,
} from "../types/analyzer";
import type { INullable } from "../types/common";

export const useAnalyzerStore = defineStore("analyzer", () => {
  const overviewState = ref<LoadState>(LoadState.Idle);
  const analyzeState = ref<LoadState>(LoadState.Idle);
  const scanState = ref<LoadState>(LoadState.Idle);
  const moversState = ref<LoadState>(LoadState.Idle);
  const dashboardState = ref<LoadState>(LoadState.Idle);
  const errorMessage = ref("");

  const overview = ref<INullable<OverviewResponse>>(null);
  const analysis = ref<INullable<AnalyzeResponse>>(null);
  const scanResult = ref<INullable<ScanResponse>>(null);
  const movers = ref<INullable<MoversPayload>>(null);
  const dashboard = ref<INullable<DashboardResponse>>(null);
  const risk = ref<INullable<RiskStatus>>(null);
  const trades = ref<TradeRecord[]>([]);
  const signalHistory = ref<SignalHistoryEntry[]>([]);

  const selectedSymbol = ref(readStoredString({ key: STORAGE_KEYS.symbol, fallback: "XRPUSDT" }));
  const selectedTf = ref(readStoredString({ key: STORAGE_KEYS.tf, fallback: "15" }));
  const accountBalance = ref(readStoredNumber({ key: STORAGE_KEYS.balance, fallback: DEFAULT_BALANCE_USD }));
  const { copiedTarget, flashCopied, copyToClipboard } = useCopyFeedback();
  const { soundEnabled, toggleSound, alertOnNewTradeable } = useScanAlerts();
  const autoScanMinutes = ref(DEFAULT_AUTO_SCAN_MINUTES);

  watch(accountBalance, (value) => writeStoredNumber({ key: STORAGE_KEYS.balance, value }));

  const ledgerSymbols = computed(() => {
    const setups = overview.value?.setups || {};
    return Object.keys(setups).map((key) => key.replace(".P", ""));
  });

  const tvSymbols = computed(() => {
    const core = new Set(ledgerSymbols.value);
    return (overview.value?.tvWatchlist || [])
      .map((key) => key.replace(".P", ""))
      .filter((sym) => !core.has(sym));
  });

  async function loadOverview() {
    overviewState.value = LoadState.Loading;
    errorMessage.value = "";
    try {
      const data = await appRequest<OverviewResponse>({ url: "/overview" });
      overview.value = data;
      movers.value = data.movers;
      risk.value = data.risk;
      trades.value = data.trades;
      signalHistory.value = data.signalHistory || [];
      overviewState.value = LoadState.Ready;
    } catch (err) {
      overviewState.value = LoadState.Error;
      errorMessage.value = err instanceof Error ? err.message : "Failed to load overview";
    }
  }

  async function analyzeCoin({ symbol, tf }: { symbol?: string; tf?: string } = {}) {
    const nextSym = (symbol || selectedSymbol.value).toUpperCase().replace(".P", "");
    const nextTf = tf || selectedTf.value;
    selectedSymbol.value = nextSym;
    selectedTf.value = nextTf;
    writeStoredString({ key: STORAGE_KEYS.symbol, value: nextSym });
    writeStoredString({ key: STORAGE_KEYS.tf, value: nextTf });
    analyzeState.value = LoadState.Loading;
    errorMessage.value = "";
    try {
      const data = await appRequest<AnalyzeResponse>({
        url: "/analyze",
        params: { symbol: nextSym, tf: nextTf },
        timeout: SCAN_TIMEOUT_MS,
      });
      analysis.value = data;
      risk.value = data.risk;
      analyzeState.value = LoadState.Ready;
    } catch (err) {
      analyzeState.value = LoadState.Error;
      errorMessage.value = err instanceof Error ? err.message : "Analysis failed";
    }
  }

  async function runScan({ extraSymbols = "" }: { extraSymbols?: string } = {}) {
    scanState.value = LoadState.Loading;
    errorMessage.value = "";
    try {
      const data = await appRequest<ScanResponse>({
        url: "/scan",
        params: extraSymbols ? { symbols: extraSymbols } : undefined,
        timeout: SCAN_TIMEOUT_MS,
      });
      alertOnNewTradeable({ scan: data, coreSymbols: ledgerSymbols.value });
      scanResult.value = data;
      risk.value = data.risk;
      if (data.signalHistory) {
        signalHistory.value = data.signalHistory;
      }
      if (data.tvWatchlist && overview.value) {
        overview.value = { ...overview.value, tvWatchlist: data.tvWatchlist };
      }
      scanState.value = LoadState.Ready;
    } catch (err) {
      scanState.value = LoadState.Error;
      errorMessage.value = err instanceof Error ? err.message : "Scan failed";
    }
  }

  async function refreshMovers() {
    moversState.value = LoadState.Loading;
    errorMessage.value = "";
    try {
      const data = await appRequest<MoversPayload>({
        url: "/movers",
        params: { refresh: 1 },
        timeout: SCAN_TIMEOUT_MS,
      });
      movers.value = data;
      if (data.tvWatchlist && overview.value) {
        overview.value = { ...overview.value, tvWatchlist: data.tvWatchlist };
      }
      moversState.value = LoadState.Ready;
      if (data.tvWatchlist && scanState.value !== LoadState.Loading) {
        void runScan();
      }
    } catch (err) {
      moversState.value = LoadState.Error;
      errorMessage.value = err instanceof Error ? err.message : "Mover refresh failed";
    }
  }

  async function copyCurrentPine({ rebuild = false }: { rebuild?: boolean } = {}) {
    try {
      const data = await appRequest<{ pine: string }>({
        url: "/pine",
        params: { rebuild: rebuild ? 1 : 0 },
      });
      await copyToClipboard({ text: data.pine, target: CopyTarget.Pine });
    } catch (err) {
      errorMessage.value = err instanceof Error ? err.message : "Failed to copy Pine";
    }
  }

  async function copySetup({ text, target = CopyTarget.Setup }: { text: string; target?: CopyTarget }) {
    try {
      await copyToClipboard({ text, target });
    } catch (err) {
      errorMessage.value = err instanceof Error ? err.message : "Clipboard write failed";
    }
  }

  async function loadDashboard() {
    dashboardState.value = LoadState.Loading;
    errorMessage.value = "";
    try {
      dashboard.value = await appRequest<DashboardResponse>({ url: "/dashboard" });
      dashboardState.value = LoadState.Ready;
    } catch (err) {
      dashboardState.value = LoadState.Error;
      errorMessage.value = err instanceof Error ? err.message : "Failed to load dashboard";
    }
  }

  const { logOpenTrade, logCloseTrade, clearTrades } = useRiskActions({ risk, trades });

  async function syncToLedger({ symbol }: { symbol: string }) {
    errorMessage.value = "";
    try {
      await appRequest<{ ok: boolean; ticker: string; ledgerUpdated: string }>({
        url: "/ledger/sync",
        method: "POST",
        data: { symbol },
        timeout: SCAN_TIMEOUT_MS,
      });
      flashCopied(CopyTarget.Ledger);
      await loadOverview();
    } catch (err) {
      errorMessage.value = err instanceof Error ? err.message : "Failed to sync ledger";
    }
  }

  return {
    overviewState,
    analyzeState,
    scanState,
    moversState,
    dashboardState,
    errorMessage,
    overview,
    analysis,
    scanResult,
    movers,
    dashboard,
    risk,
    trades,
    signalHistory,
    selectedSymbol,
    selectedTf,
    accountBalance,
    copiedTarget,
    soundEnabled,
    autoScanMinutes,
    ledgerSymbols,
    tvSymbols,
    loadOverview,
    loadDashboard,
    analyzeCoin,
    runScan,
    toggleSound,
    refreshMovers,
    copyCurrentPine,
    copySetup,
    logOpenTrade,
    logCloseTrade,
    clearTrades,
    syncToLedger,
  };
});
