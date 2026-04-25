"use client";

import { useState } from "react"; // ADDED
import { useForm, useWatch, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { isAxiosError } from "axios"; // ADDED
import { transactionCreateSchema, type TransactionCreateInput } from "@/lib/schemas/transaction";
import { useCreateTransaction, useUpdateTransaction, useUserTags } from "@/hooks/use-transactions"; // MODIFIED
import type { TransactionResponse } from "@/types/transaction"; // ADDED
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

interface TransactionFormProps {
  userAssetId: number;
  onSuccess?: () => void;
  mode?: "create" | "edit";
  initialValues?: TransactionResponse;
  /** 현재 보유 수량 — SELL 사전 검증에 사용 */
  remainingQuantity?: string;
}

export function TransactionForm({
  userAssetId,
  onSuccess,
  mode = "create",
  initialValues,
  remainingQuantity,
}: TransactionFormProps) {
  const createMutation = useCreateTransaction();
  const updateMutation = useUpdateTransaction();
  const activeMutation = mode === "edit" ? updateMutation : createMutation;
  const [conflictError, setConflictError] = useState<string | null>(null);
  const { data: existingTags = [] } = useUserTags();  // ADDED

  const today = new Date();
  const todayLocal = new Date(
    today.getTime() - today.getTimezoneOffset() * 60000,
  )
    .toISOString()
    .slice(0, 16);

  const {
    register,
    handleSubmit,
    control,
    formState: { errors },
    reset,
  } = useForm<TransactionCreateInput>({
    resolver: zodResolver(transactionCreateSchema),
    defaultValues: mode === "edit" && initialValues // MODIFIED
      ? {
          type: initialValues.type,
          quantity: initialValues.quantity,
          price: initialValues.price,
          tradedAt: new Date(initialValues.tradedAt),
          memo: initialValues.memo,
          tag: initialValues.tag,  // ADDED
        }
      : {
          type: "buy",
          quantity: "",
          price: "",
          tradedAt: new Date(),
          memo: null,
          tag: null,  // ADDED
        },
  });

  const watchedType = useWatch({ control, name: "type" });
  const watchedQuantity = useWatch({ control, name: "quantity" });

  const sellExceedsHolding: boolean =
    watchedType === "sell" &&
    remainingQuantity !== undefined &&
    mode === "create" &&
    typeof watchedQuantity === "string" &&
    watchedQuantity.trim() !== "" &&
    Number.isFinite(Number(watchedQuantity)) &&
    Number(watchedQuantity) > Number(remainingQuantity);

  function onSubmit(data: TransactionCreateInput) {
    setConflictError(null);
    if (sellExceedsHolding) {
      setConflictError(
        `보유 수량(${remainingQuantity}) 을 초과하여 매도할 수 없습니다.`,
      );
      return;
    }
    if (mode === "edit" && initialValues) { // ADDED
      updateMutation.mutate(
        { userAssetId, transactionId: initialValues.id, data },
        {
          onSuccess: () => {
            onSuccess?.();
          },
          onError: (err) => {
            if (isAxiosError(err) && err.response?.status === 409) {
              const detail = (err.response.data as { detail?: string }).detail;
              setConflictError(detail ?? "수정 결과가 보유 수량을 초과합니다.");
            }
          },
        },
      );
      return;
    }
    createMutation.mutate(
      { userAssetId, data },
      {
        onSuccess: () => {
          reset();
          onSuccess?.();
        },
        onError: (err) => { // ADDED
          if (isAxiosError(err) && err.response?.status === 409) {
            const detail = (err.response.data as { detail?: string }).detail;
            setConflictError(detail ?? "보유 수량을 초과하여 매도할 수 없습니다.");
          }
        },
      },
    );
  }

  return (
    <form
      onSubmit={handleSubmit(onSubmit)}
      className="space-y-4"
      noValidate
      aria-label={mode === "edit" ? "거래 수정 폼" : "거래 추가 폼"} // MODIFIED
    >
      {conflictError && ( // ADDED
        <p role="alert" className="text-sm font-medium text-destructive">
          {conflictError}
        </p>
      )}
      {!conflictError && activeMutation.isError && ( // MODIFIED
        <p role="alert" className="text-sm font-medium text-destructive">
          {activeMutation.error?.message ?? (mode === "edit" ? "거래 수정에 실패했습니다." : "거래 등록에 실패했습니다.")}
        </p>
      )}

      <div className="space-y-2">
        <Label htmlFor="tx-type">거래 유형</Label>
        <select
          id="tx-type"
          {...register("type")}
          className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
          aria-label="거래 유형"
        >
          <option value="buy">매수</option>
          <option value="sell">매도</option>
        </select>
        {errors.type && (
          <p role="alert" className="text-xs text-destructive">
            {errors.type.message}
          </p>
        )}
      </div>

      <div className="space-y-2">
        <Label htmlFor="tx-quantity">수량</Label>
        <Input
          id="tx-quantity"
          type="text"
          inputMode="decimal"
          placeholder="예: 1.5"
          aria-label="거래 수량"
          aria-invalid={!!errors.quantity || sellExceedsHolding}
          {...register("quantity")}
        />
        {watchedType === "sell" && remainingQuantity !== undefined && (
          <p className="text-xs text-muted-foreground" aria-live="polite">
            보유 수량: {remainingQuantity}
          </p>
        )}
        {errors.quantity && (
          <p role="alert" className="text-xs text-destructive">
            {errors.quantity.message}
          </p>
        )}
        {sellExceedsHolding && !errors.quantity && (
          <p role="alert" className="text-xs text-destructive">
            보유 수량을 초과하여 매도할 수 없습니다.
          </p>
        )}
      </div>

      <div className="space-y-2">
        <Label htmlFor="tx-price">단가</Label>
        <Input
          id="tx-price"
          type="text"
          inputMode="decimal"
          placeholder="예: 50000"
          aria-label="거래 단가"
          aria-invalid={!!errors.price}
          {...register("price")}
        />
        {errors.price && (
          <p role="alert" className="text-xs text-destructive">
            {errors.price.message}
          </p>
        )}
      </div>

      <div className="space-y-2">
        <Label htmlFor="tx-tradedAt">거래일</Label>
        <Controller
          name="tradedAt"
          control={control}
          render={({ field }) => (
            <Input
              id="tx-tradedAt"
              type="datetime-local"
              max={todayLocal}
              aria-label="거래일"
              aria-invalid={!!errors.tradedAt}
              value={
                field.value instanceof Date
                  ? new Date(
                      field.value.getTime() -
                        field.value.getTimezoneOffset() * 60000,
                    )
                      .toISOString()
                      .slice(0, 16)
                  : todayLocal
              }
              onChange={(e) => {
                const val = e.target.value;
                field.onChange(val ? new Date(val) : new Date());
              }}
            />
          )}
        />
        {errors.tradedAt && (
          <p role="alert" className="text-xs text-destructive">
            {errors.tradedAt.message}
          </p>
        )}
      </div>

      <div className="space-y-2">
        <Label htmlFor="tx-memo">메모 (선택)</Label>
        <Input
          id="tx-memo"
          type="text"
          placeholder="거래 관련 메모..."
          aria-label="거래 메모"
          maxLength={255}
          {...register("memo")}
        />
        {errors.memo && (
          <p role="alert" className="text-xs text-destructive">
            {errors.memo.message}
          </p>
        )}
      </div>

      <div className="space-y-2">
        <Label htmlFor="tx-tag">태그 (선택)</Label>
        <Input
          id="tx-tag"
          type="text"
          placeholder="예: DCA, 스윙, 장기보유"
          aria-label="거래 태그"
          maxLength={50}
          list="tx-tag-suggestions"
          {...register("tag")}
        />
        {existingTags.length > 0 && (
          <datalist id="tx-tag-suggestions">
            {existingTags.map((t) => (
              <option key={t} value={t} />
            ))}
          </datalist>
        )}
        {errors.tag && (
          <p role="alert" className="text-xs text-destructive">
            {errors.tag.message}
          </p>
        )}
      </div>

      <Button
        type="submit"
        className="w-full"
        disabled={activeMutation.isPending || sellExceedsHolding}
        aria-busy={activeMutation.isPending}
      >
        {activeMutation.isPending
          ? mode === "edit"
            ? "수정 중..."
            : "등록 중..."
          : mode === "edit"
            ? "수정하기"
            : "거래 추가"}
      </Button>
    </form>
  );
}
