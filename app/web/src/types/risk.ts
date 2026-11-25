export interface RiskStatus {
  locked: boolean;
  reasons: string[];
  open: string[];
  daily_pct: number;
  streak: number;
  closed_today: number;
}

export interface TradeRecord {
  coin: string;
  type: string;
  opened: string;
  entry: number;
  stop: number;
  target?: number | null;
  risk_pct: number;
  closed: string | null;
  r: number | null;
  fill_price?: number;
}
