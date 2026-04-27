import { format } from "date-fns";
import { ko } from "date-fns/locale";
import { formatCurrency } from "@/lib/format"; /* ADDED */
import type { HistoryPeriod } from "@/types/portfolio-history";

export function formatTimestamp(date: Date, period: HistoryPeriod): string {
  if (period === "1D") return format(date, "HH:mm", { locale: ko });
  if (period === "1W") return format(date, "M/d", { locale: ko });
  if (period === "1M") return format(date, "M/d", { locale: ko });
  if (period === "1Y") return format(date, "yy/MM", { locale: ko });
  return format(date, "yyyy/MM", { locale: ko });
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

export function formatTooltipLabel(label: unknown): string {
  const d = label instanceof Date ? label : new Date(label as string);
  return format(d, "yyyy년 M월 d일 HH:mm", { locale: ko });
}
