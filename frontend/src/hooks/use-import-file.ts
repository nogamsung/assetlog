"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { isAxiosError } from "axios";
import { toast } from "sonner";
import { importFile } from "@/lib/api/integrations";
import type { ImportFileArgs, ImportFileResult } from "@/lib/api/integrations";

// ── Query keys ────────────────────────────────────────────────────────────────

export const importFileQueryKeys = {
  transactions: ["transactions"] as const,
  portfolioSummary: ["portfolioSummary"] as const,
  portfolioHoldings: ["portfolio", "holdings"] as const,
} as const;

// ── Hook ──────────────────────────────────────────────────────────────────────

export function useImportFile() {
  const queryClient = useQueryClient();

  return useMutation<ImportFileResult, Error, ImportFileArgs>({
    mutationFn: importFile,
    onSuccess: (result, variables) => {
      if (variables.dryRun) return;

      void queryClient.invalidateQueries({
        queryKey: importFileQueryKeys.transactions,
      });
      void queryClient.invalidateQueries({
        queryKey: importFileQueryKeys.portfolioSummary,
      });
      void queryClient.invalidateQueries({
        queryKey: importFileQueryKeys.portfolioHoldings,
      });

      const total =
        result.insertedTrades + result.insertedDividends + result.insertedCashTxs;
      toast.success(`${total}건의 거래내역이 가져오기 완료되었습니다.`);
    },
    onError: (err) => {
      if (isAxiosError(err)) {
        const status = err.response?.status;
        const detail = (err.response?.data as { detail?: string } | undefined)?.detail;

        if (status === 422) {
          const msg = detail?.includes("password")
            ? "PDF 비밀번호가 올바르지 않습니다."
            : (detail ?? "파일 형식이 올바르지 않습니다.");
          toast.error(msg);
          return;
        }
        if (status === 401) {
          toast.error("로그인이 필요합니다.");
          return;
        }
        toast.error(detail ?? "가져오기에 실패했습니다.");
        return;
      }
      toast.error("가져오기에 실패했습니다.");
    },
  });
}
