"use client";

import Link from "next/link";
import { usePortfolioSummary, usePortfolioHoldings } from "@/hooks/use-portfolio";
import { SummaryCards } from "./summary-cards";
import { AllocationDonut } from "./allocation-donut";
import { HoldingsTable } from "./holdings-table";
import { PortfolioHistoryChart } from "./portfolio-history-chart";

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
  const summaryQuery = usePortfolioSummary();
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

  // 가장 큰 보유액 통화 결정 (차트 기본 currency)
  const totalValueByCurrency = summary.totalValueByCurrency;
  const defaultCurrency =
    Object.entries(totalValueByCurrency).sort(
      ([, a], [, b]) => Number(b) - Number(a),
    )[0]?.[0] ?? "KRW";

  return (
    <div className="space-y-6">
      <SummaryCards summary={summary} />
      <AllocationDonut allocation={summary.allocation} />
      <PortfolioHistoryChart currency={defaultCurrency} />
      <HoldingsTable holdings={holdings} />
    </div>
  );
}
