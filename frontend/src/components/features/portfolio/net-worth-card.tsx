"use client";

import { useNetWorth } from "@/hooks/use-net-worth";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { formatCurrency } from "@/lib/format";

interface NetWorthCardProps {
  displayCurrency?: string;
}

const ACCOUNT_LABELS: Record<string, string> = {
  toss_securities: "토스증권",
  shinhan: "신한투자증권",
  upbit: "업비트",
  bithumb: "빗썸",
  binance: "바이낸스",
  kis: "한국투자증권",
  manual: "수동 입력",
};

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
              총 평가액 ({data.displayCurrency})
            </p>
            <p className="mt-1 text-2xl font-bold text-toss-textStrong tabular-nums">
              {formatCurrency(data.convertedTotal, data.displayCurrency)}
            </p>
            <p className="mt-1 text-[11px] text-toss-textWeak">
              보유자산 + 모든 계좌 현금
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

        {Object.keys(data.byAccount).length > 0 && (
          <div className="space-y-2">
            <p className="text-xs font-medium text-toss-textWeak">
              계좌별 현금 잔액
            </p>
            <div className="overflow-x-auto rounded-md border">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b bg-muted/30 text-left text-xs uppercase text-muted-foreground">
                    <th className="px-3 py-2 font-medium">계좌</th>
                    <th className="px-3 py-2 text-right font-medium">잔액</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(data.byAccount)
                    .sort(([a], [b]) => a.localeCompare(b))
                    .flatMap(([source, ccyMap]) =>
                      Object.entries(ccyMap)
                        .sort(([a], [b]) => a.localeCompare(b))
                        .map(([ccy, amount]) => (
                          <tr
                            key={`${source}-${ccy}`}
                            className="border-b last:border-0"
                          >
                            <td className="px-3 py-2">
                              <span className="font-medium">
                                {ACCOUNT_LABELS[source] ?? source}
                              </span>
                              <span className="ml-2 rounded bg-muted px-1.5 py-0.5 text-xs text-muted-foreground">
                                {ccy}
                              </span>
                            </td>
                            <td className="px-3 py-2 text-right tabular-nums font-medium">
                              {formatCurrency(amount, ccy)}
                            </td>
                          </tr>
                        )),
                    )}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
