"use client";

import { useQuery } from "@tanstack/react-query";
import { getMarketIndices } from "@/lib/api/market-index";
import type { IndexQuote } from "@/types/market-index";

export const marketIndexKeys = {
  all: ["market", "indices"] as const,
} as const;

export function useMarketIndices() {
  return useQuery<IndexQuote[]>({
    queryKey: marketIndexKeys.all,
    queryFn: getMarketIndices,
    staleTime: 5 * 60_000,
    retry: false,
  });
}
