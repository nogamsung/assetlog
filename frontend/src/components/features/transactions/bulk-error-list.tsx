"use client";

import type { BulkTransactionError } from "@/types/bulk-transaction";

interface BulkErrorListProps {
  errors: BulkTransactionError[];
  className?: string;
}

export function BulkErrorList({ errors, className = "" }: BulkErrorListProps) {
  if (errors.length === 0) return null;

  const globalErrors = errors.filter((e) => e.row === 0 || e.field === null);
  const rowErrors = errors.filter((e) => e.row > 0 && e.field !== null);

  return (
    <div
      role="alert"
      aria-label="일괄 등록 오류 목록"
      className={`rounded-md border border-destructive/50 bg-destructive/10 p-4 ${className}`}
    >
      <p className="mb-2 text-sm font-semibold text-destructive">
        {errors.length}건의 오류가 발생했습니다.
      </p>

      {globalErrors.length > 0 && (
        <ul className="mb-2 space-y-1 text-sm text-destructive" aria-label="전역 오류">
          {globalErrors.map((e, i) => (
            <li key={`global-${i}`} className="flex items-start gap-1.5">
              <span className="mt-0.5 shrink-0 text-xs font-medium">오류:</span>
              <span>{e.message}</span>
            </li>
          ))}
        </ul>
      )}

      {rowErrors.length > 0 && (
        <ul className="space-y-1 text-sm text-destructive" aria-label="행별 오류">
          {rowErrors.map((e, i) => (
            <li key={`row-${i}`} className="flex items-start gap-1.5">
              <span className="mt-0.5 shrink-0 rounded bg-destructive/20 px-1.5 py-0.5 text-xs font-mono font-medium">
                {e.row}행{e.field ? ` / ${e.field}` : ""}
              </span>
              <span>{e.message}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
