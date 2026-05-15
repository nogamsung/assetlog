"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { useAllTransactions } from "@/hooks/use-transactions";
import { useAllCashTransactions } from "@/hooks/use-cash-accounts";
import { formatCurrency, formatQuantity, pnlColor } from "@/lib/format";
import { formatDateTimeKST } from "@/lib/datetime";
import type { TransactionWithSymbolResponse } from "@/types/transaction";

type AssetGroup = "kr_stock" | "us_stock" | "crypto";

const GROUP_LABELS: Record<AssetGroup, string> = {
  kr_stock: "국내주식",
  us_stock: "해외주식",
  crypto: "암호화폐",
};

const SOURCE_LABELS: Record<string, string> = {
  toss_investment: "토스증권",
  shinhan_investment: "신한투자증권",
  k_bank: "케이뱅크",
  upbit: "업비트",
  bithumb: "빗썸",
  binance: "바이낸스",
  kis: "한국투자증권",
  manual: "수동 입력",
};

function sourceLabel(s: string | null | undefined): string {
  if (!s) return "수동 입력";
  return SOURCE_LABELS[s] ?? s;
}

type Filter = "all" | "buy" | "sell" | "deposit" | "withdraw";

const FILTERS: { value: Filter; label: string }[] = [
  { value: "all", label: "전체" },
  { value: "buy", label: "매수" },
  { value: "sell", label: "매도" },
  { value: "deposit", label: "입금" },
  { value: "withdraw", label: "출금" },
];

