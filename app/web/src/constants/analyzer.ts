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
  moverTab: "autotrader_mover_tab",
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
export const ZONE_FILL_DEMAND = "rgba(34, 197, 94, 0.14)";
export const ZONE_FILL_SUPPLY = "rgba(239, 68, 68, 0.14)";
export const ZONE_FILL_USED_DEMAND = "rgba(34, 197, 94, 0.06)";
export const ZONE_FILL_USED_SUPPLY = "rgba(239, 68, 68, 0.06)";
export const MIN_ZONE_BAND_PX = 3;

// "base" names a box that no lower-timeframe zone narrowed; "refined" one that was.
export const ZONE_TF_LABELS: Record<string, { base: string; refined: string }> = {
  "60->15": { base: "1H", refined: "1H - 15min" },
  "240->60": { base: "4H", refined: "4H - 1H" },
};

export const INITIAL_VISIBLE_BARS = 200;
export const ORIGIN_PADDING_BARS = 10;
export const ZONE_LABEL_MIN_GAP_PX = 16;
