"use client";

import Link from "next/link";
import { type AxiosError } from "axios";
import { useUserAssets, useDeleteUserAsset } from "@/hooks/use-assets";
import { AssetTypeBadge } from "./asset-type-badge";
import { Button } from "@/components/ui/button";
import { Trash2, Plus } from "lucide-react";

function AssetListSkeleton() {
  return (
    <div className="space-y-3" aria-label="자산 목록 로딩 중">
      {[1, 2, 3].map((i) => (
        <div
          key={i}
          className="h-16 rounded-lg border bg-muted/40 animate-pulse"
        />
      ))}
    </div>
  );
}

function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      <p className="text-muted-foreground mb-4">보유 자산이 없습니다.</p>
      <Link
        href="/assets/new"
        className="inline-flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground shadow hover:bg-primary/90 transition-colors"
      >
        <Plus className="h-4 w-4" aria-hidden="true" />
        자산 추가하기
      </Link>
    </div>
  );
}

export function AssetList() {
  const { data: assets, isLoading, isError, error } = useUserAssets();
  const deleteMutation = useDeleteUserAsset();

  if (isLoading) return <AssetListSkeleton />;

  if (isError) {
    const axiosErr = error as AxiosError<{ detail: string }>;
    const message =
      axiosErr.response?.data?.detail ?? "자산 목록을 불러오지 못했습니다.";
    return (
      <p role="alert" className="text-sm text-destructive">
        {message}
      </p>
    );
  }

  if (!assets || assets.length === 0) return <EmptyState />;

  function handleDelete(id: number, symbolName: string) {
    if (window.confirm(`"${symbolName}" 을(를) 보유 자산에서 삭제하시겠습니까?`)) {
      deleteMutation.mutate(id);
    }
  }

  return (
    <div className="space-y-2">
      {assets.map((asset) => (
        <div
          key={asset.id}
          className="flex items-center justify-between rounded-lg border bg-card px-4 py-3 shadow-sm"
        >
          <div className="flex items-center gap-4">
            <div>
              <p className="font-semibold text-sm">
                {asset.assetSymbol.symbol}
              </p>
              <p className="text-xs text-muted-foreground">
                {asset.assetSymbol.name}
              </p>
            </div>
            <AssetTypeBadge assetType={asset.assetSymbol.assetType} />
            <span className="text-xs text-muted-foreground hidden sm:inline">
              {asset.assetSymbol.exchange}
            </span>
            <span className="text-xs text-muted-foreground hidden sm:inline">
              {asset.assetSymbol.currency}
            </span>
          </div>
          <Button
            variant="ghost"
            size="icon"
            onClick={() =>
              handleDelete(asset.id, asset.assetSymbol.symbol)
            }
            disabled={deleteMutation.isPending}
            aria-label={`${asset.assetSymbol.symbol} 삭제`}
          >
            <Trash2 className="h-4 w-4 text-destructive" aria-hidden="true" />
          </Button>
        </div>
      ))}
    </div>
  );
}
