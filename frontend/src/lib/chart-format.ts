import { format } from "date-fns";
import { ko } from "date-fns/locale";
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

export function formatCurrencyValue(value: unknown, currency: string): string {
  const num = typeof value === "number" ? value : Number(value);
  return new Intl.NumberFormat("ko-KR", {
    style: "currency",
    currency,
    maximumFractionDigits: 0,
  }).format(num);
}

export function formatTooltipLabel(label: unknown): string {
  const d = label instanceof Date ? label : new Date(label as string);
  return format(d, "yyyy년 M월 d일 HH:mm", { locale: ko });
}
