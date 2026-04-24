"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { formatCurrency, formatPercent, formatRelativeTime } from "@/lib/format";
import type { PortfolioSummary } from "@/types/portfolio";

interface SummaryCardsProps {
  summary: PortfolioSummary;
}

function PnlColorClass(abs: string): string {
  const n = Number(abs);
  if (n > 0) return "text-green-600";
  if (n < 0) return "text-destructive";
  return "text-muted-foreground";
}

export function SummaryCards({ summary }: SummaryCardsProps) {
  const totalValueEntries = Object.entries(summary.totalValueByCurrency);
  const pnlEntries = Object.entries(summary.pnlByCurrency);

  const totalValueText =
    totalValueEntries.length === 0
      ? "—"
      : totalValueEntries
          .map(([currency, amount]) => formatCurrency(amount, currency))
          .join(" · ");

  const pnlText =
    pnlEntries.length === 0
      ? "—"
      : pnlEntries
          .map(([currency, pnl]) => {
            const sign = Number(pnl.abs) >= 0 ? "+" : "";
            return `${sign}${formatCurrency(pnl.abs, currency)} (${sign}${formatPercent(pnl.pct)})`;
          })
          .join(" · ");

  const firstPnlAbs =
    pnlEntries.length > 0 ? pnlEntries[0][1].abs : "0";

  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
      {/* 총평가액 카드 */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium text-muted-foreground">
            총평가액
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-2xl font-bold">{totalValueText}</p>
        </CardContent>
      </Card>

      {/* 총손익 카드 */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium text-muted-foreground">
            총손익
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className={`text-2xl font-bold ${PnlColorClass(firstPnlAbs)}`}>
            {pnlText}
          </p>
        </CardContent>
      </Card>

      {/* 메타 카드 */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium text-muted-foreground">
            갱신 정보
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            {formatRelativeTime(summary.lastPriceRefreshedAt)}
          </p>
          {summary.pendingCount > 0 && (
            <p
              className="mt-1 text-xs text-yellow-700"
              role="status"
              aria-live="polite"
            >
              현재가 대기 중 {summary.pendingCount}건
            </p>
          )}
          {summary.staleCount > 0 && (
            <p
              className="mt-1 text-xs text-orange-700"
              role="status"
              aria-live="polite"
            >
              지연 {summary.staleCount}건
            </p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
