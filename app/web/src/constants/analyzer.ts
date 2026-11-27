import { RiskMode } from "../types/enums";
import type { TimeframeOption } from "../types/chart";

export const SCAN_TIMEOUT_MS = 180_000;
export const COPY_RESET_MS = 2_000;
export const DEFAULT_BALANCE_USD = 1000;
export const DEFAULT_AUTO_SCAN_MINUTES = 5;

export const MAX_SCALP_AGE_CANDLES = 72;
export const SAFE_LEVERAGE_FACTOR = 80;
export const TIGHT_STOP_PCT = 1;

export const RISK_PCT_BY_MODE: Record<RiskMode, number> = {
  [RiskMode.Scalp]: 0.5,
  [RiskMode.Intraday]: 1.0,
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

/** Marks the zone behind the 4H badge, which is computed separately from the engine zones. */
export const BADGE_ZONE_TF = "badge4h";
export const BADGE_ZONE_LABEL = "4H badge";

// "base" names a box that no lower-timeframe zone narrowed; "refined" one that was.
export const ZONE_TF_LABELS: Record<string, { base: string; refined: string }> = {
  [BADGE_ZONE_TF]: { base: BADGE_ZONE_LABEL, refined: BADGE_ZONE_LABEL },
  "60->15": { base: "1H", refined: "1H - 15min" },
  "240->60": { base: "4H", refined: "4H - 1H" },
};

export const INITIAL_VISIBLE_BARS = 200;
export const ORIGIN_PADDING_BARS = 10;
export const ZONE_LABEL_MIN_GAP_PX = 16;
export const ZONE_LABEL_HEIGHT_PX = 20;

export const PAST_TRADE_PADDING_BARS = 30;
export const PAST_TRADE_MIN_BOX_PX = 130;
// Candles the server sends per timeframe for the chart, and each timeframe's length.
export const CHART_CANDLE_LIMIT = 500;
export const TF_MINUTES: Record<string, number> = { "5": 5, "15": 15, "60": 60, "240": 240 };

export const TRADEABLE_VERDICTS = ["VALID", "LATE_ENTRY"];

export const PRICE_SIG_FIGS = 6;
export const PRICE_MIN_DECIMALS = 4;
