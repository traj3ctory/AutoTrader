export type IMaybe<T> = T | null | undefined;
export type INullable<T> = T | null;

export interface RiskPrefillPayload {
  coin: string;
  type: string;
  entry: number;
  stop: number;
  target?: INullable<number>;
}

export interface OpenTradePayload {
  coin: string;
  type: string;
  entry: number;
  stop: number;
  target?: INullable<number>;
  risk_pct?: number;
}

export interface CloseTradePayload {
  coin: string;
  r: number;
  fill_price?: number;
}
