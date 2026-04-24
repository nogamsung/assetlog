"use client";

import { useTransactions, useDeleteTransaction } from "@/hooks/use-transactions";

interface TransactionListProps {
  userAssetId: number;
}

function TransactionListSkeleton() {
  return (
    <div className="space-y-2" aria-label="거래 내역 로딩 중" role="status">
      {[1, 2, 3].map((i) => (
        <div key={i} className="h-14 rounded-lg border bg-muted/40 animate-pulse" />
      ))}
    </div>
  );
}

function EmptyState() {
  return (
    <div className="py-8 text-center">
      <p className="text-sm text-muted-foreground">거래 내역이 없습니다.</p>
    </div>
  );
}

export function TransactionList({ userAssetId }: TransactionListProps) {
  const { data: transactions, isLoading, isError, error } = useTransactions(userAssetId);
  const deleteMutation = useDeleteTransaction();

  if (isLoading) return <TransactionListSkeleton />;

  if (isError) {
    return (
      <p role="alert" className="text-sm text-destructive">
        {error?.message ?? "거래 내역을 불러오지 못했습니다."}
      </p>
    );
  }

  if (!transactions || transactions.length === 0) return <EmptyState />;

  function handleDelete(txId: number) {
    if (window.confirm("이 거래 기록을 삭제하시겠습니까?")) {
      deleteMutation.mutate({ userAssetId, txId });
    }
  }

  return (
    <div className="space-y-2">
      {transactions.map((tx) => {
        const tradedAtDate = new Date(tx.tradedAt);
        const formattedDate = tradedAtDate.toLocaleString("ko-KR", {
          year: "numeric",
          month: "2-digit",
          day: "2-digit",
          hour: "2-digit",
          minute: "2-digit",
        });

        return (
          <div
            key={tx.id}
            className="flex items-center justify-between rounded-lg border bg-card px-4 py-3 shadow-sm"
          >
            <div className="flex items-center gap-4">
              <span
                className={`text-xs font-semibold px-2 py-0.5 rounded-full ${ // MODIFIED
                  tx.type === "buy"
                    ? "bg-emerald-100 text-emerald-700"
                    : "bg-rose-100 text-rose-700"
                }`}
              >
                {tx.type === "buy" ? "매수" : "매도"}
              </span>
              <div>
                <p className="text-sm font-medium">
                  {tx.type === "buy" ? "+" : "-"}{tx.quantity}{/* ADDED sign */}{" "}
                  <span className="text-muted-foreground">@ {tx.price}</span>
                </p>
                <p className="text-xs text-muted-foreground">{formattedDate}</p>
              </div>
              {tx.memo && (
                <p className="hidden sm:block text-xs text-muted-foreground max-w-xs truncate">
                  {tx.memo}
                </p>
              )}
            </div>
            <button
              type="button"
              onClick={() => handleDelete(tx.id)}
              disabled={deleteMutation.isPending}
              aria-label={`거래 #${tx.id} 삭제`}
              className="rounded p-1 text-muted-foreground hover:text-destructive hover:bg-destructive/10 transition-colors disabled:opacity-50"
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                width="16"
                height="16"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
                aria-hidden="true"
              >
                <path d="M3 6h18" />
                <path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6" />
                <path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2" />
              </svg>
            </button>
          </div>
        );
      })}
    </div>
  );
}
