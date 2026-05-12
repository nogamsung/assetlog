import { formatCurrency } from "@/lib/format"; /* ADDED */
import { formatChartTickKST } from "@/lib/datetime"; /* ADDED */
import type { HistoryPeriod } from "@/types/portfolio-history";

export function formatTimestamp(date: Date, period: HistoryPeriod): string { /* MODIFIED: KST via formatChartTickKST */
  if (period === "1D") return formatChartTickKST(date, "HH:mm");
  if (period === "1W") return formatChartTickKST(date, "M/d");
  if (period === "1M") return formatChartTickKST(date, "M/d");
  if (period === "1Y") return formatChartTickKST(date, "yy/MM");
  return formatChartTickKST(date, "yyyy/MM");
}

export function formatCompactNumber(value: number): string {
  return new Intl.NumberFormat("ko-KR", {
    notation: "compact",
    maximumFractionDigits: 1,
  }).format(value);
}

/* MODIFIED: delegates to unified formatCurrency with category rules */
export function formatCurrencyValue(value: unknown, currency: string): string {
  const str = typeof value === "number" ? String(value) : String(value ?? 0);
  return formatCurrency(str, currency);
}

export function formatTooltipLabel(label: unknown): string { /* MODIFIED: KST */
  const d = label instanceof Date ? label : new Date(label as string);
  const year = formatChartTickKST(d, "yyyy");
  const month = formatChartTickKST(d, "M");
  const day = formatChartTickKST(d, "d");
  const time = formatChartTickKST(d, "HH:mm");
  return `${year}년 ${month}월 ${day}일 ${time}`;
}
