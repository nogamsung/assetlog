"use client";

import { useTagBreakdown } from "@/hooks/use-tag-breakdown";
import { formatCurrency } from "@/lib/format";
import type { TagBreakdownEntry } from "@/types/tag-breakdown";

// ── Sub-components ────────────────────────────────────────────────────────────

function TableSkeleton() {
  return (
    <div
      role="status"
      aria-label="태그별 거래 집계 로딩 중"
      className="space-y-2"
    >
      {[1, 2, 3].map((i) => (
        <div
          key={i}
          className="h-10 rounded bg-muted/40 animate-pulse"
        />
      ))}
    </div>
  );
}

function EmptyState() {
  return (
    <p className="py-8 text-center text-sm text-muted-foreground">
      거래 내역이 없습니다.
    </p>
  );
}

function CurrencyAmountCell({
  amounts,
  label,
}: {
  amounts: Record<string, string>;
  label: string;
}) {
  const entries = Object.entries(amounts);
  if (entries.length === 0) {
    return <span className="text-muted-foreground">—</span>;
  }
  return (
    <span aria-label={label}>
      {entries.map(([currency, amount], idx) => (
        <span key={currency}>
          {formatCurrency(amount, currency)}
          {idx < entries.length - 1 && (
            <span className="mx-1 text-muted-foreground">/</span>
          )}
        </span>
      ))}
    </span>
  );
}

function TagCell({ tag }: { tag: string | null }) {
  if (tag === null) {
    return <span className="text-muted-foreground">(태그 없음)</span>;
  }
  return <span>{tag}</span>;
}

function TagRow({ entry }: { entry: TagBreakdownEntry }) {
  return (
    <tr className="border-b last:border-0 hover:bg-muted/20 transition-colors">
      <td className="px-4 py-3 font-medium">
        <TagCell tag={entry.tag} />
      </td>
      <td className="px-4 py-3 text-right">
        <span>{entry.transactionCount}</span>
        <span className="ml-1 text-xs text-muted-foreground">
          (매수 {entry.buyCount} · 매도 {entry.sellCount})
        </span>
      </td>
      <td className="px-4 py-3 text-right">
        <CurrencyAmountCell
          amounts={entry.totalBoughtValueByCurrency}
          label={`${entry.tag ?? "태그 없음"} 매수 합계`}
        />
      </td>
      <td className="px-4 py-3 text-right">
        <CurrencyAmountCell
          amounts={entry.totalSoldValueByCurrency}
          label={`${entry.tag ?? "태그 없음"} 매도 합계`}
        />
      </td>
    </tr>
  );
}

// ── Main component ─────────────────────────────────────────────────────────────

export function TagBreakdownTable() {
  const { data, isLoading, isError, error } = useTagBreakdown();

  return (
    <div className="rounded-2xl border border-toss-border bg-toss-card"> {/* MODIFIED: toss tokens */}
      <div className="border-b border-toss-border px-4 py-3"> {/* MODIFIED */}
        <h2 className="text-sm font-semibold text-toss-textStrong">태그별 거래 집계</h2> {/* MODIFIED */}
      </div>

      <div className="overflow-x-auto"> {/* MODIFIED: horizontal scroll for mobile */}
        {isLoading ? (
          <div className="p-4">
            <TableSkeleton />
          </div>
        ) : isError ? (
          <div
            role="alert"
            className="px-4 py-6 text-center text-sm text-destructive"
          >
            {error instanceof Error
              ? error.message
              : "태그별 거래 집계를 불러오지 못했습니다."}
          </div>
        ) : !data || data.entries.length === 0 ? (
          <EmptyState />
        ) : (
          <table className="w-full text-sm min-w-[480px]"> {/* MODIFIED: min-w prevents collapse on mobile */}
            <caption className="sr-only">태그별 거래 flow 집계 테이블</caption>
            <thead>
              <tr className="border-b border-toss-border text-left text-toss-textWeak"> {/* MODIFIED */}
                <th scope="col" className="sticky left-0 bg-toss-card px-4 py-3 font-medium"> {/* MODIFIED: sticky first col */}
                  태그
                </th>
                <th scope="col" className="px-4 py-3 font-medium text-right">
                  거래수
                </th>
                <th scope="col" className="px-4 py-3 font-medium text-right">
                  매수 합계
                </th>
                <th scope="col" className="px-4 py-3 font-medium text-right">
                  매도 합계
                </th>
              </tr>
            </thead>
            <tbody>
              {data.entries.map((entry, idx) => (
                <TagRow
                  key={entry.tag ?? `__untagged__${idx}`}
                  entry={entry}
                />
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
