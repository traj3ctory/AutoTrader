import { computed, ref, watch } from "vue";
import { defineStore } from "pinia";
import { appRequest } from "../utils/appRequest";
import { playTradeAlert } from "../utils/soundAlert";
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

const SCAN_TIMEOUT_MS = 90_000;
const COPY_RESET_MS = 2_000;

export const useAnalyzerStore = defineStore("analyzer", () => {
  const overviewState = ref<LoadState>(LoadState.Idle);
  const analyzeState = ref<LoadState>(LoadState.Idle);
  const scanState = ref<LoadState>(LoadState.Idle);
  const moversState = ref<LoadState>(LoadState.Idle);
  const dashboardState = ref<LoadState>(LoadState.Idle);
  const errorMessage = ref("");

  const overview = ref<OverviewResponse | null>(null);
  const analysis = ref<AnalyzeResponse | null>(null);
  const scanResult = ref<ScanResponse | null>(null);
  const movers = ref<MoversPayload | null>(null);
  const dashboard = ref<DashboardResponse | null>(null);
  const risk = ref<RiskStatus | null>(null);
  const trades = ref<TradeRecord[]>([]);
  const signalHistory = ref<SignalHistoryEntry[]>([]);

  const STORAGE_KEYS = {
    symbol: "autotrader_selected_symbol",
    tf: "autotrader_selected_tf",
    balance: "autotrader_account_balance",
  };

  function readStoredString({ key, fallback }: { key: string; fallback: string }): string {
    try {
      return window.localStorage.getItem(key) || fallback;
    } catch {
      return fallback;
    }
  }

  function readStoredNumber({ key, fallback }: { key: string; fallback: number }): number {
    try {
      const raw = Number(window.localStorage.getItem(key));
      return Number.isFinite(raw) && raw > 0 ? raw : fallback;
    } catch {
      return fallback;
    }
  }

  const selectedSymbol = ref(readStoredString({ key: STORAGE_KEYS.symbol, fallback: "XRPUSDT" }));
  const selectedTf = ref(readStoredString({ key: STORAGE_KEYS.tf, fallback: "15" }));
  const accountBalance = ref(readStoredNumber({ key: STORAGE_KEYS.balance, fallback: 1000 }));
  const copiedTarget = ref<CopyTarget>(CopyTarget.None);
  const soundEnabled = ref(true);
  const autoScanMinutes = ref(5);
  const seenTradeableKeys = new Set<string>();

  watch(accountBalance, (val) => {
    try {
      if (Number.isFinite(val) && val >= 0) {
        window.localStorage.setItem(STORAGE_KEYS.balance, String(val));
      }
    } catch {
      // ignore storage errors
    }
  });

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

  async function copyToClipboard({ text, target }: { text: string; target: CopyTarget }) {
    if (!text) return;
    await navigator.clipboard.writeText(text);
    copiedTarget.value = target;
    window.setTimeout(() => {
      if (copiedTarget.value === target) {
        copiedTarget.value = CopyTarget.None;
      }
    }, COPY_RESET_MS);
  }

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
    try {
      window.localStorage.setItem(STORAGE_KEYS.symbol, nextSym);
      window.localStorage.setItem(STORAGE_KEYS.tf, nextTf);
    } catch {
      // ignore storage errors
    }
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
      let hasNewSignal = false;
      const nextKeys = new Set<string>();
      for (const item of data.tradeable) {
        const key = `${item.symbol}:${item.mode}`;
        nextKeys.add(key);
        if (!seenTradeableKeys.has(key)) {
          hasNewSignal = true;
        }
      }
      seenTradeableKeys.clear();
      for (const key of nextKeys) {
        seenTradeableKeys.add(key);
      }
      if (hasNewSignal && soundEnabled.value) {
        playTradeAlert();
      }
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

  function toggleSound() {
    soundEnabled.value = !soundEnabled.value;
    if (soundEnabled.value) {
      playTradeAlert();
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
      moversState.value = LoadState.Ready;
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

  async function logOpenTrade(payload: {
    coin: string;
    type: string;
    entry: number;
    stop: number;
    risk_pct?: number;
  }) {
    const res = await appRequest<{ risk: RiskStatus; trades: TradeRecord[] }>({
      url: "/risk/open",
      method: "POST",
      data: payload,
    });
    risk.value = res.risk;
    trades.value = res.trades;
  }

  async function logCloseTrade(payload: { coin: string; r: number; fill_price?: number }) {
    const res = await appRequest<{ risk: RiskStatus; trades: TradeRecord[] }>({
      url: "/risk/close",
      method: "POST",
      data: payload,
    });
    risk.value = res.risk;
    trades.value = res.trades;
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
  };
});
