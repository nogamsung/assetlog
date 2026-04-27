"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { formatCurrency, formatCompactCurrency, formatPercent, formatRelativeTime, pnlColor } from "@/lib/format"; /* MODIFIED */
import { tossHeroNumber, tossCardNumber } from "@/lib/toss-tokens"; /* ADDED */
import { cn } from "@/lib/utils"; /* ADDED */
import type { PortfolioSummary } from "@/types/portfolio";

interface SummaryCardsProps {
  summary: PortfolioSummary;
}

/** Use compact currency when value (in KRW equivalent approx) is large — ADDED */
function shouldCompact(amount: string, currency: string): boolean {
  const n = Math.abs(Number(amount));
  if (currency === "KRW" || currency === "JPY") return n >= 1e8;
  return n >= 1e6;
}

function formatDisplay(amount: string, currency: string): string {
  if (shouldCompact(amount, currency)) {
    return formatCompactCurrency(amount, currency);
  }
  return formatCurrency(amount, currency);
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
      ? formatDisplay(summary.convertedTotalValue, displayCurrency)
      : totalValueEntries.length === 1
        ? formatDisplay(totalValueEntries[0][1], totalValueEntries[0][0])
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

  // ── 현금 합계 ─────────────────────────────────────────────────────────────
  const cashEntries = Object.entries(summary.cashTotalByCurrency);
  const hasCash = cashEntries.length > 0;

  return (
    <div className="space-y-4"> {/* MODIFIED: vertical layout instead of grid for hero card */}

      {/* MODIFIED: Hero card — 총평가액 with big number */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium text-toss-textWeak"> {/* MODIFIED */}
            총평가액
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className={cn(tossHeroNumber)}>{totalValueMain}</p> {/* MODIFIED: hero number */}
          {totalValueSub !== null && (
            <p className="mt-1 text-xs text-toss-textWeak">{totalValueSub}</p>
          )}
        </CardContent>
      </Card>

      {/* MODIFIED: Sub cards — 2 or 3 column grid */}
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-3">
        {/* 미실현 손익 카드 */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-toss-textWeak"> {/* MODIFIED */}
              미실현 손익
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className={cn(tossCardNumber, pnlColor(firstPnlAbs))}> {/* MODIFIED: pnlColor + tossCardNumber */}
              {pnlMain}
            </p>
            {pnlSub !== null && (
              <p className="mt-1 text-xs text-toss-textWeak">{pnlSub}</p>
            )}
          </CardContent>
        </Card>

        {/* 실현 손익 카드 */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-toss-textWeak"> {/* MODIFIED */}
              실현 손익
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className={cn(tossCardNumber, pnlColor(firstRealizedAbs))}> {/* MODIFIED: pnlColor */}
              {realizedMain}
            </p>
            {realizedSub !== null && (
              <p className="mt-1 text-xs text-toss-textWeak">{realizedSub}</p>
            )}
          </CardContent>
        </Card>

        {/* 현금 카드 */}
        {hasCash && (
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-toss-textWeak"> {/* MODIFIED */}
                현금
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-1">
                {cashEntries.map(([currency, amount]) => (
                  <p key={currency} className="text-sm font-medium text-toss-text"> {/* MODIFIED */}
                    <span className="text-xs text-toss-textWeak mr-1"> {/* MODIFIED */}
                      {currency}
                    </span>
                    {formatCurrency(amount, currency)}
                  </p>
                ))}
              </div>
            </CardContent>
          </Card>
        )}

        {/* 메타 카드 */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-toss-textWeak"> {/* MODIFIED */}
              갱신 정보
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-toss-textWeak"> {/* MODIFIED */}
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
    </div>
  );
}
