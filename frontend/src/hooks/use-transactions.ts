"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  createTransaction,
  listTransactions,
  deleteTransaction,
  getAssetSummary,
} from "@/lib/api/transaction";
import type { TransactionResponse, UserAssetSummaryResponse } from "@/types/transaction";
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

export function useCreateTransaction() {
  const queryClient = useQueryClient();

  return useMutation<
    TransactionResponse,
    Error,
    { userAssetId: number; data: TransactionCreateInput }
  >({
    mutationFn: ({ userAssetId, data }) => createTransaction(userAssetId, data),
    onSuccess: (_result, { userAssetId }) => {
      void queryClient.invalidateQueries({
        queryKey: transactionKeys.list(userAssetId),
      });
      void queryClient.invalidateQueries({
        queryKey: transactionKeys.summary(userAssetId),
      });
      for (const key of portfolioInvalidationKeys) {
        void queryClient.invalidateQueries({ queryKey: key });
      }
    },
  });
}

export function useDeleteTransaction() {
  const queryClient = useQueryClient();

  return useMutation<void, Error, { userAssetId: number; txId: number }>({
    mutationFn: ({ userAssetId, txId }) => deleteTransaction(userAssetId, txId),
    onSuccess: (_result, { userAssetId }) => {
      void queryClient.invalidateQueries({
        queryKey: transactionKeys.list(userAssetId),
      });
      void queryClient.invalidateQueries({
        queryKey: transactionKeys.summary(userAssetId),
      });
      for (const key of portfolioInvalidationKeys) {
        void queryClient.invalidateQueries({ queryKey: key });
      }
    },
  });
}
