"use client";

import { useState } from "react";
import { type AxiosError } from "axios";
import { Plus, Pencil, Trash2 } from "lucide-react";
import { useCashAccounts } from "@/hooks/use-cash-accounts";
import { formatCurrency } from "@/lib/format";
import type { CashAccount } from "@/types/cash-account";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { CashAccountAddDialog } from "./cash-account-add-dialog";
import { CashAccountEditDialog } from "./cash-account-edit-dialog";
import { CashAccountDeleteDialog } from "./cash-account-delete-dialog";

function CashListSkeleton() {
  return (
    <div className="space-y-3" aria-label="현금 계좌 목록 로딩 중">
      {[1, 2].map((i) => (
        <div
          key={i}
          className="h-16 rounded-lg border bg-muted/40 animate-pulse"
        />
      ))}
    </div>
  );
}

interface EmptyCashStateProps {
  onAdd: () => void;
}

function EmptyCashState({ onAdd }: EmptyCashStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-8 text-center rounded-lg border border-dashed">
      <p className="text-muted-foreground mb-3 text-sm">
        등록된 현금 계좌가 없습니다.
      </p>
      <Button
        type="button"
        variant="outline"
        size="sm"
        onClick={onAdd}
        aria-label="현금 추가"
      >
        <Plus className="h-4 w-4" aria-hidden="true" />
        현금 추가
      </Button>
    </div>
  );
}

export function CashAccountList() {
  const { data: accounts, isLoading, isError, error } = useCashAccounts();
  const [addOpen, setAddOpen] = useState(false);
  const [editTarget, setEditTarget] = useState<CashAccount | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<CashAccount | null>(null);

  if (isLoading) return <CashListSkeleton />;

  if (isError) {
    const axiosErr = error as AxiosError<{ detail: string }>;
    const message =
      axiosErr.response?.data?.detail ?? "현금 계좌를 불러오지 못했습니다.";
    return (
      <p role="alert" className="text-sm text-destructive">
        {message}
      </p>
    );
  }

  return (
    <>
      {/* 헤더 */}
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-lg font-semibold">현금</h2>
        <Button
          type="button"
          size="sm"
          onClick={() => setAddOpen(true)}
          aria-label="현금 추가"
        >
          <Plus className="h-4 w-4" aria-hidden="true" />
          현금 추가
        </Button>
      </div>

      {/* 목록 */}
      {!accounts || accounts.length === 0 ? (
        <EmptyCashState onAdd={() => setAddOpen(true)} />
      ) : (
        <div className="space-y-2">
          {accounts.map((account) => (
            <div
              key={account.id}
              className="flex items-center justify-between rounded-lg border bg-card px-4 py-3 shadow-sm"
            >
              <div className="flex items-center gap-3 min-w-0">
                <Badge variant="secondary" className="shrink-0">
                  {account.currency}
                </Badge>
                <div className="min-w-0">
                  <p className="font-medium text-sm truncate">{account.label}</p>
                  <p className="text-xs text-muted-foreground">
                    {formatCurrencySafe(account.balance, account.currency)}
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-1 shrink-0">
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  onClick={() => setEditTarget(account)}
                  aria-label={`${account.label} 수정`}
                >
                  <Pencil className="h-4 w-4" aria-hidden="true" />
                </Button>
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  onClick={() => setDeleteTarget(account)}
                  aria-label={`${account.label} 삭제`}
                >
                  <Trash2 className="h-4 w-4 text-destructive" aria-hidden="true" />
                </Button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* 다이얼로그 */}
      <CashAccountAddDialog
        open={addOpen}
        onClose={() => setAddOpen(false)}
      />

      {editTarget !== null && (
        <CashAccountEditDialog
          open={true}
          onClose={() => setEditTarget(null)}
          account={editTarget}
        />
      )}

      {deleteTarget !== null && (
        <CashAccountDeleteDialog
          open={true}
          onClose={() => setDeleteTarget(null)}
          account={deleteTarget}
        />
      )}
    </>
  );
}

/**
 * USDT / USDC 등 Intl.NumberFormat 미지원 통화 코드를 안전하게 포맷.
 * try/catch 후 fallback "${formattedNumber} ${code}" 형식.
 * 기존 formatCurrency 시그니처 변경 없이 래핑.
 */
function formatCurrencySafe(amount: string, currency: string): string {
  try {
    return formatCurrency(amount, currency);
  } catch {
    const num = Number(amount);
    const formatted = new Intl.NumberFormat("ko-KR", {
      minimumFractionDigits: 0,
      maximumFractionDigits: 4,
    }).format(num);
    return `${formatted} ${currency}`;
  }
}
