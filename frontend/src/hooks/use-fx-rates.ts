"use client";

import { useQuery } from "@tanstack/react-query";
import { getFxRates } from "@/lib/api/fx-rate";
import type { FxRateEntry } from "@/types/fx-rate";

// ── Query keys (co-located) ───────────────────────────────────────────────────

export const fxRateKeys = {
  all: ["fx", "rates"] as const,
} as const;

// ── Hook ──────────────────────────────────────────────────────────────────────

export function useFxRates() {
  return useQuery<FxRateEntry[]>({
    queryKey: fxRateKeys.all,
    queryFn: getFxRates,
    staleTime: 60_000,
    retry: false,
  });
}
