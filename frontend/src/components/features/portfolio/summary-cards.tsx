"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { formatCurrency, formatPercent, formatRelativeTime } from "@/lib/format";
import type { PortfolioSummary } from "@/types/portfolio";

interface SummaryCardsProps {
  summary: PortfolioSummary;
}

function PnlColorClass(abs: string): string {
  const n = Number(abs);
  if (n > 0) return "text-green-600 dark:text-green-400";
  if (n < 0) return "text-destructive";
  return "text-muted-foreground";
}

export function SummaryCards({ summary }: SummaryCardsProps) {
  const { displayCurrency } = summary;
  const hasConversion = displayCurrency !== null;

  const totalValueEntries = Object.entries(summary.totalValueByCurrency);
  const pnlEntries = Object.entries(summary.pnlByCurrency);
  const realizedEntries = Object.entries(summary.realizedPnlByCurrency);

  // ── 총평가액 ──────────────────────────────────────────────────────────────
  const perCurrencyTotalText =
    totalValueEntries.length === 0
      ? "—"
      : totalValueEntries
          .map(([currency, amount]) => formatCurrency(amount, currency))
          .join(" · ");

  const totalValueMain =
    hasConversion && summary.convertedTotalValue !== null
      ? formatCurrency(summary.convertedTotalValue, displayCurrency)
      : perCurrencyTotalText;

  const totalValueSub =
    hasConversion && summary.convertedTotalValue !== null
      ? perCurrencyTotalText
      : null;

  // ── 미실현 손익 ──────────────────────────────────────────────────────────
  const perCurrencyPnlText =
    pnlEntries.length === 0
      ? "—"
      : pnlEntries
          .map(([currency, pnl]) => {
            const sign = Number(pnl.abs) >= 0 ? "+" : "";
            return `${sign}${formatCurrency(pnl.abs, currency)} (${sign}${formatPercent(pnl.pct)})`;
          })
          .join(" · ");

  const pnlMain =
    hasConversion && summary.convertedPnlAbs !== null
      ? (() => {
          const sign = Number(summary.convertedPnlAbs) >= 0 ? "+" : "";
          return `${sign}${formatCurrency(summary.convertedPnlAbs, displayCurrency)}`;
        })()
      : perCurrencyPnlText;

  const pnlSub =
    hasConversion && summary.convertedPnlAbs !== null
      ? perCurrencyPnlText
      : null;

  const firstPnlAbs =
    hasConversion && summary.convertedPnlAbs !== null
      ? summary.convertedPnlAbs
      : pnlEntries.length > 0
        ? pnlEntries[0][1].abs
        : "0";

  // ── 실현 손익 ────────────────────────────────────────────────────────────
  const perCurrencyRealizedText =
    realizedEntries.length === 0
      ? "—"
      : realizedEntries
          .map(([currency, amount]) => {
            const sign = Number(amount) > 0 ? "+" : "";
            return `${sign}${formatCurrency(amount, currency)}`;
          })
          .join(" · ");

  const realizedMain =
    hasConversion && summary.convertedRealizedPnl !== null
      ? (() => {
          const sign = Number(summary.convertedRealizedPnl) > 0 ? "+" : "";
          return `${sign}${formatCurrency(summary.convertedRealizedPnl, displayCurrency)}`;
        })()
      : perCurrencyRealizedText;

  const realizedSub =
    hasConversion && summary.convertedRealizedPnl !== null
      ? perCurrencyRealizedText
      : null;

  const firstRealizedAbs =
    hasConversion && summary.convertedRealizedPnl !== null
      ? summary.convertedRealizedPnl
      : realizedEntries.length > 0
        ? realizedEntries[0][1]
        : "0";

  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
      {/* 총평가액 카드 */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium text-muted-foreground">
            총평가액
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-2xl font-bold">{totalValueMain}</p>
          {totalValueSub !== null && (
            <p className="mt-1 text-xs text-muted-foreground">{totalValueSub}</p>
          )}
        </CardContent>
      </Card>

      {/* 미실현 손익 카드 */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium text-muted-foreground">
            미실현 손익
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className={`text-2xl font-bold ${PnlColorClass(firstPnlAbs)}`}>
            {pnlMain}
          </p>
          {pnlSub !== null && (
            <p className="mt-1 text-xs text-muted-foreground">{pnlSub}</p>
          )}
        </CardContent>
      </Card>

      {/* 실현 손익 카드 */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium text-muted-foreground">
            실현 손익
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className={`text-2xl font-bold ${PnlColorClass(firstRealizedAbs)}`}>
            {realizedMain}
          </p>
          {realizedSub !== null && (
            <p className="mt-1 text-xs text-muted-foreground">{realizedSub}</p>
          )}
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
