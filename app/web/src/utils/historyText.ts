import type { SignalHistoryEntry } from "../types/analyzer";
import { SignalOutcome } from "../types/enums";

function rewardRatio({ entry, stop, target }: { entry: number; stop: number; target: number }): string {
  return (Math.abs(target - entry) / Math.abs(entry - stop)).toFixed(2);
}

/**
 * @function historyExitPrice
 * @description The level a closed signal ended on; open and expired signals have none.
 */
export function historyExitPrice({ item }: { item: SignalHistoryEntry }): number | null {
  if (item.outcome === SignalOutcome.Win) return item.target ?? null;
  if (item.outcome === SignalOutcome.Loss) return item.stop ?? null;
  return null;
}

function historyResult({ item }: { item: SignalHistoryEntry }): string {
  if (item.outcome === SignalOutcome.Win) return `Target hit at ${item.target}.`;
  if (item.outcome === SignalOutcome.Loss) return `Stop hit at ${item.stop}.`;
  if (item.outcome === SignalOutcome.BreakEven) return "Closed at breakeven.";
  if (item.outcome === SignalOutcome.Expired) {
    return item.closedAtUtc ? "Never filled: the stop traded first." : "Closed by the earlier rule with no exit recorded.";
  }
  if (item.status === "STALE_ORDER") return "Limit not filled yet; entry window passed.";
  if (item.status === "ENGINE_IN_TRADE") return "Filled, still open: no stop or target hit yet. Too late to enter.";
  return "Open.";
}

/**
 * @function historySummary
 * @description Card text built from the stored levels and current result, not the old scan sentence.
 */
export function historySummary({ item }: { item: SignalHistoryEntry }): string {
  const { direction, entry, stop, target } = item;
  if (!direction || entry === undefined || stop === undefined || target === undefined) return item.summary;
  const levels = `${direction.toUpperCase()} · entry ${entry} · SL ${stop} · TP ${target} · R:R ${rewardRatio({ entry, stop, target })}`;
  return `${levels}. ${historyResult({ item })}`;
}
