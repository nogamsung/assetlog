"use client";

import { useMarketIndices } from "@/hooks/use-market-indices";
import { formatPercent, pnlColor } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { IndexQuote } from "@/types/market-index";

function formatIndexPrice(quote: IndexQuote): string {
  const n = Number(quote.price);
  if (Number.isNaN(n)) return "—";
  if (quote.currency === "KRW" || quote.currency === "JPY") {
    return new Intl.NumberFormat("ko-KR", {
      style: "currency",
      currency: quote.currency,
      maximumFractionDigits: 0,
    }).format(n);
  }
  try {
    return new Intl.NumberFormat("ko-KR", {
      style: "currency",
      currency: quote.currency,
      maximumFractionDigits: 2,
    }).format(n);
  } catch {
    return `${n.toLocaleString("ko-KR", { maximumFractionDigits: 2 })} ${quote.currency}`;
  }
}

function IndexCard({ quote }: { quote: IndexQuote }) {
  const changeNum = Number(quote.changePct);
  const sign = changeNum > 0 ? "+" : "";
  return (
    <div className="flex min-w-[140px] flex-col gap-1 rounded-2xl border border-toss-border bg-toss-card p-4">
      <p className="text-xs font-medium text-toss-textWeak">{quote.name}</p>
      <p className="text-sm font-semibold text-toss-text">{formatIndexPrice(quote)}</p>
      <p className={cn("text-xs font-medium", pnlColor(quote.changePct))}>
        {Number.isNaN(changeNum)
          ? "—"
          : `${sign}${formatPercent(quote.changePct)}`}
      </p>
    </div>
  );
}

function MarketIndicesSkeleton() {
  return (
    <div
      role="status"
      aria-label="지수 로딩 중"
      className="flex gap-3 overflow-x-auto pb-1"
    >
      {[0, 1, 2, 3, 4].map((i) => (
        <div
          key={i}
          className="h-20 min-w-[140px] flex-shrink-0 rounded-2xl border border-toss-border bg-muted/40 animate-pulse"
        />
      ))}
    </div>
  );
}

export function MarketIndicesStrip() {
  const { data, isLoading, isError } = useMarketIndices();

  if (isLoading) return <MarketIndicesSkeleton />;
  if (isError || !data || data.length === 0) return null;

  return (
    <section aria-label="주요 시장 지수">
      <div className="flex gap-3 overflow-x-auto pb-1">
        {data.map((quote) => (
          <IndexCard key={quote.symbol} quote={quote} />
        ))}
      </div>
    </section>
  );
}
