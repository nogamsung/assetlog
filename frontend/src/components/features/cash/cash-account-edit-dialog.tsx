"use client";

import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { isAxiosError } from "axios";
import { toast } from "sonner";
import { X } from "lucide-react";
import {
  cashAccountUpdateSchema,
  type CashAccountUpdateInput,
} from "@/lib/schemas/cash-account";
import { useUpdateCashAccount } from "@/hooks/use-cash-accounts";
import type { CashAccount } from "@/types/cash-account";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

interface CashAccountEditDialogProps {
  open: boolean;
  onClose: () => void;
  account: CashAccount;
}

export function CashAccountEditDialog({
  open,
  onClose,
  account,
}: CashAccountEditDialogProps) {
  const updateMutation = useUpdateCashAccount();

  const {
    register,
    handleSubmit,
    reset,
    setError,
    formState: { errors },
  } = useForm<CashAccountUpdateInput>({
    resolver: zodResolver(cashAccountUpdateSchema),
    defaultValues: {
      label: account.label,
      balance: account.balance,
    },
  });

  useEffect(() => {
    if (open) {
      reset({ label: account.label, balance: account.balance });
    }
  }, [open, account, reset]);

  function onSubmit(data: CashAccountUpdateInput) {
    updateMutation.mutate(
      { id: account.id, input: data },
      {
        onSuccess: () => {
          toast.success("현금 계좌가 수정되었습니다.");
          onClose();
        },
        onError: (err) => {
          if (isAxiosError(err) && err.response?.status === 422) {
            const detail = (err.response.data as { detail?: string }).detail;
            setError("root", {
              message: detail ?? "입력값을 확인해 주세요.",
            });
          }
        },
      },
    );
  }

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-background/80 backdrop-blur-sm"
      role="dialog"
      aria-modal="true"
      aria-label="현금 계좌 수정 다이얼로그"
    >
      <div
        className="relative w-full max-w-md rounded-xl border bg-background shadow-lg mx-4"
        role="document"
      >
        {/* 헤더 */}
        <div className="flex items-center justify-between border-b px-6 py-4">
          <h2 className="text-lg font-semibold">현금 수정</h2>
          <button
            type="button"
            onClick={onClose}
            aria-label="다이얼로그 닫기"
            className="rounded p-1 text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
          >
            <X className="h-5 w-5" aria-hidden="true" />
          </button>
        </div>

        {/* 폼 */}
        <form
          onSubmit={handleSubmit(onSubmit)}
          className="space-y-4 px-6 py-5"
          noValidate
          aria-label="현금 계좌 수정 폼"
        >
          {errors.root && (
            <p role="alert" className="text-sm font-medium text-destructive">
              {errors.root.message}
            </p>
          )}

          <div className="space-y-2">
            <Label htmlFor="edit-cash-label">라벨</Label>
            <Input
              id="edit-cash-label"
              type="text"
              placeholder="예: 토스뱅크 원화"
              aria-label="계좌 라벨"
              aria-invalid={!!errors.label}
              {...register("label")}
            />
            {errors.label && (
              <p role="alert" className="text-xs text-destructive">
                {errors.label.message}
              </p>
            )}
          </div>

          {/* 통화는 수정 불가 — readonly 표시 */}
          <div className="space-y-2">
            <Label htmlFor="edit-cash-currency">통화</Label>
            <Input
              id="edit-cash-currency"
              type="text"
              value={account.currency}
              readOnly
              disabled
              aria-label="통화 (변경 불가)"
              className="cursor-not-allowed"
            />
            <p className="text-xs text-muted-foreground">
              통화는 생성 후 변경할 수 없습니다.
            </p>
          </div>

          <div className="space-y-2">
            <Label htmlFor="edit-cash-balance">잔액</Label>
            <Input
              id="edit-cash-balance"
              type="text"
              inputMode="decimal"
              placeholder="예: 1500000"
              aria-label="계좌 잔액"
              aria-invalid={!!errors.balance}
              {...register("balance")}
            />
            {errors.balance && (
              <p role="alert" className="text-xs text-destructive">
                {errors.balance.message}
              </p>
            )}
          </div>

          <div className="flex flex-col-reverse gap-2 pt-2 sm:flex-row sm:justify-end"> {/* MODIFIED */}
            <Button type="button" variant="outline" onClick={onClose}>
              취소
            </Button>
            <Button
              type="submit"
              disabled={updateMutation.isPending}
              aria-busy={updateMutation.isPending}
            >
              {updateMutation.isPending ? "수정 중..." : "수정"}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}
