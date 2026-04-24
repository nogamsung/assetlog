"use client";

import { useState } from "react";
import Link from "next/link";
import { usePortfolioSummary, usePortfolioHoldings } from "@/hooks/use-portfolio";
import { SummaryCards } from "./summary-cards";
import { AllocationDonut } from "./allocation-donut";
import { HoldingsTable } from "./holdings-table";
import { PortfolioHistoryChart } from "./portfolio-history-chart";
import { CurrencySwitcher } from "./currency-switcher";

function DashboardSkeleton() {
  return (
    <div className="space-y-6" aria-label="대시보드 로딩 중" role="status">
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        {[1, 2, 3].map((i) => (
          <div key={i} className="h-28 rounded-xl border bg-muted/40 animate-pulse" />
        ))}
      </div>
      <div className="h-64 rounded-xl border bg-muted/40 animate-pulse" />
      <div className="h-64 rounded-xl border bg-muted/40 animate-pulse" />
    </div>
  );
}

function ErrorState({ message }: { message: string }) {
  return (
    <div role="alert" className="rounded-xl border border-destructive/30 bg-destructive/5 p-6 text-center">
      <p className="text-sm text-destructive">{message}</p>
    </div>
  );
}

function EmptyPortfolio() {
  return (
    <div className="flex flex-col items-center justify-center py-24 text-center">
      <p className="text-muted-foreground mb-4">
        포트폴리오에 자산이 없습니다. 첫 번째 자산을 추가해보세요.
      </p>
      <Link
        href="/assets/new"
        className="inline-flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground shadow hover:bg-primary/90 transition-colors"
      >
        자산 추가하기
      </Link>
    </div>
  );
}

export function DashboardView() {
  const [displayCurrency, setDisplayCurrency] = useState<string | null>(null);

  const summaryQuery = usePortfolioSummary(displayCurrency ?? undefined);
  const holdingsQuery = usePortfolioHoldings();

  const isLoading = summaryQuery.isLoading || holdingsQuery.isLoading;
  const isError = summaryQuery.isError || holdingsQuery.isError;

  if (isLoading) return <DashboardSkeleton />;

  if (isError) {
    const message =
      summaryQuery.error?.message ??
      holdingsQuery.error?.message ??
      "대시보드를 불러오지 못했습니다.";
    return <ErrorState message={message} />;
  }

  const summary = summaryQuery.data;
  const holdings = holdingsQuery.data ?? [];

  if (!summary || holdings.length === 0) {
    return <EmptyPortfolio />;
  }

  // 환율 미비 감지: convertTo 를 요청했으나 모든 converted_* 가 null 인 경우
  const fxUnavailable =
    displayCurrency !== null &&
    summary.convertedTotalValue === null &&
    summary.convertedPnlAbs === null &&
    summary.convertedRealizedPnl === null;

  // CurrencySwitcher 에 제공할 통화 목록 (totalValueByCurrency 키 기준)
  const availableCurrencies = Object.keys(summary.totalValueByCurrency);

  // 가장 큰 보유액 통화 결정 (차트 기본 currency)
  const defaultCurrency =
    Object.entries(summary.totalValueByCurrency).sort(
      ([, a], [, b]) => Number(b) - Number(a),
    )[0]?.[0] ?? "KRW";

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <span className="text-sm text-muted-foreground">포트폴리오 요약</span>
        <CurrencySwitcher
          value={displayCurrency}
          onChange={setDisplayCurrency}
          availableCurrencies={availableCurrencies}
        />
      </div>

      {fxUnavailable && (
        <p
          role="status"
          aria-live="polite"
          className="rounded-md border border-yellow-300 bg-yellow-50 px-3 py-2 text-xs text-yellow-800"
        >
          {displayCurrency} 환율 준비 중입니다. 잠시 후 다시 시도해 주세요.
        </p>
      )}

      <SummaryCards summary={summary} />
      <AllocationDonut allocation={summary.allocation} />
      <PortfolioHistoryChart currency={defaultCurrency} />
      <HoldingsTable holdings={holdings} />
    </div>
  );
}
