"use client";

import { useEffect } from "react";
import { useForm, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { isAxiosError } from "axios";
import { toast } from "sonner";
import { X } from "lucide-react";
import {
  cashAccountCreateSchema,
  type CashAccountCreateInput,
} from "@/lib/schemas/cash-account";
import { useCreateCashAccount } from "@/hooks/use-cash-accounts";
import { CurrencySelect } from "./currency-select";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

interface CashAccountAddDialogProps {
  open: boolean;
  onClose: () => void;
}

export function CashAccountAddDialog({
  open,
  onClose,
}: CashAccountAddDialogProps) {
  const createMutation = useCreateCashAccount();

  const {
    register,
    handleSubmit,
    control,
    reset,
    setError,
    formState: { errors },
  } = useForm<CashAccountCreateInput>({
    resolver: zodResolver(cashAccountCreateSchema),
    defaultValues: {
      label: "",
      currency: "",
      balance: "",
    },
  });

  useEffect(() => {
    if (!open) {
      reset();
    }
  }, [open, reset]);

  function onSubmit(data: CashAccountCreateInput) {
    createMutation.mutate(data, {
      onSuccess: () => {
        toast.success("현금 계좌가 추가되었습니다.");
        reset();
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
    });
  }

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-background/80 backdrop-blur-sm"
      role="dialog"
      aria-modal="true"
      aria-label="현금 계좌 추가 다이얼로그"
    >
      <div
        className="relative w-full max-w-md rounded-xl border bg-background shadow-lg mx-4"
        role="document"
      >
        {/* 헤더 */}
        <div className="flex items-center justify-between border-b px-6 py-4">
          <h2 className="text-lg font-semibold">현금 추가</h2>
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
          aria-label="현금 계좌 추가 폼"
        >
          {errors.root && (
            <p role="alert" className="text-sm font-medium text-destructive">
              {errors.root.message}
            </p>
          )}

          <div className="space-y-2">
            <Label htmlFor="cash-label">라벨</Label>
            <Input
              id="cash-label"
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

          <div className="space-y-2">
            <Label htmlFor="cash-currency">통화</Label>
            <Controller
              name="currency"
              control={control}
              render={({ field }) => (
                <CurrencySelect
                  id="cash-currency"
                  value={field.value}
                  onChange={field.onChange}
                  aria-invalid={!!errors.currency}
                />
              )}
            />
            {errors.currency && (
              <p role="alert" className="text-xs text-destructive">
                {errors.currency.message}
              </p>
            )}
          </div>

          <div className="space-y-2">
            <Label htmlFor="cash-balance">잔액</Label>
            <Input
              id="cash-balance"
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
              disabled={createMutation.isPending}
              aria-busy={createMutation.isPending}
            >
              {createMutation.isPending ? "추가 중..." : "추가"}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}
