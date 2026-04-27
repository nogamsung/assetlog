"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  getCashAccounts,
  createCashAccount,
  updateCashAccount,
  deleteCashAccount,
} from "@/lib/api/cash-account";
import { portfolioKeys } from "@/hooks/use-portfolio";
import type { CashAccount } from "@/types/cash-account";
import type {
  CashAccountCreateInput,
  CashAccountUpdateInput,
} from "@/lib/schemas/cash-account";

// ── Query keys (co-located) ───────────────────────────────────────────────────

export const cashAccountKeys = {
  all: ["cash-accounts"] as const,
} as const;

// ── Hooks ─────────────────────────────────────────────────────────────────────

export function useCashAccounts() {
  return useQuery<CashAccount[]>({
    queryKey: cashAccountKeys.all,
    queryFn: getCashAccounts,
    staleTime: 30_000,
  });
}

export function useCreateCashAccount() {
  const queryClient = useQueryClient();

  return useMutation<CashAccount, Error, CashAccountCreateInput>({
    mutationFn: createCashAccount,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: cashAccountKeys.all });
      void queryClient.invalidateQueries({ queryKey: portfolioKeys.summary() });
    },
  });
}

export function useUpdateCashAccount() {
  const queryClient = useQueryClient();

  return useMutation<
    CashAccount,
    Error,
    { id: number; input: CashAccountUpdateInput }
  >({
    mutationFn: ({ id, input }) => updateCashAccount(id, input),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: cashAccountKeys.all });
      void queryClient.invalidateQueries({ queryKey: portfolioKeys.summary() });
    },
  });
}

export function useDeleteCashAccount() {
  const queryClient = useQueryClient();

  return useMutation<void, Error, number>({
    mutationFn: deleteCashAccount,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: cashAccountKeys.all });
      void queryClient.invalidateQueries({ queryKey: portfolioKeys.summary() });
    },
  });
}
