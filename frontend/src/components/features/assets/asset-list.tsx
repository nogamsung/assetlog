"use client";

import Link from "next/link";
import { type AxiosError } from "axios";
import { usePortfolioHoldings } from "@/hooks/use-portfolio";
import { useDeleteUserAsset } from "@/hooks/use-assets";
import { useSampleSeed } from "@/hooks/use-sample-seed";
import { AssetTypeBadge } from "./asset-type-badge";
import { Button } from "@/components/ui/button";
import { Trash2, Plus } from "lucide-react";
import { formatCurrency, formatQuantity } from "@/lib/format";

function AssetListSkeleton() {
  return (
    <div className="space-y-3" aria-label="자산 목록 로딩 중">
      {[1, 2, 3].map((i) => (
        <div
          key={i}
          className="h-20 rounded-lg border bg-muted/40 animate-pulse"
        />
      ))}
    </div>
  );
}

function EmptyState() {
  const { mutate: seedSample, isPending: isSeeding } = useSampleSeed();

  return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      <p className="text-muted-foreground mb-4">보유 자산이 없습니다.</p>
      <div className="flex flex-wrap items-center justify-center gap-2">
        <Link
          href="/assets/new"
          className="inline-flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground shadow hover:bg-primary/90 transition-colors"
        >
          <Plus className="h-4 w-4" aria-hidden="true" />
          자산 추가하기
        </Link>
        <Button
          variant="outline"
          size="sm"
          onClick={() => seedSample()}
          disabled={isSeeding}
          aria-label="샘플 데이터로 시작"
          className="text-muted-foreground"
        >
          {isSeeding ? "추가 중..." : "샘플 데이터로 시작"}
        </Button>
      </div>
    </div>
  );
}

export function AssetList() {
  const { data: holdings, isLoading, isError, error } = usePortfolioHoldings();
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

  if (!holdings || holdings.length === 0) return <EmptyState />;

  function handleDelete(id: number, symbolName: string) {
    if (window.confirm(`"${symbolName}" 을(를) 보유 자산에서 삭제하시겠습니까?`)) {
      deleteMutation.mutate(id);
    }
  }

  return (
    <div className="space-y-2">
      {holdings.map((holding) => {
        const { assetSymbol, userAssetId } = holding;
        const currency = assetSymbol.currency;

        return (
          <div
            key={userAssetId}
            className="flex items-center justify-between rounded-lg border bg-card px-4 py-3 shadow-sm"
          >
            <Link
              href={`/assets/${userAssetId}`}
              className="flex flex-1 items-center gap-4 min-w-0"
              aria-label={`${assetSymbol.symbol} 상세 보기`}
            >
              <div className="min-w-0">
                <p className="font-semibold text-sm">{assetSymbol.symbol}</p>
                <p className="text-xs text-muted-foreground truncate">
                  {assetSymbol.name}
                </p>
              </div>
              <AssetTypeBadge assetType={assetSymbol.assetType} />
              <div className="hidden sm:flex items-center gap-4 text-xs text-muted-foreground">
                <span>{assetSymbol.exchange}</span>
                <span>{assetSymbol.currency}</span>
              </div>
              <div className="hidden md:flex items-center gap-4 text-xs ml-auto mr-4">
                <div className="text-right">
                  <p className="text-muted-foreground">보유 수량</p>{/* MODIFIED */}
                  <p className="font-medium">
                    {formatQuantity(holding.quantity, assetSymbol.assetType)}
                  </p>
                </div>
                <div className="text-right">
                  <p className="text-muted-foreground">평단가</p>
                  <p className="font-medium">
                    {formatCurrency(holding.avgCost, currency)}
                  </p>
                </div>
                <div className="text-right">
                  <p className="text-muted-foreground">현재가</p>
                  <p className="font-medium">
                    {holding.latestPrice !== null
                      ? formatCurrency(holding.latestPrice, currency)
                      : "—"}
                  </p>
                </div>
                <div className="text-right">
                  <p className="text-muted-foreground">평가액</p>
                  <p className="font-medium">
                    {holding.latestValue !== null
                      ? formatCurrency(holding.latestValue, currency)
                      : "—"}
                  </p>
                </div>
                {Number(holding.realizedPnl) !== 0 && ( // ADDED realized_pnl 뱃지
                  <div className="text-right">
                    <p className="text-muted-foreground">실현</p>
                    <p
                      className={`font-medium ${
                        Number(holding.realizedPnl) > 0
                          ? "text-emerald-600"
                          : "text-rose-600"
                      }`}
                    >
                      {Number(holding.realizedPnl) > 0 ? "+" : ""}
                      {formatCurrency(holding.realizedPnl, currency)}
                    </p>
                  </div>
                )}
              </div>
            </Link>
            <Button
              variant="ghost"
              size="icon"
              onClick={() => handleDelete(userAssetId, assetSymbol.symbol)}
              disabled={deleteMutation.isPending}
              aria-label={`${assetSymbol.symbol} 삭제`}
            >
              <Trash2 className="h-4 w-4 text-destructive" aria-hidden="true" />
            </Button>
          </div>
        );
      })}
    </div>
  );
}
