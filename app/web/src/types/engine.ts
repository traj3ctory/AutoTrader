import { RiskStatus } from "./risk";

export interface ZoneInfo {
  kind: "demand" | "supply";
  low: number;
  high: number;
  proximal: number;
  distal: number;
  hasFvg: boolean;
  touchIndex: number | null;
  tf?: string;
  refined?: boolean;
  consumed?: boolean;
  isTarget?: boolean;
  timeSec?: number;
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

export interface TargetLevel {
  label: string;
  price: number;
  rr: number;
  source: string;
  note: string;
}

export interface ScalpPosition {
  direction: "long" | "short";
  entry: number;
  stop: number;
  activeStop: number;
  target: number;
  targets?: TargetLevel[];
  rr: number;
  ageCandles: number;
  unrealR: number;
  closedAtUtc: string;
  entryTimeSec: number;
}

export interface IntradayPending {
  direction: "long" | "short";
  confirmation: string;
  signalAtUtc: string;
  entry: number;
  stop: number;
  target: number;
  targets?: TargetLevel[];
  rr: number;
  ageCandles: number;
  gapPct: number;
  entryTimeSec: number;
}

export interface IntradayPosition {
  direction: "long" | "short";
  entry: number;
  stop: number;
  target: number;
  targets?: TargetLevel[];
  rr: number;
  ageCandles?: number;
  unrealR: number;
  entryAtUtc: string;
  signalAtUtc: string;
  entryTimeSec: number;
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

export interface Zone4hBadge {
  label: string;
  side: "supply" | "demand";
  distPct: number;
  zone: ZoneInfo | null;
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
  zone4hBadge?: Zone4hBadge | null;
  nearZones: Record<"scalp" | "intraday", { demand: ZoneInfo[]; supply: ZoneInfo[] }>;
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
    contextOnly: boolean;
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
