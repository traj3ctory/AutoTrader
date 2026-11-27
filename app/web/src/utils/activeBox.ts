import { BADGE_ZONE_TF, MAX_SCALP_AGE_CANDLES } from "../constants/analyzer";
import type { AnalyzeResponse, ZoneInfo } from "../types/analyzer";
import type { ActiveBoxSpec } from "../types/chart";
import type { INullable } from "../types/common";

/**
 * @function pickActiveBox
 * @description Selects the primary fresh setup box in priority order (Scalp EMA -> Intraday Limit); Scalp Zone is context only.
 */
export function pickActiveBox({ analysis }: { analysis: AnalyzeResponse }): INullable<ActiveBoxSpec> {
  const { scalp, intraday } = analysis;
  const scalpFresh =
    scalp.verdictKind === "VALID" ||
    scalp.verdictKind === "LATE_ENTRY" ||
    (scalp.verdictKind === "ENGINE_IN_TRADE" && (scalp.position?.ageCandles ?? 0) <= MAX_SCALP_AGE_CANDLES);

  if (scalp.position && scalpFresh) {
    return { label: "Scalp", ...scalp.position };
  }
  if (intraday.pending && intraday.verdictKind === "VALID") {
    return { label: "Limit", ...intraday.pending };
  }
  return null;
}

function pickBadgeZones({ badge }: { badge: AnalyzeResponse["zone4hBadge"] }): ZoneInfo[] {
  const sides = badge?.sides ? Object.values(badge.sides) : badge ? [badge] : [];
  return sides.flatMap((side) => (side.zone ? [{ ...side.zone, tf: BADGE_ZONE_TF }] : []));
}

/**
 * @function pickChartZones
 * @description Zones of the engine behind the active box (or both), plus the zone behind the 4H badge.
 */
export function pickChartZones({ analysis, box }: { analysis: AnalyzeResponse; box: INullable<ActiveBoxSpec> }): ZoneInfo[] {
  const { scalp, intraday } = analysis.nearZones;
  const sets = box?.label === "Limit" ? [intraday] : box ? [scalp] : [scalp, intraday];
  const engineZones = sets.flatMap((set) => [...set.supply, ...set.demand]).filter((zone) => zone.isTarget || !zone.consumed);
  return [...engineZones, ...pickBadgeZones({ badge: analysis.zone4hBadge })];
}
