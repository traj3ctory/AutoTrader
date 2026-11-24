export const enum LoadState {
  Idle = 0,
  Loading = 1,
  Ready = 2,
  Error = 3,
}

export const enum CopyTarget {
  None = 0,
  Setup = 1,
  Pine = 2,
  Tradeable = 3,
}

export const enum SidebarTab {
  Movers = 0,
  Risk = 1,
}

export const enum AppView {
  Analyzer = 0,
  Dashboard = 1,
}

export interface ScorecardRecord {
  id: string;
  date: string;
  coin: string;
  trade_type: string;
  direction: string;
  outcome: string;
  trade_taken: boolean;
  trade_result: string;
  review_note: string;
}

export interface JournalEntry {
  coin: string;
  date: string;
  setup_type: string;
  result: string;
  mistake_tag: string;
  note: string;
}

export interface DashboardResponse {
  scorecard: {
    last_updated: string | null;
    summary: Record<string, number>;
    records: ScorecardRecord[];
  };
  journal: JournalEntry[];
  trades: TradeRecord[];
  risk: RiskStatus;
  signalHistory?: SignalHistoryEntry[];
  backtests: {
    oos: string;
    edgeDecay: string;
  };
}

export interface ZoneInfo {
  kind: "demand" | "supply";
  low: number;
  high: number;
  proximal: number;
  distal: number;
  hasFvg: boolean;
  touchIndex: number | null;
}

export interface ScalpSideInfo {
  blockedBy: string[];
  status: string;
  zone: ZoneInfo | null;
  stop: number | null;
  target: number | null;
  rr: number | null;
}

export interface IntradaySideInfo {
  blockedBy: string[];
  status: string;
  nearestZone: ZoneInfo | null;
}

export interface EngineReplay {
  days: number;
  closed: number;
  wins: number;
  totalR: number;
  summary: string;
}

export interface ScalpPosition {
  direction: "long" | "short";
  entry: number;
  stop: number;
  activeStop: number;
  target: number;
  rr: number;
  ageCandles: number;
  unrealR: number;
  closedAtUtc: string;
}

export interface IntradayPending {
  direction: "long" | "short";
  confirmation: string;
  entry: number;
  stop: number;
  target: number;
  rr: number;
  ageCandles: number;
  gapPct: number;
}

export interface IntradayPosition {
  direction: "long" | "short";
  entry: number;
  stop: number;
  target: number;
  rr: number;
  unrealR: number;
  entryAtUtc: string;
}

export interface CandlePoint {
  time: number;
  open: number;
  high: number;
  low: number;
  close: number;
  ema9: number | null;
  ema20: number | null;
}

export interface AnalyzeResponse {
  symbol: string;
  ticker: string;
  tf: string;
  price: number;
  historyDays: number;
  lastClosed5mUtc: string;
  lastClosed15mUtc: string;
  structure4h: string;
  structure1d: string;
  atr4hPct: number | null;
  vwap: number;
  emaOrder: string;
  emaSlope: string;
  lastCross: {
    direction: string | null;
    closedAtUtc: string | null;
    candlesAgo: number | null;
    summary: string;
  };
  scalpZone: {
    verdictKind: string;
    verdictText: string;
    tradeable: boolean;
    emaBadge: string;
    position: ScalpPosition | null;
    long: ScalpSideInfo;
    short: ScalpSideInfo;
    replay: EngineReplay;
  };
  scalp: {
    verdictKind: string;
    verdictText: string;
    tradeable: boolean;
    position: ScalpPosition | null;
    long: ScalpSideInfo;
    short: ScalpSideInfo;
    replay: EngineReplay;
  };
  intraday: {
    verdictKind: string;
    verdictText: string;
    tradeable: boolean;
    position: IntradayPosition | null;
    pending: IntradayPending | null;
    long: IntradaySideInfo;
    short: IntradaySideInfo;
    replay: EngineReplay;
  };
  candles: CandlePoint[];
  copyText: string;
  risk: RiskStatus;
}

export interface RiskStatus {
  locked: boolean;
  reasons: string[];
  open: string[];
  daily_pct: number;
  streak: number;
  closed_today: number;
}

export interface TradeRecord {
  coin: string;
  type: string;
  opened: string;
  entry: number;
  stop: number;
  risk_pct: number;
  closed: string | null;
  r: number | null;
  fill_price?: number;
}

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

export interface MoversPayload {
  updatedAt: string | null;
  gainers: MoverRow[];
  losers: MoverRow[];
  rangeMovers: MoverRow[];
  raw: string;
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
  emaBadge?: string;
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
  mode: string;
  emaBadge?: string;
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
