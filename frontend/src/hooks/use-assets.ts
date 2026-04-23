"use client";

import { useDeferredValue, useMemo } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import {
  searchSymbols,
  listUserAssets,
  createUserAsset,
  deleteUserAsset,
} from "@/lib/api/asset";
import type { AssetType, UserAssetResponse } from "@/types/asset";
import type { UserAssetCreateInput } from "@/lib/schemas/asset";

// ── Query keys (co-located) ───────────────────────────────────────────────────

export const assetKeys = {
  userAssets: ["user-assets"] as const,
  symbolSearch: (
    q: string,
    assetType: AssetType | undefined,
    exchange: string | undefined,
  ) => ["symbol-search", q, assetType, exchange] as const,
} as const;

// ── User assets ───────────────────────────────────────────────────────────────

export function useUserAssets() {
  return useQuery<UserAssetResponse[]>({
    queryKey: assetKeys.userAssets,
    queryFn: listUserAssets,
    staleTime: 30_000,
  });
}

export function useCreateUserAsset() {
  const queryClient = useQueryClient();
  const router = useRouter();

  return useMutation<UserAssetResponse, Error, UserAssetCreateInput>({
    mutationFn: createUserAsset,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: assetKeys.userAssets });
      router.push("/assets");
    },
  });
}

export function useDeleteUserAsset() {
  const queryClient = useQueryClient();

  return useMutation<void, Error, number>({
    mutationFn: deleteUserAsset,
    onMutate: async (id) => {
      await queryClient.cancelQueries({ queryKey: assetKeys.userAssets });
      const previous = queryClient.getQueryData<UserAssetResponse[]>(
        assetKeys.userAssets,
      );
      queryClient.setQueryData<UserAssetResponse[]>(
        assetKeys.userAssets,
        (old) => old?.filter((a) => a.id !== id) ?? [],
      );
      return { previous };
    },
    onError: (_err, _id, context) => {
      const ctx = context as { previous?: UserAssetResponse[] } | undefined;
      if (ctx?.previous !== undefined) {
        queryClient.setQueryData(assetKeys.userAssets, ctx.previous);
      }
    },
    onSettled: () => {
      void queryClient.invalidateQueries({ queryKey: assetKeys.userAssets });
    },
  });
}

// ── Symbol search ─────────────────────────────────────────────────────────────

export function useSymbolSearch(
  q: string,
  assetType?: AssetType,
  exchange?: string,
) {
  // useDeferredValue 로 300ms 디바운스 효과 (낮은 우선순위 렌더링)
  const deferredQ = useDeferredValue(q);
  const deferredAssetType = useDeferredValue(assetType);
  const deferredExchange = useDeferredValue(exchange);

  const enabled = useMemo(
    () => deferredQ.length >= 1 || deferredAssetType != null,
    [deferredQ, deferredAssetType],
  );

  return useQuery({
    queryKey: assetKeys.symbolSearch(
      deferredQ,
      deferredAssetType,
      deferredExchange,
    ),
    queryFn: () =>
      searchSymbols({
        q: deferredQ || undefined,
        assetType: deferredAssetType,
        exchange: deferredExchange,
      }),
    enabled,
    staleTime: 30_000,
  });
}
