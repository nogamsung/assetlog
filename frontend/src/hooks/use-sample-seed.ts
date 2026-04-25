"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { seedSampleData } from "@/lib/api/sample";
import type { SampleSeedResponse } from "@/types/sample";

// ── Invalidation keys ─────────────────────────────────────────────────────────

const seedInvalidationKeys = [
  ["user-assets"],
  ["portfolioSummary"],
  ["portfolio", "summary"],
  ["portfolio", "holdings"],
  ["portfolioHistory"],
  ["userTags"],
] as const;

// ── Hook ──────────────────────────────────────────────────────────────────────

export function useSampleSeed() {
  const queryClient = useQueryClient();

  return useMutation<SampleSeedResponse, Error>({
    mutationFn: seedSampleData,
    onSuccess: (data) => {
      if (data.seeded) {
        for (const key of seedInvalidationKeys) {
          void queryClient.invalidateQueries({ queryKey: key });
        }
        toast.success(
          `샘플 자산 5개와 거래 ${data.transactionsCreated}건이 추가되었습니다.`,
        );
      } else {
        toast("이미 보유 자산이 있어 샘플 데이터를 추가하지 않았습니다.");
      }
    },
    onError: () => {
      toast.error("샘플 데이터 추가에 실패했습니다.");
    },
  });
}
