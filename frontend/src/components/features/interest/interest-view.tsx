"use client";

import { useInterestTransactions } from "@/hooks/use-cash-accounts";
import { formatCurrency } from "@/lib/format";

const SOURCE_LABELS: Record<string, string> = {
  toss_investment: "토스증권",
  shinhan_investment: "신한증권",
  k_bank: "케이뱅크",
  upbit: "업비트",
  bithumb: "빗썸",
  binance: "바이낸스",
  kis: "한국투자증권",
  manual: "수동 입력",
};

function formatSource(s: string | null | undefined): string {
  if (!s) return "—";
  return SOURCE_LABELS[s] ?? s;
}

function totalsByCurrency(
  rows: { amount: string; currency: string }[],
): Record<string, number> {
  const acc: Record<string, number> = {};
  for (const r of rows) {
    acc[r.currency] = (acc[r.currency] ?? 0) + Number(r.amount);
  }
  return acc;
}

function formatDate(iso: string): string {
  return iso.slice(0, 10);
}

export function InterestView() {
  const { data, isLoading, isError } = useInterestTransactions();

  if (isLoading) {
    return (
      <div
        role="status"
        aria-label="이자 내역 로딩 중"
        className="h-32 rounded-md bg-muted/40 animate-pulse"
      />
    );
  }
  if (isError) {
    return (
      <p role="alert" className="text-sm text-destructive">
        이자 내역을 불러오지 못했습니다.
      </p>
    );
  }

  const rows = data ?? [];
  const totals = totalsByCurrency(rows);

  if (rows.length === 0) {
    return (
      <p className="text-sm text-muted-foreground">아직 받은 이자가 없습니다.</p>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-2">
        {Object.entries(totals).map(([currency, total]) => (
          <div
            key={currency}
            className="rounded-md border bg-muted/20 px-3 py-2 text-sm"
          >
            <span className="text-muted-foreground">누적 이자 ({currency})</span>{" "}
            <span className="font-semibold">
              {formatCurrency(total.toString(), currency)}
            </span>
          </div>
        ))}
      </div>
      <div className="overflow-x-auto rounded-md border">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b bg-muted/30 text-left text-xs uppercase text-muted-foreground">
              <th className="px-3 py-2 font-medium">날짜</th>
              <th className="px-3 py-2 font-medium">통화</th>
              <th className="px-3 py-2 text-right font-medium">금액</th>
              <th className="px-3 py-2 font-medium">출처</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.id} className="border-b last:border-0">
                <td className="px-3 py-2">{formatDate(r.tradedAt)}</td>
                <td className="px-3 py-2">{r.currency}</td>
                <td className="px-3 py-2 text-right font-medium">
                  {formatCurrency(r.amount, r.currency)}
                </td>
                <td className="px-3 py-2 text-muted-foreground">
                  {formatSource(r.externalSource)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
