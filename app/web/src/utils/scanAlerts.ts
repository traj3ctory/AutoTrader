import type { ScanTradeableItem } from "../types/analyzer";

/** Returns items not seen in the previous scan and replaces the seen set with the current keys. */
export function takeNewTradeable({ items, seenKeys }: { items: ScanTradeableItem[]; seenKeys: Set<string> }): ScanTradeableItem[] {
  const nextKeys = new Set(items.map((item) => `${item.symbol}:${item.mode}`));
  const fresh = items.filter((item) => !seenKeys.has(`${item.symbol}:${item.mode}`));
  seenKeys.clear();
  nextKeys.forEach((key) => seenKeys.add(key));
  return fresh;
}
