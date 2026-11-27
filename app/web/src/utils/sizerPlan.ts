import { TRADEABLE_VERDICTS } from "../constants/analyzer";
import type { AnalyzeResponse } from "../types/analyzer";
import type { INullable } from "../types/common";
import { RiskMode } from "../types/enums";
import type { SizerPlan } from "../types/sizing";

function toPlan({ mode, levels }: { mode: RiskMode; levels: Omit<SizerPlan, "mode"> }): SizerPlan {
  return { mode, entry: levels.entry, stop: levels.stop, target: levels.target };
}

/**
 * @function buildSizerPlan
 * @description Picks the levels to size: tradeable signals first, then engine trades, then a reference zone.
 */
export function buildSizerPlan({ analysis }: { analysis: AnalyzeResponse }): INullable<SizerPlan> {
  const { scalp, intraday, price } = analysis;
  if (scalp.position && TRADEABLE_VERDICTS.includes(scalp.verdictKind)) {
    return toPlan({ mode: RiskMode.Scalp, levels: scalp.position });
  }
  if (intraday.pending) return toPlan({ mode: RiskMode.Intraday, levels: intraday.pending });
  if (scalp.position) return toPlan({ mode: RiskMode.Scalp, levels: scalp.position });
  if (intraday.position) return toPlan({ mode: RiskMode.Intraday, levels: intraday.position });
  const refSide = scalp.short.zone ? scalp.short : scalp.long;
  return refSide.stop ? { mode: RiskMode.Scalp, entry: price, stop: refSide.stop, target: refSide.target } : null;
}
