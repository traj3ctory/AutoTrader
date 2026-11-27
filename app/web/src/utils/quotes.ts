const MISSING_VALUE = "—";

export function formatPct(pct?: number): string {
  if (pct === undefined) return MISSING_VALUE;
  return `${pct >= 0 ? "+" : ""}${pct}%`;
}

export function formatRange(rangePct?: number): string {
  return rangePct === undefined ? MISSING_VALUE : `${rangePct}%`;
}

export function formatTurnover(turnoverM?: number): string {
  return turnoverM === undefined ? MISSING_VALUE : `$${turnoverM}M`;
}

export function pctClass(pct?: number): string {
  if (pct === undefined) return "text-ink-muted";
  return pct >= 0 ? "text-accent-bull" : "text-accent-bear";
}
