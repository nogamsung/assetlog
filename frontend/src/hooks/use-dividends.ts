"use client";

import { useQuery } from "@tanstack/react-query";
import { listDividends } from "@/lib/api/dividend";
import type { DividendListResponse } from "@/types/dividend";

export const dividendKeys = {
  bySymbol: (assetSymbolId: number) =>
    ["dividends", "by-symbol", assetSymbolId] as const,
  all: () => ["dividends", "all"] as const,
} as const;

export function useDividendsBySymbol(assetSymbolId: number | undefined) {
  return useQuery<DividendListResponse>({
    queryKey: dividendKeys.bySymbol(assetSymbolId ?? -1),
    queryFn: () => listDividends({ assetSymbolId }),
    staleTime: 60_000,
    enabled: assetSymbolId !== undefined && assetSymbolId > 0,
  });
}
