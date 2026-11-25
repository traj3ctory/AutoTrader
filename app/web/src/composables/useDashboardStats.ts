import { computed, type Ref } from "vue";
import { AUTOMATION_GATE_GOAL } from "../constants/analyzer";
import type { DashboardResponse } from "../types/analyzer";

export function useDashboardStats({ dashboard, searchQuery }: { dashboard: () => DashboardResponse | null; searchQuery: Ref<string> }) {
  const scorecardStats = computed(() => {
    const records = dashboard()?.scorecard.records || [];
    const reviewed = records.length;
    const correct = records.filter((r) => /correct/i.test(r.outcome)).length;
    const invalidated = records.filter((r) => /invalidated/i.test(r.outcome)).length;
    const taken = records.filter((r) => r.trade_taken).length;
    const wins = records.filter((r) => /^win$/i.test(r.trade_result)).length;
    const losses = records.filter((r) => /^loss$/i.test(r.trade_result)).length;
    const qualifying = records.filter((r) => /correct/i.test(r.outcome) || r.trade_taken).length;
    const gatePct = Math.min(100, Math.round((qualifying / AUTOMATION_GATE_GOAL) * 100));
    const accuracyPct = reviewed > 0 ? Math.round((correct / reviewed) * 100) : 0;
    return { reviewed, correct, invalidated, taken, wins, losses, qualifying, gatePct, accuracyPct };
  });

  const mistakeTags = computed(() => {
    const counts = new Map<string, number>();
    for (const item of dashboard()?.journal || []) {
      if (item.mistake_tag && item.mistake_tag !== "N/A") {
        counts.set(item.mistake_tag, (counts.get(item.mistake_tag) || 0) + 1);
      }
    }
    return [...counts.entries()].sort((a, b) => b[1] - a[1]);
  });

  const filteredRecords = computed(() => {
    const records = dashboard()?.scorecard.records || [];
    const q = searchQuery.value.trim().toLowerCase();
    if (!q) return records;
    return records.filter((r) =>
      [r.coin, r.trade_type, r.direction, r.outcome, r.trade_result, r.review_note].join(" ").toLowerCase().includes(q)
    );
  });

  return { scorecardStats, mistakeTags, filteredRecords };
}
