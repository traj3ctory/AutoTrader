export const enum LoadState {
  Idle = 0,
  Loading = 1,
  Ready = 2,
  Error = 3,
}

export const enum CopyTarget {
  None = 0,
  Setup = 1,
  Pine = 2,
  Tradeable = 3,
  Ledger = 4,
}

export const enum SidebarTab {
  Movers = 0,
  Risk = 1,
}

export const enum AppView {
  Analyzer = 0,
  Dashboard = 1,
}
