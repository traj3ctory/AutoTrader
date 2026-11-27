import { BADGE_ZONE_LABEL, ZONE_TF_LABELS } from "../constants/analyzer";
import type { ZoneInfo } from "../types/analyzer";
import type { ChartZone } from "../types/chart";

function toChartZone(zone: ZoneInfo): ChartZone {
  const tfNames = ZONE_TF_LABELS[zone.tf ?? ""];
  return {
    kind: zone.kind,
    low: zone.low,
    high: zone.high,
    consumed: Boolean(zone.consumed),
    isTarget: Boolean(zone.isTarget),
    timeSec: zone.timeSec,
    tfLabels: [(zone.refined ? tfNames?.refined : tfNames?.base) ?? zone.tf ?? ""],
  };
}

function combine({ into, next }: { into: ChartZone; next: ChartZone }): ChartZone {
  const bothTimed = into.timeSec !== undefined && next.timeSec !== undefined;
  return {
    kind: into.kind,
    low: Math.min(into.low, next.low),
    high: Math.max(into.high, next.high),
    consumed: into.consumed && next.consumed,
    isTarget: into.isTarget || next.isTarget,
    timeSec: bothTimed ? Math.min(into.timeSec as number, next.timeSec as number) : undefined,
    // The badge name goes last so it never splits the engine's timeframe names.
    tfLabels: [...new Set([...into.tfLabels, ...next.tfLabels])].sort(
      (a, b) => Number(a === BADGE_ZONE_LABEL) - Number(b === BADGE_ZONE_LABEL)
    ),
  };
}

/**
 * @function mergeZones
 * @description Draws overlapping zones of one side as a single band; the engine's zones stay unchanged.
 */
export function mergeZones({ zones }: { zones: ZoneInfo[] }): ChartZone[] {
  const sorted = zones.map(toChartZone).sort((a, b) => a.kind.localeCompare(b.kind) || a.low - b.low);
  return sorted.reduce<ChartZone[]>((merged, next) => {
    const last = merged[merged.length - 1];
    if (last && last.kind === next.kind && next.low <= last.high) {
      return [...merged.slice(0, -1), combine({ into: last, next })];
    }
    return [...merged, next];
  }, []);
}
