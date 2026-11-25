import type { TradeRecord } from "../types/analyzer";

/**
 * @function findCorrelatedOpenTrades
 * @description Warns when a new order shares direction with an already open altcoin position.
 */
export function findCorrelatedOpenTrades({
  coin,
  entry,
  stop,
  trades,
}: {
  coin: string;
  entry: number;
  stop: number;
  trades: TradeRecord[];
}): string {
  if (!Number.isFinite(entry) || !Number.isFinite(stop) || entry === stop) {
    return "";
  }
  const formDir = entry > stop ? "long" : "short";
  const formBase = coin.trim().toUpperCase().replace(".P", "").replace(/USDT$/, "");
  const matches = trades.filter((t) => {
    if (t.closed || t.entry === t.stop) return false;
    const tDir = t.entry > t.stop ? "long" : "short";
    const tBase = t.coin.toUpperCase().replace(".P", "").replace(/USDT$/, "");
    return tDir === formDir && tBase !== formBase;
  });
  if (matches.length === 0) return "";
  const names = matches.map((m) => m.coin.replace("USDT.P", "")).join(", ");
  return `Correlated ${formDir.toUpperCase()} exposure: ${names} already open. Consider half size.`;
}
