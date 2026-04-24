"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { isAxiosError } from "axios";
import { toast } from "sonner";
import {
  createTransaction,
  updateTransaction,
  listTransactions,
  deleteTransaction,
  getAssetSummary,
  importTransactionsCsv,
} from "@/lib/api/transaction";
import type {
  TransactionResponse,
  UserAssetSummaryResponse,
  TransactionImportResponse,
  CsvImportValidationErrorBody,
} from "@/types/transaction";
import type { TransactionCreateInput } from "@/lib/schemas/transaction";

// ── Query keys (co-located) ───────────────────────────────────────────────────

export const transactionKeys = {
  list: (userAssetId: number) => ["transactions", userAssetId] as const,
  summary: (userAssetId: number) => ["assetSummary", userAssetId] as const,
} as const;

const portfolioInvalidationKeys = [
  ["portfolioSummary"],
  ["portfolio", "summary"],
  ["portfolio", "holdings"],
  ["portfolioHistory"],
] as const;

// ── Hooks ─────────────────────────────────────────────────────────────────────

export function useTransactions(userAssetId: number) {
  return useQuery<TransactionResponse[]>({
    queryKey: transactionKeys.list(userAssetId),
    queryFn: () => listTransactions(userAssetId, { limit: 100, offset: 0 }),
    staleTime: 30_000,
  });
}

export function useAssetSummary(userAssetId: number) {
  return useQuery<UserAssetSummaryResponse>({
    queryKey: transactionKeys.summary(userAssetId),
    queryFn: () => getAssetSummary(userAssetId),
    staleTime: 30_000,
  });
}

function invalidateAll(
  queryClient: ReturnType<typeof useQueryClient>,
  userAssetId: number,
): void {
  void queryClient.invalidateQueries({
    queryKey: transactionKeys.list(userAssetId),
  });
  void queryClient.invalidateQueries({
    queryKey: transactionKeys.summary(userAssetId),
  });
  for (const key of portfolioInvalidationKeys) {
    void queryClient.invalidateQueries({ queryKey: key });
  }
}

function extractErrorMessage(err: Error, fallback: string): string {
  if (isAxiosError(err)) {
    const detail = (err.response?.data as { detail?: string } | undefined)
      ?.detail;
    if (detail) return detail;
  }
  return fallback;
}

export function useCreateTransaction() {
  const queryClient = useQueryClient();

  return useMutation<
    TransactionResponse,
    Error,
    { userAssetId: number; data: TransactionCreateInput }
  >({
    mutationFn: ({ userAssetId, data }) => createTransaction(userAssetId, data),
    onSuccess: (_result, { userAssetId }) => {
      invalidateAll(queryClient, userAssetId);
      toast.success("거래가 기록되었습니다.");
    },
    onError: (err) => {
      toast.error(extractErrorMessage(err, "거래 기록에 실패했습니다."));
    },
  });
}

export function useUpdateTransaction() {
  const queryClient = useQueryClient();

  return useMutation<
    TransactionResponse,
    Error,
    { userAssetId: number; transactionId: number; data: TransactionCreateInput }
  >({
    mutationFn: ({ userAssetId, transactionId, data }) =>
      updateTransaction(userAssetId, transactionId, data),
    onSuccess: (_result, { userAssetId }) => {
      invalidateAll(queryClient, userAssetId);
      toast.success("거래가 수정되었습니다.");
    },
    onError: (err) => {
      toast.error(extractErrorMessage(err, "거래 수정에 실패했습니다."));
    },
  });
}

export function useImportTransactionsCsv() {
  const queryClient = useQueryClient();

  return useMutation<
    TransactionImportResponse,
    Error,
    { userAssetId: number; file: File }
  >({
    mutationFn: ({ userAssetId, file }) =>
      importTransactionsCsv(userAssetId, file),
    onSuccess: (result, { userAssetId }) => {
      invalidateAll(queryClient, userAssetId);
      toast.success(`${result.importedCount}건의 거래가 추가되었습니다.`);
    },
    onError: (err) => {
      if (isAxiosError(err) && err.response?.status === 422) {
        // 422 는 컴포넌트에서 errors[] 배열로 처리 — toast 스킵
        return;
      }
      const body = isAxiosError(err)
        ? (err.response?.data as CsvImportValidationErrorBody | undefined)
        : undefined;
      const message = body?.detail ?? "CSV 가져오기에 실패했습니다.";
      toast.error(message);
    },
  });
}

export function useDeleteTransaction() {
  const queryClient = useQueryClient();

  return useMutation<void, Error, { userAssetId: number; txId: number }>({
    mutationFn: ({ userAssetId, txId }) => deleteTransaction(userAssetId, txId),
    onSuccess: (_result, { userAssetId }) => {
      invalidateAll(queryClient, userAssetId);
      toast.success("거래가 삭제되었습니다.");
    },
    onError: (err) => {
      toast.error(extractErrorMessage(err, "거래 삭제에 실패했습니다."));
    },
  });
}
