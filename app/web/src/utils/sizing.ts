import { RISK_PCT_BY_MODE, SAFE_LEVERAGE_FACTOR } from "../constants/analyzer";
import type { INullable } from "../types/common";
import type { RiskMode } from "../types/enums";

export interface SizingInput {
  entry: number;
  stop: number;
  balance: number;
  riskMode: RiskMode;
}

export interface SizingResult {
  entry: number;
  stop: number;
  riskPct: number;
  riskUsd: number;
  stopPct: number;
  notionalUsd: number;
  qty: number;
  maxSafeLev: number;
}

/**
 * @function calculatePositionSize
 * @description Computes position sizing, notional value, and safe isolated leverage ceiling.
 */
export function calculatePositionSize({
  entry,
  stop,
  balance,
  riskMode,
}: SizingInput): INullable<SizingResult> {
  if (!entry || !stop || entry === stop || balance <= 0) {
    return null;
  }
  const riskPct = RISK_PCT_BY_MODE[riskMode];
  const riskUsd = balance * (riskPct / 100);
  const stopRatio = Math.abs(entry - stop) / entry;
  const notionalUsd = riskUsd / stopRatio;
  const qty = notionalUsd / entry;
  const stopPct = stopRatio * 100;
  return {
    entry,
    stop,
    riskPct,
    riskUsd,
    stopPct,
    notionalUsd,
    qty,
    maxSafeLev: Math.max(1, Math.floor(SAFE_LEVERAGE_FACTOR / stopPct)),
  };
}
