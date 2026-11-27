import type { INullable } from "./common";
import type { RiskMode } from "./enums";

export interface SizerPlan {
  mode: RiskMode;
  entry: number;
  stop: number;
  target: INullable<number>;
}
