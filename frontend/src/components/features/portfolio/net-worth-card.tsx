"use client";

import { useNetWorth } from "@/hooks/use-net-worth";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { formatCurrency } from "@/lib/format";

interface NetWorthCardProps {
  displayCurrency?: string;
}

export function NetWorthCard({ displayCurrency }: NetWorthCardProps) {
  const { data, isLoading, isError } = useNetWorth(displayCurrency);

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-base">총 재산</CardTitle>
        </CardHeader>
        <CardContent>
          <div
            role="status"
            aria-label="총 재산 로딩 중"
            className="h-24 rounded-md bg-muted/40 animate-pulse"
          />
        </CardContent>
      </Card>
    );
  }
  if (isError || !data) return null;

  const currencies = Object.keys(data.byCurrency).sort();
  const hasData = currencies.length > 0;
  if (!hasData) return null;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">총 재산</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {data.convertedTotal !== null && data.displayCurrency && (
          <div className="rounded-xl border bg-toss-card px-4 py-3">
            <p className="text-xs text-toss-textWeak">
              합계 ({data.displayCurrency})
            </p>
            <p className="mt-1 text-2xl font-bold text-toss-textStrong tabular-nums">
              {formatCurrency(data.convertedTotal, data.displayCurrency)}
            </p>
          </div>
        )}
        <div className="overflow-x-auto rounded-md border">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b bg-muted/30 text-left text-xs uppercase text-muted-foreground">
                <th className="px-3 py-2 font-medium">통화</th>
                <th className="px-3 py-2 text-right font-medium">현금</th>
                <th className="px-3 py-2 text-right font-medium">자산 평가액</th>
                <th className="px-3 py-2 text-right font-medium">소계</th>
              </tr>
            </thead>
            <tbody>
              {currencies.map((cur) => {
                const e = data.byCurrency[cur];
                return (
                  <tr key={cur} className="border-b last:border-0">
                    <td className="px-3 py-2 font-medium">{cur}</td>
                    <td className="px-3 py-2 text-right tabular-nums">
                      {formatCurrency(e.cash, cur)}
                    </td>
                    <td className="px-3 py-2 text-right tabular-nums">
                      {formatCurrency(e.assets, cur)}
                    </td>
                    <td className="px-3 py-2 text-right font-semibold tabular-nums">
                      {formatCurrency(e.total, cur)}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </CardContent>
    </Card>
  );
}
