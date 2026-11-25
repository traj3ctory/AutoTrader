import type { TimeframeOption } from "../types/chart";

export const SCAN_TIMEOUT_MS = 180_000;
export const COPY_RESET_MS = 2_000;
export const DEFAULT_BALANCE_USD = 1000;
export const DEFAULT_AUTO_SCAN_MINUTES = 5;

export const MAX_SCALP_AGE_CANDLES = 72;
export const SAFE_LEVERAGE_FACTOR = 80;
export const TIGHT_STOP_PCT = 1;

export const RISK_PCT_BY_MODE: Record<"scalp" | "intraday", number> = {
  scalp: 0.5,
  intraday: 1.0,
};

export const STORAGE_KEYS = {
  symbol: "autotrader_selected_symbol",
  tf: "autotrader_selected_tf",
  balance: "autotrader_account_balance",
} as const;

export const TIMEFRAMES: TimeframeOption[] = [
  { value: "5", label: "5m" },
  { value: "15", label: "15m" },
  { value: "60", label: "1H" },
  { value: "240", label: "4H" },
];

export const AUTOMATION_GATE_GOAL = 30;
export const BOX_FUTURE_WIDTH_PX = 120;
export const BOX_GAP_PX = 8;
export const CHART_RIGHT_OFFSET_BARS = 24;
