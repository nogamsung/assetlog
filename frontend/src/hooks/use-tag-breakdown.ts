"use client";

import { useQuery } from "@tanstack/react-query";
import { getTagBreakdown } from "@/lib/api/tag-breakdown";
import type { TagBreakdownResponse } from "@/types/tag-breakdown";

// ── Query keys (co-located) ───────────────────────────────────────────────────

export const tagBreakdownKeys = {
  all: ["portfolio", "tagBreakdown"] as const,
} as const;

// ── Hook ──────────────────────────────────────────────────────────────────────

export function useTagBreakdown() {
  return useQuery<TagBreakdownResponse>({
    queryKey: tagBreakdownKeys.all,
    queryFn: getTagBreakdown,
    staleTime: 30_000,
  });
}
