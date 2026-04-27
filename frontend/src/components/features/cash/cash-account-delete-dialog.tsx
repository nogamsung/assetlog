"use client";

import { toast } from "sonner";
import { X } from "lucide-react";
import { useDeleteCashAccount } from "@/hooks/use-cash-accounts";
import type { CashAccount } from "@/types/cash-account";
import { Button } from "@/components/ui/button";

interface CashAccountDeleteDialogProps {
  open: boolean;
  onClose: () => void;
  account: CashAccount;
}

export function CashAccountDeleteDialog({
  open,
  onClose,
  account,
}: CashAccountDeleteDialogProps) {
  const deleteMutation = useDeleteCashAccount();

  function handleConfirm() {
    deleteMutation.mutate(account.id, {
      onSuccess: () => {
        toast.success("현금 계좌가 삭제되었습니다.");
        onClose();
      },
    });
  }

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-background/80 backdrop-blur-sm"
      role="dialog"
      aria-modal="true"
      aria-label="현금 계좌 삭제 확인 다이얼로그"
    >
      <div
        className="relative w-full max-w-sm rounded-xl border bg-background shadow-lg mx-4"
        role="document"
      >
        {/* 헤더 */}
        <div className="flex items-center justify-between border-b px-6 py-4">
          <h2 className="text-lg font-semibold">현금 삭제</h2>
          <button
            type="button"
            onClick={onClose}
            aria-label="다이얼로그 닫기"
            className="rounded p-1 text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
          >
            <X className="h-5 w-5" aria-hidden="true" />
          </button>
        </div>

        {/* 내용 */}
        <div className="px-6 py-5 space-y-4">
          <p className="text-sm text-muted-foreground">
            <span className="font-semibold text-foreground">
              {account.label}
            </span>{" "}
            ({account.currency}) 을(를) 삭제하시겠습니까?
          </p>
          <p className="text-sm font-medium text-destructive">
            삭제하면 복구할 수 없습니다.
          </p>

          {deleteMutation.isError && (
            <p role="alert" className="text-sm text-destructive">
              삭제에 실패했습니다. 다시 시도해 주세요.
            </p>
          )}

          <div className="flex justify-end gap-2 pt-2">
            <Button
              type="button"
              variant="outline"
              onClick={onClose}
              disabled={deleteMutation.isPending}
            >
              취소
            </Button>
            <Button
              type="button"
              variant="destructive"
              onClick={handleConfirm}
              disabled={deleteMutation.isPending}
              aria-busy={deleteMutation.isPending}
            >
              {deleteMutation.isPending ? "삭제 중..." : "삭제"}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
