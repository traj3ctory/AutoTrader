import { ref } from "vue";
import type { ScanResponse } from "../types/analyzer";
import { takeNewTradeable } from "../utils/scanAlerts";
import { playTradeAlert, requestNotificationPermission, sendDesktopNotification } from "../utils/soundAlert";

export function useScanAlerts() {
  const soundEnabled = ref(true);
  const seenKeys = new Set<string>();

  function toggleSound() {
    soundEnabled.value = !soundEnabled.value;
    if (soundEnabled.value) {
      playTradeAlert();
      requestNotificationPermission();
    }
  }

  function alertOnNewTradeable({ scan, coreSymbols }: { scan: ScanResponse; coreSymbols: string[] }) {
    const core = new Set(coreSymbols);
    const fresh = takeNewTradeable({ items: scan.tradeable, seenKeys }).filter((item) => core.has(item.symbol) && !item.watchOnly && !item.lowerTier);
    if (scan.risk.locked || fresh.length === 0 || !soundEnabled.value) return;
    playTradeAlert();
    sendDesktopNotification({ title: `AutoTrader: ${fresh[0].symbol} · ${fresh[0].mode}`, body: fresh[0].summary });
  }

  return { soundEnabled, toggleSound, alertOnNewTradeable };
}
