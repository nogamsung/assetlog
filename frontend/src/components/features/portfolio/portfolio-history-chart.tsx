"use client";

import { useState } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { format } from "date-fns";
import { ko } from "date-fns/locale";
import { usePortfolioHistory } from "@/hooks/use-portfolio-history";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { HistoryPeriod } from "@/types/portfolio-history";

const PERIODS: { label: string; value: HistoryPeriod }[] = [
  { label: "1일", value: "1D" },
  { label: "1주", value: "1W" },
  { label: "1개월", value: "1M" },
  { label: "1년", value: "1Y" },
  { label: "전체", value: "ALL" },
];

function formatTimestamp(date: Date, period: HistoryPeriod): string {
  if (period === "1D") return format(date, "HH:mm", { locale: ko });
  if (period === "1W") return format(date, "M/d", { locale: ko });
  if (period === "1M") return format(date, "M/d", { locale: ko });
  if (period === "1Y") return format(date, "yy/MM", { locale: ko });
  return format(date, "yyyy/MM", { locale: ko });
}

function ChartSkeleton() {
  return (
    <div
      className="h-64 rounded-lg bg-muted/40 animate-pulse"
      role="status"
      aria-label="차트 로딩 중"
    />
  );
}

function ChartEmpty() {
  return (
    <div className="flex h-64 items-center justify-center">
      <p className="text-sm text-muted-foreground">
        해당 기간에 데이터가 없습니다.
      </p>
    </div>
  );
}

function ChartError({ message }: { message: string }) {
  return (
    <div
      className="flex h-64 items-center justify-center"
      role="alert"
    >
      <p className="text-sm text-destructive">{message}</p>
    </div>
  );
}

interface PortfolioHistoryChartProps {
  currency: string;
}

export function PortfolioHistoryChart({ currency }: PortfolioHistoryChartProps) {
  const [period, setPeriod] = useState<HistoryPeriod>("1M");

  const { data, isLoading, isError, error } = usePortfolioHistory({
    period,
    currency,
  });

  const chartData =
    data?.points.map((p) => ({
      timestamp: p.timestamp,
      value: Number(p.value),
      costBasis: Number(p.costBasis),
    })) ?? [];

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between flex-wrap gap-2">
          <CardTitle className="text-base">포트폴리오 추이 ({currency})</CardTitle>
          <div
            className="flex gap-1"
            role="group"
            aria-label="차트 기간 선택"
          >
            {PERIODS.map((p) => (
              <button
                key={p.value}
                type="button"
                onClick={() => setPeriod(p.value)}
                aria-label={`${p.label} 기간 선택`}
                aria-pressed={period === p.value}
                className={`rounded px-3 py-1 text-xs font-medium transition-colors ${
                  period === p.value
                    ? "bg-primary text-primary-foreground"
                    : "bg-muted text-muted-foreground hover:bg-muted/80"
                }`}
              >
                {p.label}
              </button>
            ))}
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <div
          role="img"
          aria-label="포트폴리오 시계열 차트"
        >
          {isLoading && <ChartSkeleton />}
          {isError && (
            <ChartError
              message={error?.message ?? "차트 데이터를 불러오지 못했습니다."}
            />
          )}
          {!isLoading && !isError && chartData.length === 0 && <ChartEmpty />}
          {!isLoading && !isError && chartData.length > 0 && (
            <ResponsiveContainer width="100%" height={256}>
              <LineChart
                data={chartData}
                margin={{ top: 8, right: 8, left: 8, bottom: 8 }}
              >
                <XAxis
                  dataKey="timestamp"
                  tickFormatter={(val: Date) => formatTimestamp(val, period)}
                  tick={{ fontSize: 11 }}
                  tickLine={false}
                  axisLine={false}
                />
                <YAxis
                  tick={{ fontSize: 11 }}
                  tickLine={false}
                  axisLine={false}
                  tickFormatter={(val: number) =>
                    new Intl.NumberFormat("ko-KR", {
                      notation: "compact",
                      maximumFractionDigits: 1,
                    }).format(val)
                  }
                  width={60}
                />
                <Tooltip
                  formatter={(val: unknown) => {
                    const num = typeof val === "number" ? val : Number(val);
                    return new Intl.NumberFormat("ko-KR", {
                      style: "currency",
                      currency,
                      maximumFractionDigits: 0,
                    }).format(num);
                  }}
                  labelFormatter={(label: unknown) => {
                    const d = label instanceof Date ? label : new Date(label as string);
                    return format(d, "yyyy년 M월 d일 HH:mm", { locale: ko });
                  }}
                />
                <Line
                  type="monotone"
                  dataKey="value"
                  name="평가액"
                  stroke="#2563eb"
                  strokeWidth={2}
                  dot={false}
                  activeDot={{ r: 4 }}
                />
              </LineChart>
            </ResponsiveContainer>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
