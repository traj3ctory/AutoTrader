import type { Zone4hBadge } from "./engine";
import type { RiskStatus, TradeRecord } from "./risk";

export interface MoverRow {
  ticker: string;
  symbol: string;
  pct: number;
  turnoverM: number;
  price: number;
  inLedger: boolean;
  rangePct?: number;
  high?: string;
  low?: string;
}

export type CoinQuote = Pick<MoverRow, "symbol"> & Partial<MoverRow>;

export interface WatchlistResponse {
  rows: MoverRow[];
}

export interface MoverScheduleInfo {
  times: string[];
  tzOffsetHours: number;
}

export interface MoversPayload {
  updatedAt: string | null;
  gainers: MoverRow[];
  losers: MoverRow[];
  rangeMovers: MoverRow[];
  raw: string;
  tvWatchlist?: string[];
  schedule?: MoverScheduleInfo;
}

export interface LedgerSetup {
  coin: string;
  trade_type: string;
  setup_state: string;
  position_status: string;
  analyzed_at: string;
  watch_zone?: {
    low: number | null;
    high: number | null;
    label?: string;
  };
}

export interface SignalHistoryEntry {
  id: string;
  seenAtUtc: string;
  symbol: string;
  mode: string;
  status?: string;
  outcome?: string | null;
  netR?: number | null;
  closedAtUtc?: string | null;
  emaBadge?: string;
  zone4hBadge?: Zone4hBadge | null;
  summary: string;
  copyText: string;
}

export interface OverviewResponse {
  ledgerUpdated: string | null;
  contextWatch: Record<string, {
    coin: string;
    key_resistance?: { low: number; high: number };
    key_support?: { low: number; high: number };
    analyzed_at?: string;
  }>;
  setups: Record<string, LedgerSetup>;
  tvWatchlist?: string[];
  signalHistory?: SignalHistoryEntry[];
  risk: RiskStatus;
  riskLine: string;
  trades: TradeRecord[];
  scorecardSummary: Record<string, number>;
  movers: MoversPayload;
}

export interface ScanTradeableItem {
  symbol: string;
  watchOnly?: boolean;
  watchReasons?: string[];
  trend: "with" | "range" | "counter";
  lowerTier: boolean;
  btcEth: string | null;
  mode: string;
  status?: string;
  emaBadge?: string;
  zone4hBadge?: Zone4hBadge | null;
  summary: string;
  copyText: string;
}

export interface ScanCheckedItem {
  symbol: string;
  ticker: string;
  price: number;
  structure4h: string;
  structure1d: string;
  scalpKind: string;
  intradayKind: string;
  tradeable: boolean;
  copyText: string;
}

export interface ScanResponse {
  scannedAtUtc: string;
  tradeable: ScanTradeableItem[];
  checked: ScanCheckedItem[];
  failed: Array<{ symbol: string; error: string }>;
  tvWatchlist?: string[];
  signalHistory?: SignalHistoryEntry[];
  risk: RiskStatus;
}
