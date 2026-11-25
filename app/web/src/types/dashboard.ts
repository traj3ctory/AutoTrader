import type { SignalHistoryEntry } from "./market";
import type { RiskStatus, TradeRecord } from "./risk";

export interface ScorecardRecord {
  id: string;
  date: string;
  coin: string;
  trade_type: string;
  direction: string;
  outcome: string;
  trade_taken: boolean;
  trade_result: string;
  review_note: string;
}

export interface JournalEntry {
  coin: string;
  date: string;
  setup_type: string;
  result: string;
  mistake_tag: string;
  note: string;
}

export interface DashboardResponse {
  scorecard: {
    last_updated: string | null;
    summary: Record<string, number>;
    records: ScorecardRecord[];
  };
  journal: JournalEntry[];
  trades: TradeRecord[];
  risk: RiskStatus;
  signalHistory?: SignalHistoryEntry[];
  backtests: {
    oos: string;
    edgeDecay: string;
  };
}
