import type { SignalHistoryEntry } from "../types/analyzer";

/**
 * @function emaBadgeClass
 * @description Maps EMA alignment badge strings to Tailwind utility classes.
 */
export function emaBadgeClass(badge: string): string {
  if (badge === "SUPPORTING" || badge === "BULL") {
    return "bg-accent-bull/20 text-accent-bull";
  }
  if (badge === "COUNTER" || badge === "BEAR") {
    return "bg-accent-bear/20 text-accent-bear";
  }
  return "bg-surface-panel text-ink-secondary";
}

/**
 * @function statusLabel
 * @description Formats signal verdict status codes for alert badges.
 */
export function statusLabel(status?: string): string {
  if (status === "LATE_ENTRY") return "LATE";
  if (status === "ENGINE_IN_TRADE") return "IN TRADE";
  return "VALID";
}

/**
 * @function statusBadgeClass
 * @description Maps live signal status codes to semantic Tailwind badge classes.
 */
export function statusBadgeClass(status?: string): string {
  if (status === "ENGINE_IN_TRADE") return "bg-accent-brand/20 text-accent-brand";
  if (status === "LATE_ENTRY") return "bg-accent-warn/20 text-accent-warn";
  return "bg-accent-bull/20 text-accent-bull";
}

/**
 * @function historyOutcomeLabel
 * @description Builds a readable outcome label for persisted signal history rows.
 */
export function historyOutcomeLabel(item: SignalHistoryEntry): string {
  if (item.outcome === "WIN") return `WIN${item.netR != null ? ` ${item.netR >= 0 ? "+" : ""}${item.netR}R` : ""}`;
  if (item.outcome === "LOSS") return `LOSS${item.netR != null ? ` ${item.netR}R` : ""}`;
  if (item.outcome === "BE") return "BE 0R";
  if (item.outcome === "EXPIRED") return "EXPIRED";
  if (item.status === "ENGINE_IN_TRADE") return "PAST ENTRY WINDOW";
  return statusLabel(item.status);
}

/**
 * @function historyOutcomeClass
 * @description Maps persisted signal history outcomes to Tailwind badge classes.
 */
export function historyOutcomeClass(item: SignalHistoryEntry): string {
  if (item.outcome === "WIN") return "bg-accent-bull/20 text-accent-bull";
  if (item.outcome === "LOSS") return "bg-accent-bear/20 text-accent-bear";
  if (item.outcome === "BE" || item.outcome === "EXPIRED" || item.status === "ENGINE_IN_TRADE") {
    return "bg-surface-panel text-ink-muted";
  }
  return statusBadgeClass(item.status);
}

export function trendLabel({ trend }: { trend: string }): string {
  return trend === "counter" ? "COUNTER-TREND" : trend === "with" ? "WITH 4H TREND" : "4H RANGE";
}

export function trendBadgeClass({ trend }: { trend: string }): string {
  return trend === "counter"
    ? "bg-accent-bear/20 text-accent-bear"
    : trend === "with"
      ? "bg-accent-bull/20 text-accent-bull"
      : "bg-surface-elevated text-ink-secondary";
}

export function btcEthBadgeClass({ btcEth }: { btcEth: string }): string {
  return btcEth === "ALIGNED"
    ? "bg-accent-bull/20 text-accent-bull"
    : btcEth === "CONFLICTING"
      ? "bg-accent-bear/20 text-accent-bear"
      : "bg-surface-elevated text-ink-secondary";
}
