"use client";

import { Pencil, Trash2 } from "lucide-react"; /* MODIFIED: added Trash2 */
import { useTransactions, useDeleteTransaction } from "@/hooks/use-transactions";
import type { TransactionResponse } from "@/types/transaction"; // ADDED

interface TransactionListProps {
  userAssetId: number;
  onEdit?: (transaction: TransactionResponse) => void; // ADDED
  onTagClick?: (tag: string) => void;  // ADDED
  activeTag?: string | null;            // ADDED
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

export function TransactionList({ userAssetId, onEdit, onTagClick, activeTag }: TransactionListProps) { // MODIFIED
  const { data: transactions, isLoading, isError, error } = useTransactions(userAssetId, activeTag ?? undefined);
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
            className="flex items-center justify-between rounded-2xl border border-toss-border bg-toss-card px-4 py-3" /* MODIFIED: toss card */
          >
            <div className="flex items-center gap-4">
              <span
                className={`text-xs font-bold px-2.5 py-0.5 rounded-full ${ /* MODIFIED: toss colors for buy/sell */
                  tx.type === "buy"
                    ? "bg-toss-up/10 text-toss-up"
                    : "bg-toss-down/10 text-toss-down"
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
              {tx.tag && (                // ADDED — tag badge
                <button
                  type="button"
                  onClick={() => onTagClick?.(tx.tag!)}
                  aria-label={`태그 ${tx.tag} 필터 적용`}
                  className="hidden sm:inline-flex items-center rounded px-2 py-0.5 text-xs bg-muted text-foreground hover:bg-muted/70 transition-colors"
                >
                  {tx.tag}
                </button>
              )}
            </div>
            <div className="flex items-center gap-1"> {/* ADDED */}
            {onEdit && (
              <button
                type="button"
                onClick={() => onEdit(tx)}
                aria-label={`거래 #${tx.id} 편집`}
                className="min-h-11 min-w-11 flex items-center justify-center rounded-xl text-toss-textWeak hover:text-toss-text hover:bg-toss-card transition-colors" /* MODIFIED: icon-touch */
              >
                <Pencil className="h-4 w-4" aria-hidden="true" />
              </button>
            )}
            <button
              type="button"
              onClick={() => handleDelete(tx.id)}
              disabled={deleteMutation.isPending}
              aria-label={`거래 #${tx.id} 삭제`}
              className="min-h-11 min-w-11 flex items-center justify-center rounded-xl text-toss-textWeak hover:text-toss-up hover:bg-toss-up/10 transition-colors disabled:opacity-50" /* MODIFIED: icon-touch + toss colors + Trash2 */
            >
              <Trash2 className="h-4 w-4" aria-hidden="true" /> {/* MODIFIED: replaced inline SVG */}
            </button>
            </div> {/* ADDED */}
          </div>
        );
      })}
    </div>
  );
}
