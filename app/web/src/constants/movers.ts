import { MoverTab } from "../types/enums";

export const MOVER_TABS = [
  { value: MoverTab.Watchlist, label: "Watchlist", hint: "Ledger coins and the synced TradingView picks" },
  { value: MoverTab.Losers, label: "Losers", hint: "Biggest 24h falls" },
  { value: MoverTab.Gainers, label: "Gainers", hint: "Biggest 24h rises" },
  { value: MoverTab.Range, label: "Range", hint: "Wide 24h swing that ended near where it started" },
];