export function HistoryView() {
  const tradesQ = useAllTransactions();
  const cashQ = useAllCashTransactions();

  const [filter, setFilter] = useState<Filter>("all");

  const trades = tradesQ.data ?? [];
  const cashRows = cashQ.data ?? [];

  // Group trades by asset_type. Cash rows go into their own bucket below.
  const tradesByGroup = useMemo(() => {
    const m = new Map<AssetGroup, TransactionWithSymbolResponse[]>();
    for (const t of trades) {
      if (filter === "buy" && t.type !== "buy") continue;
      if (filter === "sell" && t.type !== "sell") continue;
      if (filter === "deposit" || filter === "withdraw") continue;
      const g = t.assetType as AssetGroup;
      const list = m.get(g) ?? [];
      list.push(t);
      m.set(g, list);
    }
    return m;
  }, [trades, filter]);

  const cashFiltered = useMemo(() => {
    if (filter === "buy" || filter === "sell") return [];
    return cashRows.filter((c) => {
      if (filter === "deposit") return c.kind === "deposit";
      if (filter === "withdraw") return c.kind === "withdraw";
      return c.kind === "deposit" || c.kind === "withdraw";
    });
  }, [cashRows, filter]);

  if (tradesQ.isLoading || cashQ.isLoading) {
    return (
      <div
        role="status"
        aria-label="거래 내역 로딩 중"
        className="h-32 rounded-md bg-muted/40 animate-pulse"
      />
    );
  }

  const isEmpty =
    Array.from(tradesByGroup.values()).every((v) => v.length === 0) &&
    cashFiltered.length === 0;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap gap-2" role="group" aria-label="유형 필터">
        {FILTERS.map((f) => (
          <button
            key={f.value}
            type="button"
            aria-pressed={filter === f.value}
            onClick={() => setFilter(f.value)}
            className={`rounded-full px-3 py-1.5 text-xs font-medium transition-colors ${
              filter === f.value
                ? "bg-primary text-primary-foreground"
                : "bg-muted text-foreground hover:bg-muted/70"
            }`}
          >
            {f.label}
          </button>
        ))}
      </div>

      {isEmpty && (
        <p className="py-12 text-center text-sm text-muted-foreground">
          표시할 거래 내역이 없습니다.
        </p>
      )}

      {(["kr_stock", "us_stock", "crypto"] as AssetGroup[]).map((g) => {
        const rows = tradesByGroup.get(g) ?? [];
        if (rows.length === 0) return null;
        return (
          <section key={g} aria-label={`${GROUP_LABELS[g]} 거래 내역`} className="space-y-2">
            <div className="flex items-baseline justify-between px-1">
              <h2 className="text-sm font-bold text-toss-textStrong">
                {GROUP_LABELS[g]}
              </h2>
              <span className="text-xs text-muted-foreground">{rows.length}건</span>
            </div>
            <div className="overflow-x-auto rounded-2xl border border-toss-border bg-toss-card">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b text-left text-xs uppercase tracking-wide text-muted-foreground">
                    <th scope="col" className="px-4 py-2 font-medium">일시</th>
                    <th scope="col" className="px-4 py-2 font-medium">종목</th>
                    <th scope="col" className="px-4 py-2 font-medium">유형</th>
                    <th scope="col" className="px-4 py-2 text-right font-medium tabular-nums">수량</th>
                    <th scope="col" className="px-4 py-2 text-right font-medium tabular-nums">단가</th>
                    <th scope="col" className="px-4 py-2 text-right font-medium tabular-nums">금액</th>
                    <th scope="col" className="px-4 py-2 font-medium">출처</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((t) => {
                    const gross = Number(t.quantity) * Number(t.price);
                    return (
                      <tr
                        key={t.id}
                        className="border-b last:border-0 hover:bg-muted/30 transition-colors"
                      >
                        <td className="px-4 py-2 whitespace-nowrap text-xs text-muted-foreground">
                          {formatDateTimeKST(t.tradedAt)}
                        </td>
                        <td className="px-4 py-2">
                          <Link
                            href={`/assets/${t.userAssetId}`}
                            className="hover:text-toss-blue transition-colors"
                          >
                            <p className="font-medium">{t.symbol}</p>
                            {t.name && (
                              <p className="text-xs text-muted-foreground truncate max-w-[200px]">
                                {t.name}
                              </p>
                            )}
                          </Link>
                        </td>
                        <td className="px-4 py-2">
                          <span
                            className={`inline-flex rounded-full px-2 py-0.5 text-xs font-semibold ${
                              t.type === "buy"
                                ? "bg-toss-up/10 text-toss-up"
                                : "bg-toss-down/10 text-toss-down"
                            }`}
                          >
                            {t.type === "buy" ? "매수" : "매도"}
                          </span>
                        </td>
                        <td className="px-4 py-2 text-right tabular-nums">
                          {formatQuantity(t.quantity, t.assetType)}
                        </td>
                        <td className="px-4 py-2 text-right tabular-nums">
                          {formatCurrency(t.price, t.currency)}
                        </td>
                        <td
                          className={`px-4 py-2 text-right tabular-nums font-medium ${pnlColor(
                            t.type === "sell" ? gross : -gross,
                          )}`}
                        >
                          {t.type === "sell" ? "+" : "−"}
                          {formatCurrency(String(gross), t.currency)}
                        </td>
                        <td className="px-4 py-2 text-xs text-muted-foreground">
                          {sourceLabel(t.externalSource)}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </section>
        );
      })}

      {cashFiltered.length > 0 && (
        <section aria-label="현금 입출금 내역" className="space-y-2">
          <div className="flex items-baseline justify-between px-1">
            <h2 className="text-sm font-bold text-toss-textStrong">현금 입출금</h2>
            <span className="text-xs text-muted-foreground">{cashFiltered.length}건</span>
          </div>
          <div className="overflow-x-auto rounded-2xl border border-toss-border bg-toss-card">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b text-left text-xs uppercase tracking-wide text-muted-foreground">
                  <th scope="col" className="px-4 py-2 font-medium">일시</th>
                  <th scope="col" className="px-4 py-2 font-medium">유형</th>
                  <th scope="col" className="px-4 py-2 text-right font-medium tabular-nums">금액</th>
                  <th scope="col" className="px-4 py-2 font-medium">출처</th>
                </tr>
              </thead>
              <tbody>
                {cashFiltered.map((c) => (
                  <tr key={c.id} className="border-b last:border-0 hover:bg-muted/30">
                    <td className="px-4 py-2 whitespace-nowrap text-xs text-muted-foreground">
                      {formatDateTimeKST(c.tradedAt)}
                    </td>
                    <td className="px-4 py-2">
                      <span
                        className={`inline-flex rounded-full px-2 py-0.5 text-xs font-semibold ${
                          c.kind === "deposit"
                            ? "bg-toss-up/10 text-toss-up"
                            : "bg-toss-down/10 text-toss-down"
                        }`}
                      >
                        {c.kind === "deposit" ? "입금" : "출금"}
                      </span>
                    </td>
                    <td
                      className={`px-4 py-2 text-right tabular-nums font-medium ${pnlColor(
                        c.kind === "deposit" ? Number(c.amount) : -Number(c.amount),
                      )}`}
                    >
                      {c.kind === "deposit" ? "+" : "−"}
                      {formatCurrency(c.amount, c.currency)}
                    </td>
                    <td className="px-4 py-2 text-xs text-muted-foreground">
                      {sourceLabel(c.externalSource)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}
    </div>
  );
}
