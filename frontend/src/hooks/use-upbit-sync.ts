"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { isAxiosError } from "axios";
import { toast } from "sonner";
import { syncUpbit } from "@/lib/api/integrations";
import type { UpbitSyncResult } from "@/lib/api/integrations";

export const upbitSyncQueryKeys = {
  transactions: ["transactions"] as const,
  portfolioSummary: ["portfolioSummary"] as const,
  portfolioHoldings: ["portfolio", "holdings"] as const,
} as const;

export function useUpbitSync() {
  const queryClient = useQueryClient();

  return useMutation<UpbitSyncResult, Error, void>({
    mutationFn: syncUpbit,
    onSuccess: (result) => {
      void queryClient.invalidateQueries({ queryKey: upbitSyncQueryKeys.transactions });
      void queryClient.invalidateQueries({ queryKey: upbitSyncQueryKeys.portfolioSummary });
      void queryClient.invalidateQueries({ queryKey: upbitSyncQueryKeys.portfolioHoldings });

      if (result.inserted === 0 && result.skippedDuplicate > 0) {
        toast.success(`이미 동기화된 거래입니다 (중복 ${result.skippedDuplicate}건).`);
      } else {
        toast.success(`업비트 ${result.inserted}건의 매매 기록을 가져왔습니다.`);
      }
    },
    onError: (err) => {
      if (isAxiosError(err)) {
        const status = err.response?.status;
        const detail = (err.response?.data as { detail?: string } | undefined)?.detail;

        if (status === 502) {
          toast.error(
            detail ??
              "업비트 API 키가 설정되지 않았습니다. 서버 환경변수 (UPBIT_ACCESS_KEY, UPBIT_SECRET_KEY) 를 확인하세요.",
          );
          return;
        }
        if (status === 401) {
          toast.error("로그인이 필요합니다.");
          return;
        }
        toast.error(detail ?? "업비트 동기화에 실패했습니다.");
        return;
      }
      toast.error("업비트 동기화에 실패했습니다.");
    },
  });
}
