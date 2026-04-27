"use client";

/**
 * HoldingsList — mobile card list (block sm:hidden).
 * Toss list pattern: circular icon left, big number right, PnL below.
 */

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { formatCurrency, formatPercent, pnlColor } from "@/lib/format";
import { tossCardNumber } from "@/lib/toss-tokens";
import { cn } from "@/lib/utils";
import type { HoldingResponse } from "@/types/portfolio";

type SortKey = "latestValue" | "pnlAbs" | "weightPct";
type SortDir = "asc" | "desc";

const SORT_LABELS: Record<SortKey, string> = {
  latestValue: "평가액",
  pnlAbs: "손익",
  weightPct: "비중",
};

interface HoldingsListProps {
  holdings: HoldingResponse[];
}

function displayValue(h: HoldingResponse, kind: "latestValue" | "pnlAbs"): string | null {
  if (h.displayCurrency !== null) {
    return kind === "latestValue" ? h.convertedLatestValue : h.convertedPnlAbs;
  }
  return kind === "latestValue" ? h.latestValue : h.pnlAbs;
}

function compareHoldings(a: HoldingResponse, b: HoldingResponse, key: SortKey, dir: SortDir): number {
  let aVal: number;
  let bVal: number;
  if (key === "latestValue") {
    aVal = Number(displayValue(a, "latestValue") ?? "-Infinity");
    bVal = Number(displayValue(b, "latestValue") ?? "-Infinity");
  } else if (key === "pnlAbs") {
    aVal = Number(displayValue(a, "pnlAbs") ?? "-Infinity");
    bVal = Number(displayValue(b, "pnlAbs") ?? "-Infinity");
  } else {
    aVal = a.weightPct;
    bVal = b.weightPct;
  }
  return dir === "desc" ? bVal - aVal : aVal - bVal;
}

function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      <p className="text-toss-textWeak text-base font-medium mb-2">보유 자산이 없습니다.</p>
      <p className="text-toss-textDisabled text-sm mb-4">첫 번째 자산을 추가해보세요.</p>
      <Link
        href="/assets/new"
        className="inline-flex items-center gap-2 rounded-xl bg-toss-blue px-5 h-11 text-sm font-bold text-white active:scale-[0.98] transition-transform"
      >
        자산 추가하기
      </Link>
    </div>
  );
}

/** Two-letter abbreviation for circular icon — ADDED */
function symbolAbbr(symbol: string): string {
  return symbol.slice(0, 2).toUpperCase();
}

export function HoldingsList({ holdings }: HoldingsListProps) {
  const router = useRouter();
  const [sortKey, setSortKey] = useState<SortKey>("latestValue");
  const [sortDir, setSortDir] = useState<SortDir>("desc");
  const [sortOpen, setSortOpen] = useState(false);

  if (holdings.length === 0) return <EmptyState />;

  const sorted = [...holdings].sort((a, b) => compareHoldings(a, b, sortKey, sortDir));

  function selectSort(key: SortKey) {
    if (key === sortKey) {
      setSortDir((prev) => (prev === "desc" ? "asc" : "desc"));
    } else {
      setSortKey(key);
      setSortDir("desc");
    }
    setSortOpen(false);
  }

  return (
    <div className="block sm:hidden space-y-2"> {/* ADDED: block sm:hidden */}
      {/* Sort dropdown */}
      <div className="relative flex justify-end">
        <button
          type="button"
          onClick={() => setSortOpen((prev) => !prev)}
          aria-label="정렬 기준 변경"
          aria-expanded={sortOpen}
          className="inline-flex items-center gap-1 rounded-xl border border-toss-border bg-toss-card px-3 h-9 text-sm text-toss-textWeak active:scale-[0.98] transition-transform"
        >
          {SORT_LABELS[sortKey]} {sortDir === "desc" ? "▼" : "▲"}
        </button>
        {sortOpen && (
          <div className="absolute right-0 top-10 z-20 rounded-xl border border-toss-border bg-toss-bg shadow-2xl overflow-hidden">
            {(Object.keys(SORT_LABELS) as SortKey[]).map((key) => (
              <button
                key={key}
                type="button"
                onClick={() => selectSort(key)}
                className={cn(
                  "block w-full px-4 py-3 text-left text-sm transition-colors",
                  key === sortKey
                    ? "text-toss-blue font-bold bg-toss-blueBg"
                    : "text-toss-text hover:bg-toss-card",
                )}
              >
                {SORT_LABELS[key]}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Card containing all rows */}
      <div className="rounded-2xl border border-toss-border bg-toss-card overflow-hidden">
        {sorted.map((holding, idx) => {
          const nativeCurrency = holding.assetSymbol.currency;
          const displayCurr = holding.displayCurrency ?? nativeCurrency;
          const dispLatestValue = displayValue(holding, "latestValue");
          const dispPnl = displayValue(holding, "pnlAbs");

          return (
            <div
              key={holding.userAssetId}
              className={cn(
                "flex items-center justify-between px-4 py-4 active:scale-[0.99] transition-transform cursor-pointer",
                idx < sorted.length - 1 && "border-b border-toss-border/50",
              )}
              onClick={() => router.push(`/assets/${holding.userAssetId}`)}
              role="button"
              tabIndex={0}
              aria-label={`${holding.assetSymbol.symbol} 상세 보기`}
              onKeyDown={(e) => e.key === "Enter" && router.push(`/assets/${holding.userAssetId}`)}
            >
              {/* Left: icon + name */}
              <div className="flex items-center gap-3 min-w-0">
                {/* Circular icon */}
                <div
                  className="h-10 w-10 shrink-0 rounded-full bg-toss-blueBg text-toss-blue grid place-items-center font-bold text-sm select-none"
                  aria-hidden="true"
                >
                  {symbolAbbr(holding.assetSymbol.symbol)}
                </div>
                <div className="min-w-0">
                  <p className="font-bold text-base text-toss-textStrong truncate">
                    {holding.assetSymbol.symbol}
                  </p>
                  <p className="text-sm text-toss-textWeak truncate">
                    {holding.assetSymbol.name}
                  </p>
                </div>
              </div>

              {/* Right: value + pnl */}
              <div className="text-right shrink-0 ml-3">
                {holding.isPending ? (
                  <p className="text-toss-textWeak text-sm">—</p>
                ) : (
                  <>
                    <p className={cn(tossCardNumber, "text-lg sm:text-xl")}>
                      {dispLatestValue !== null
                        ? formatCurrency(dispLatestValue, displayCurr)
                        : "—"}
                    </p>
                    {dispPnl !== null && (
                      <p className={cn("text-sm tabular-nums font-medium", pnlColor(dispPnl))}>
                        {Number(dispPnl) >= 0 ? "▲" : "▼"}{" "}
                        {Number(dispPnl) >= 0 ? "+" : ""}
                        {formatCurrency(dispPnl, displayCurr)}
                        {holding.pnlPct !== null && (
                          <span className="ml-1 text-xs">
                            ({Number(holding.pnlPct) >= 0 ? "+" : ""}
                            {formatPercent(holding.pnlPct)})
                          </span>
                        )}
                      </p>
                    )}
                  </>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
