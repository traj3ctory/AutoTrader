import type { Ref } from "vue";
import type { RiskStatus, TradeRecord } from "../types/analyzer";
import type { CloseTradePayload, OpenTradePayload } from "../types/common";
import { appRequest } from "../utils/appRequest";

interface RiskActionsOptions {
  risk: Ref<RiskStatus | null>;
  trades: Ref<TradeRecord[]>;
}

type RiskReply = { risk: RiskStatus; trades: TradeRecord[] };

export function useRiskActions({ risk, trades }: RiskActionsOptions) {
  async function post({ url, data }: { url: string; data: object }) {
    const res = await appRequest<RiskReply>({ url, method: "POST", data });
    risk.value = res.risk;
    trades.value = res.trades;
  }

  return {
    logOpenTrade: (payload: OpenTradePayload) => post({ url: "/risk/open", data: payload }),
    logCloseTrade: (payload: CloseTradePayload) => post({ url: "/risk/close", data: payload }),
    clearTrades: () => post({ url: "/risk/clear", data: {} }),
  };
}
