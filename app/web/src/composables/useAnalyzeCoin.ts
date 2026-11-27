import { ref, type Ref } from "vue";
import { SCAN_TIMEOUT_MS } from "../constants/analyzer";
import { appRequest } from "../utils/appRequest";
import { LoadState, type AnalyzeResponse, type RiskStatus } from "../types/analyzer";
import type { INullable } from "../types/common";

export function useAnalyzeCoin({ risk, errorMessage }: { risk: Ref<INullable<RiskStatus>>; errorMessage: Ref<string> }) {
  const analyzeState = ref<LoadState>(LoadState.Idle);
  const analysis = ref<INullable<AnalyzeResponse>>(null);
  let latestRequestId = 0;

  /**
   * @function fetchAnalysis
   * @description Applies only the newest request, so slow older replies are dropped.
   */
  async function fetchAnalysis({ symbol, tf }: { symbol: string; tf: string }) {
    const requestId = ++latestRequestId;
    analyzeState.value = LoadState.Loading;
    errorMessage.value = "";
    try {
      const data = await appRequest<AnalyzeResponse>({
        url: "/analyze",
        params: { symbol, tf },
        timeout: SCAN_TIMEOUT_MS,
      });
      if (requestId !== latestRequestId) return;
      analysis.value = data;
      risk.value = data.risk;
      analyzeState.value = LoadState.Ready;
    } catch (err) {
      if (requestId !== latestRequestId) return;
      analyzeState.value = LoadState.Error;
      errorMessage.value = err instanceof Error ? err.message : "Analysis failed";
    }
  }

  return { analyzeState, analysis, fetchAnalysis };
}
