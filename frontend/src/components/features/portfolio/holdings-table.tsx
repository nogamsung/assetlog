"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { formatCurrency, formatPercent, formatQuantity } from "@/lib/format";
import { PendingBadge } from "./pending-badge";
import { StaleBadge } from "./stale-badge";
import type { HoldingResponse } from "@/types/portfolio";

type SortKey = "latestValue" | "pnlAbs" | "weightPct";
type SortDir = "asc" | "desc";

interface HoldingsTableProps {
  holdings: HoldingResponse[];
}

function compareHoldings(a: HoldingResponse, b: HoldingResponse, key: SortKey, dir: SortDir): number {
  let aVal: number;
  let bVal: number;

  if (key === "latestValue") {
    aVal = a.latestValue !== null ? Number(a.latestValue) : -Infinity;
    bVal = b.latestValue !== null ? Number(b.latestValue) : -Infinity;
  } else if (key === "pnlAbs") {
    aVal = a.pnlAbs !== null ? Number(a.pnlAbs) : -Infinity;
    bVal = b.pnlAbs !== null ? Number(b.pnlAbs) : -Infinity;
  } else {
    aVal = a.weightPct;
    bVal = b.weightPct;
  }

  return dir === "desc" ? bVal - aVal : aVal - bVal;
}

function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      <p className="text-muted-foreground mb-4">보유 자산이 없습니다.</p>
      <Link
        href="/assets/new"
        className="inline-flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground shadow hover:bg-primary/90 transition-colors"
      >
        자산 추가하기
      </Link>
    </div>
  );
}

export function HoldingsTable({ holdings }: HoldingsTableProps) {
  const router = useRouter();
  const [sortKey, setSortKey] = useState<SortKey>("latestValue");
  const [sortDir, setSortDir] = useState<SortDir>("desc");

  if (holdings.length === 0) return <EmptyState />;

  function handleSort(key: SortKey) {
    if (key === sortKey) {
      setSortDir((prev) => (prev === "desc" ? "asc" : "desc"));
    } else {
      setSortKey(key);
      setSortDir("desc");
    }
  }

  const sorted = [...holdings].sort((a, b) => compareHoldings(a, b, sortKey, sortDir));

  function ariaSortAttr(key: SortKey): "ascending" | "descending" | "none" {
    if (sortKey !== key) return "none";
    return sortDir === "asc" ? "ascending" : "descending";
  }

  return (
    <div className="overflow-x-auto rounded-xl border bg-card">
      <table className="w-full text-sm">
        <caption className="sr-only">보유 자산 목록 — 열 헤더를 클릭하면 정렬됩니다</caption>
        <thead>
          <tr className="border-b text-left text-muted-foreground">
            <th scope="col" className="px-4 py-3 font-medium">심볼</th>
            <th scope="col" className="px-4 py-3 font-medium">종목명</th>
            <th scope="col" className="px-4 py-3 font-medium text-right">수량</th>
            <th scope="col" className="px-4 py-3 font-medium text-right">평균단가</th>
            <th scope="col" className="px-4 py-3 font-medium text-right">현재가</th>
            <th
              scope="col"
              className="cursor-pointer px-4 py-3 font-medium text-right hover:text-foreground transition-colors"
              aria-sort={ariaSortAttr("latestValue")}
              onClick={() => handleSort("latestValue")}
              onKeyDown={(e) => e.key === "Enter" && handleSort("latestValue")}
              tabIndex={0}
              role="columnheader"
            >
              평가액{sortKey === "latestValue" && (sortDir === "desc" ? " ▼" : " ▲")}
            </th>
            <th
              scope="col"
              className="cursor-pointer px-4 py-3 font-medium text-right hover:text-foreground transition-colors"
              aria-sort={ariaSortAttr("pnlAbs")}
              onClick={() => handleSort("pnlAbs")}
              onKeyDown={(e) => e.key === "Enter" && handleSort("pnlAbs")}
              tabIndex={0}
              role="columnheader"
            >
              손익{sortKey === "pnlAbs" && (sortDir === "desc" ? " ▼" : " ▲")}
            </th>
            <th
              scope="col"
              className="cursor-pointer px-4 py-3 font-medium text-right hover:text-foreground transition-colors"
              aria-sort={ariaSortAttr("weightPct")}
              onClick={() => handleSort("weightPct")}
              onKeyDown={(e) => e.key === "Enter" && handleSort("weightPct")}
              tabIndex={0}
              role="columnheader"
            >
              비중{sortKey === "weightPct" && (sortDir === "desc" ? " ▼" : " ▲")}
            </th>
          </tr>
        </thead>
        <tbody>
          {sorted.map((holding) => {
            const currency = holding.assetSymbol.currency;
            const pnlColorClass =
              holding.pnlAbs === null
                ? ""
                : Number(holding.pnlAbs) > 0
                  ? "text-green-600"
                  : Number(holding.pnlAbs) < 0
                    ? "text-destructive"
                    : "text-muted-foreground";

            return (
              <tr
                key={holding.userAssetId}
                className="border-b last:border-0 hover:bg-muted/30 transition-colors cursor-pointer"
                onClick={() => router.push("/assets")}
              >
                <td className="px-4 py-3 font-semibold">
                  {holding.assetSymbol.symbol}
                </td>
                <td className="px-4 py-3 text-muted-foreground">
                  {holding.assetSymbol.name}
                </td>
                <td className="px-4 py-3 text-right">
                  {formatQuantity(holding.quantity, holding.assetSymbol.assetType)}
                </td>
                <td className="px-4 py-3 text-right">
                  {formatCurrency(holding.avgCost, currency)}
                </td>
                <td className="px-4 py-3 text-right">
                  {holding.isPending ? (
                    <span className="text-muted-foreground">—</span>
                  ) : (
                    <span className="inline-flex items-center gap-1">
                      {holding.latestPrice !== null
                        ? formatCurrency(holding.latestPrice, currency)
                        : "—"}
                      {holding.isStale && <StaleBadge />}
                    </span>
                  )}
                </td>
                <td className="px-4 py-3 text-right">
                  {holding.isPending ? (
                    <span className="inline-flex items-center gap-1">
                      <span className="text-muted-foreground">—</span>
                      <PendingBadge />
                    </span>
                  ) : (
                    holding.latestValue !== null
                      ? formatCurrency(holding.latestValue, currency)
                      : "—"
                  )}
                </td>
                <td className={`px-4 py-3 text-right ${pnlColorClass}`}>
                  {holding.isPending ? (
                    <span className="text-muted-foreground">—</span>
                  ) : (
                    <span>
                      {holding.pnlAbs !== null
                        ? `${Number(holding.pnlAbs) >= 0 ? "+" : ""}${formatCurrency(holding.pnlAbs, currency)}`
                        : "—"}
                      {holding.pnlPct !== null && (
                        <span className="ml-1 text-xs">
                          ({Number(holding.pnlPct) >= 0 ? "+" : ""}{formatPercent(holding.pnlPct)})
                        </span>
                      )}
                    </span>
                  )}
                </td>
                <td className="px-4 py-3 text-right">
                  {holding.isPending ? (
                    <span className="text-muted-foreground">—</span>
                  ) : (
                    formatPercent(holding.weightPct)
                  )}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
