"use client";

import { useQuery } from "@tanstack/react-query";
import { getNetWorth } from "@/lib/api/net-worth";
import type { NetWorthResponse } from "@/types/net-worth";

export const netWorthKeys = {
  byDisplay: (displayCurrency?: string) =>
    ["netWorth", displayCurrency ?? "native"] as const,
} as const;

export function useNetWorth(displayCurrency?: string) {
  return useQuery<NetWorthResponse>({
    queryKey: netWorthKeys.byDisplay(displayCurrency),
    queryFn: () => getNetWorth(displayCurrency),
    staleTime: 30_000,
  });
}
