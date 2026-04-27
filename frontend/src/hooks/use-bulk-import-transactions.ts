"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { isAxiosError } from "axios";
import { toast } from "sonner";
import { apiClient } from "@/lib/api-client";
import type { BulkTransactionRow, BulkTransactionResponse, BulkTransactionErrorBody } from "@/types/bulk-transaction";

// ── Query keys (co-located) ───────────────────────────────────────────────────

export const bulkImportQueryKeys = {
  transactions: ["transactions"] as const,
  userAssetSummary: ["user-asset-summary"] as const,
  portfolioSummary: ["portfolioSummary"] as const,
  portfolioHoldings: ["portfolio", "holdings"] as const,
} as const;

// ── Mutation argument types ───────────────────────────────────────────────────

export type BulkImportJsonArgs = {
  mode: "json";
  rows: BulkTransactionRow[];
};

export type BulkImportCsvArgs = {
  mode: "csv";
  file: File;
};

export type BulkImportArgs = BulkImportJsonArgs | BulkImportCsvArgs;

// ── API function ──────────────────────────────────────────────────────────────

async function bulkImportTransactions(
  args: BulkImportArgs,
): Promise<BulkTransactionResponse> {
  if (args.mode === "json") {
    const response = await apiClient.post<BulkTransactionResponse>(
      "/api/transactions/bulk",
      { rows: args.rows },
      { headers: { "Content-Type": "application/json" } },
    );
    return response.data;
  }

  const formData = new FormData();
  formData.append("file", args.file);
  const response = await apiClient.post<BulkTransactionResponse>(
    "/api/transactions/bulk",
    formData,
  );
  return response.data;
}

// ── Hook ──────────────────────────────────────────────────────────────────────

export function useBulkImportTransactions() {
  const queryClient = useQueryClient();

  return useMutation<BulkTransactionResponse, Error, BulkImportArgs>({
    mutationFn: bulkImportTransactions,
    onSuccess: (result) => {
      void queryClient.invalidateQueries({
        queryKey: bulkImportQueryKeys.transactions,
      });
      void queryClient.invalidateQueries({
        queryKey: bulkImportQueryKeys.userAssetSummary,
      });
      void queryClient.invalidateQueries({
        queryKey: bulkImportQueryKeys.portfolioSummary,
      });
      void queryClient.invalidateQueries({
        queryKey: bulkImportQueryKeys.portfolioHoldings,
      });
      toast.success(`${result.imported_count}건의 거래가 일괄 등록되었습니다.`);
    },
    onError: (err) => {
      if (isAxiosError(err) && err.response?.status === 422) {
        // 422 는 컴포넌트에서 errors[] 배열로 처리 — toast 스킵
        return;
      }
      const body = isAxiosError(err)
        ? (err.response?.data as BulkTransactionErrorBody | undefined)
        : undefined;
      const message = body?.detail ?? "일괄 등록에 실패했습니다.";
      toast.error(message);
    },
  });
}

/** 422 응답에서 errors[] 를 추출하는 유틸 */
export function extractBulkErrors(err: Error): BulkTransactionErrorBody["errors"] | null {
  if (isAxiosError(err) && err.response?.status === 422) {
    const body = err.response.data as BulkTransactionErrorBody | undefined;
    return body?.errors ?? null;
  }
  return null;
}
