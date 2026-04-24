"use client";

import { useState } from "react";
import Link from "next/link";
import { ArrowLeft, Plus, X, Pencil } from "lucide-react"; // MODIFIED
import { usePortfolioHoldings } from "@/hooks/use-portfolio";
import { useAssetSummary } from "@/hooks/use-transactions";
import { TransactionList } from "./transaction-list";
import { TransactionForm } from "./transaction-form";
import { AssetTypeBadge } from "./asset-type-badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { formatCurrency, formatQuantity } from "@/lib/format";
import type { TransactionResponse } from "@/types/transaction"; // ADDED

interface AssetDetailProps {
  userAssetId: number;
}

function AssetDetailSkeleton() {
  return (
    <div className="space-y-4" aria-label="자산 상세 로딩 중" role="status">
      <div className="h-8 w-48 rounded bg-muted animate-pulse" />
      <div className="h-32 rounded-xl border bg-muted/40 animate-pulse" />
      <div className="h-48 rounded-xl border bg-muted/40 animate-pulse" />
    </div>
  );
}

export function AssetDetail({ userAssetId }: AssetDetailProps) {
  const [showAddForm, setShowAddForm] = useState(false);
  const [editingTx, setEditingTx] = useState<TransactionResponse | null>(null); // ADDED

  const holdingsQuery = usePortfolioHoldings();
  const summaryQuery = useAssetSummary(userAssetId);

  const isLoading = holdingsQuery.isLoading;

  if (isLoading) return <AssetDetailSkeleton />;

  if (holdingsQuery.isError) {
    return (
      <div className="space-y-4">
        <Link
          href="/assets"
          className="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors"
          aria-label="보유 자산 목록으로 돌아가기"
        >
          <ArrowLeft className="h-4 w-4" aria-hidden="true" />
          보유 자산 목록으로
        </Link>
        <p role="alert" className="text-sm text-destructive">
          자산 정보를 불러오지 못했습니다.
        </p>
      </div>
    );
  }

  const holdings = holdingsQuery.data ?? [];
  const holding = holdings.find((h) => h.userAssetId === userAssetId);

  return (
    <div className="space-y-6">
      <Link
        href="/assets"
        className="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors"
        aria-label="보유 자산 목록으로 돌아가기"
      >
        <ArrowLeft className="h-4 w-4" aria-hidden="true" />
        보유 자산 목록으로
      </Link>

      {holding ? (
        <>
          <Card>
            <CardHeader>
              <div className="flex items-center gap-3">
                <div>
                  <CardTitle className="text-xl">{holding.assetSymbol.symbol}</CardTitle>
                  <p className="text-sm text-muted-foreground mt-1">
                    {holding.assetSymbol.name}
                  </p>
                </div>
                <AssetTypeBadge assetType={holding.assetSymbol.assetType} />
              </div>
            </CardHeader>
            <CardContent>
              <dl className="grid grid-cols-2 gap-x-6 gap-y-3 text-sm sm:grid-cols-4">
                <div>
                  <dt className="text-muted-foreground">보유 수량</dt>
                  <dd className="font-semibold mt-0.5">
                    {formatQuantity(holding.quantity, holding.assetSymbol.assetType)}
                  </dd>
                </div>
                <div>
                  <dt className="text-muted-foreground">평균 단가</dt>
                  <dd className="font-semibold mt-0.5">
                    {formatCurrency(holding.avgCost, holding.assetSymbol.currency)}
                  </dd>
                </div>
                <div>
                  <dt className="text-muted-foreground">현재가</dt>
                  <dd className="font-semibold mt-0.5">
                    {holding.latestPrice !== null
                      ? formatCurrency(holding.latestPrice, holding.assetSymbol.currency)
                      : "—"}
                  </dd>
                </div>
                <div>
                  <dt className="text-muted-foreground">평가액</dt>
                  <dd className="font-semibold mt-0.5">
                    {holding.latestValue !== null
                      ? formatCurrency(holding.latestValue, holding.assetSymbol.currency)
                      : "—"}
                  </dd>
                </div>
              </dl>
            </CardContent>
          </Card>

          {summaryQuery.data && ( // MODIFIED — realizedPnl + remaining_quantity 섹션
            <Card>
              <CardHeader>
                <CardTitle className="text-base">투자 요약</CardTitle>
              </CardHeader>
              <CardContent>
                <dl className="grid grid-cols-2 gap-x-6 gap-y-3 text-sm sm:grid-cols-3">
                  <div>
                    <dt className="text-muted-foreground">총 매수 수량</dt>
                    <dd className="font-semibold mt-0.5">
                      {summaryQuery.data.totalBoughtQuantity}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-muted-foreground">총 매도 수량</dt>
                    <dd className="font-semibold mt-0.5">
                      {summaryQuery.data.totalSoldQuantity}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-muted-foreground">남은 수량</dt>
                    <dd className="font-semibold mt-0.5">
                      {summaryQuery.data.remainingQuantity}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-muted-foreground">총 투자금액</dt>
                    <dd className="font-semibold mt-0.5">
                      {formatCurrency(
                        summaryQuery.data.totalInvested,
                        summaryQuery.data.currency,
                      )}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-muted-foreground">매도 금액</dt>
                    <dd className="font-semibold mt-0.5">
                      {formatCurrency(
                        summaryQuery.data.totalSoldValue,
                        summaryQuery.data.currency,
                      )}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-muted-foreground">실현 손익</dt>
                    <dd
                      className={`font-semibold mt-0.5 ${
                        Number(summaryQuery.data.realizedPnl) > 0
                          ? "text-emerald-600"
                          : Number(summaryQuery.data.realizedPnl) < 0
                            ? "text-rose-600"
                            : "text-muted-foreground"
                      }`}
                    >
                      {Number(summaryQuery.data.realizedPnl) > 0 ? "+" : ""}
                      {formatCurrency(
                        summaryQuery.data.realizedPnl,
                        summaryQuery.data.currency,
                      )}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-muted-foreground">거래 건수</dt>
                    <dd className="font-semibold mt-0.5">
                      {summaryQuery.data.transactionCount}건
                    </dd>
                  </div>
                </dl>
              </CardContent>
            </Card>
          )}
        </>
      ) : (
        <Card>
          <CardContent className="pt-6">
            <p className="text-sm text-muted-foreground">
              자산 정보를 찾을 수 없습니다. 가격 데이터가 수집되기 전일 수 있습니다.
            </p>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="text-base">거래 내역</CardTitle>
            <Button
              type="button"
              size="sm"
              variant={showAddForm ? "ghost" : "outline"}
              onClick={() => setShowAddForm((prev) => !prev)}
              aria-label={showAddForm ? "거래 추가 폼 닫기" : "거래 추가"}
              className="gap-2"
            >
              {showAddForm ? (
                <>
                  <X className="h-4 w-4" aria-hidden="true" />
                  닫기
                </>
              ) : (
                <>
                  <Plus className="h-4 w-4" aria-hidden="true" />
                  거래 추가
                </>
              )}
            </Button>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          {showAddForm && (
            <div className="rounded-lg border bg-muted/20 p-4">
              <TransactionForm
                userAssetId={userAssetId}
                onSuccess={() => setShowAddForm(false)}
              />
            </div>
          )}
          {editingTx && ( // ADDED
            <div className="rounded-lg border bg-muted/20 p-4">
              <div className="flex items-center justify-between mb-3">
                <p className="text-sm font-medium flex items-center gap-1">
                  <Pencil className="h-3.5 w-3.5" aria-hidden="true" />
                  거래 수정
                </p>
                <button
                  type="button"
                  onClick={() => setEditingTx(null)}
                  aria-label="거래 수정 폼 닫기"
                  className="rounded p-1 text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
                >
                  <X className="h-4 w-4" aria-hidden="true" />
                </button>
              </div>
              <TransactionForm
                userAssetId={userAssetId}
                mode="edit"
                initialValues={editingTx}
                onSuccess={() => setEditingTx(null)}
              />
            </div>
          )}
          <TransactionList
            userAssetId={userAssetId}
            onEdit={(tx) => {
              setShowAddForm(false);
              setEditingTx(tx);
            }}
          /> {/* MODIFIED */}
        </CardContent>
      </Card>
    </div>
  );
}
