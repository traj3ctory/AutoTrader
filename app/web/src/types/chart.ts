import type { INullable } from "./common";

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
  exitTimeSec?: INullable<number>;
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

export interface ChartZone {
  kind: "demand" | "supply";
  low: number;
  high: number;
  consumed: boolean;
  isTarget: boolean;
  timeSec?: number;
  tfLabels: string[];
}

export interface ZoneBand {
  key: string;
  kind: "demand" | "supply";
  label: string;
  top: number;
  height: number;
  consumed: boolean;
  fill: string;
  left: number;
}
