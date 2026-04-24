"use client";

import { useQuery } from "@tanstack/react-query";
import { getPortfolioSummary, getPortfolioHoldings } from "@/lib/api/portfolio";
import type { PortfolioSummary, HoldingResponse } from "@/types/portfolio";

// ── Query keys (co-located) ───────────────────────────────────────────────────

export const portfolioKeys = {
  summary: (convertTo?: string) =>
    ["portfolio", "summary", convertTo ?? null] as const,
  holdings: ["portfolio", "holdings"] as const,
} as const;

// ── Hooks ─────────────────────────────────────────────────────────────────────

export function usePortfolioSummary(convertTo?: string) {
  return useQuery<PortfolioSummary>({
    queryKey: portfolioKeys.summary(convertTo),
    queryFn: () => getPortfolioSummary({ convertTo }),
    staleTime: 60_000,
  });
}

export function usePortfolioHoldings() {
  return useQuery<HoldingResponse[]>({
    queryKey: portfolioKeys.holdings,
    queryFn: getPortfolioHoldings,
    staleTime: 60_000,
  });
}
