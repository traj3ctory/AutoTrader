export interface TimeframeOption {
  value: string;
  label: string;
}

export interface ActiveBoxSpec {
  label: string;
  direction: "long" | "short";
  entry: number;
  stop: number;
  target: number;
  rr: number;
  entryTimeSec: number;
}

export interface PositionBoxCoords extends ActiveBoxSpec {
  rewardTop: number;
  rewardHeight: number;
  riskTop: number;
  riskHeight: number;
  entryTop: number;
  left: number;
  width: number;
}
