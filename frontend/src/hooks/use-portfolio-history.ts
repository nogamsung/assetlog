"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  backfillPortfolioHistory,
  getPortfolioHistory,
} from "@/lib/api/portfolio-history";
import type { BackfillResult } from "@/lib/api/portfolio-history";
import type { PortfolioHistoryResponse, HistoryPeriod } from "@/types/portfolio-history";

// ── Query keys (co-located) ───────────────────────────────────────────────────

export const portfolioHistoryKeys = {
  history: (period: HistoryPeriod, currency: string) =>
    ["portfolioHistory", period, currency] as const,
} as const;

// ── Hook ──────────────────────────────────────────────────────────────────────

export interface UsePortfolioHistoryParams {
  period: HistoryPeriod;
  currency: string;
}

export function usePortfolioHistory({ period, currency }: UsePortfolioHistoryParams) {
  return useQuery<PortfolioHistoryResponse>({
    queryKey: portfolioHistoryKeys.history(period, currency),
    queryFn: () => getPortfolioHistory({ period, currency }),
    staleTime: 60_000,
    enabled: currency.length > 0,
  });
}

export function useBackfillPortfolioHistory() {
  const queryClient = useQueryClient();
  return useMutation<BackfillResult, Error>({
    mutationFn: backfillPortfolioHistory,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["portfolioHistory"] });
      void queryClient.invalidateQueries({ queryKey: ["portfolioSummary"] });
      void queryClient.invalidateQueries({ queryKey: ["portfolio", "holdings"] });
    },
  });
}
