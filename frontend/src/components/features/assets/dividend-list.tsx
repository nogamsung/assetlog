"use client";

import { useDividendsBySymbol } from "@/hooks/use-dividends";
import { formatCurrency } from "@/lib/format";

interface DividendListProps {
  assetSymbolId: number;
}

export function DividendList({ assetSymbolId }: DividendListProps) {
  const { data, isLoading, isError } = useDividendsBySymbol(assetSymbolId);

  if (isLoading) {
    return (
      <div
        role="status"
        aria-label="배당 내역 로딩 중"
        className="h-16 rounded-md bg-muted/40 animate-pulse"
      />
    );
  }

  if (isError) {
    return (
      <p role="alert" className="text-sm text-destructive">
        배당 내역을 불러오지 못했습니다.
      </p>
    );
  }

  const dividends = data?.dividends ?? [];
  const summary = data?.summary[0];

  if (dividends.length === 0) {
    return (
      <p className="text-sm text-muted-foreground">아직 받은 배당이 없습니다.</p>
    );
  }

  return (
    <div className="space-y-3">
      {summary && (
        <div className="rounded-md border bg-muted/20 px-3 py-2 text-sm">
          <span className="text-muted-foreground">누적 배당</span>{" "}
          <span className="font-semibold">
            {formatCurrency(summary.totalAmount, summary.currency)}
          </span>
        </div>
      )}
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b text-left text-xs uppercase text-muted-foreground">
              <th className="py-2 pr-4 font-medium">배당락일</th>
              <th className="py-2 pr-4 font-medium">지급일</th>
              <th className="py-2 text-right font-medium">금액</th>
            </tr>
          </thead>
          <tbody>
            {dividends.map((d) => (
              <tr key={d.id} className="border-b last:border-0">
                <td className="py-2 pr-4">{d.exDate}</td>
                <td className="py-2 pr-4 text-muted-foreground">
                  {d.payDate ?? "—"}
                </td>
                <td className="py-2 text-right font-medium">
                  {formatCurrency(d.amount, d.currency)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
