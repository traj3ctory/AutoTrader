import { ref, watch, type Ref } from "vue";
import { appRequest } from "../utils/appRequest";
import { LoadState } from "../types/analyzer";
import type { MoverRow, WatchlistResponse } from "../types/market";

// Kept outside the composable so switching tabs shows the last quotes while reloading.
const quotes = ref<Record<string, MoverRow>>({});

export function useWatchlistQuotes({ reloadKey }: { reloadKey: Ref<string> }) {
  const quotesState = ref<LoadState>(LoadState.Idle);

  async function loadQuotes() {
    quotesState.value = LoadState.Loading;
    try {
      const data = await appRequest<WatchlistResponse>({ url: "/watchlist" });
      quotes.value = Object.fromEntries(data.rows.map((row) => [row.symbol, row]));
      quotesState.value = LoadState.Ready;
    } catch {
      quotesState.value = LoadState.Error;
    }
  }

  // An empty key means the symbol lists have not arrived yet, so there is nothing to quote.
  watch(reloadKey, (key) => key && loadQuotes(), { immediate: true });

  return { quotes, quotesState };
}
