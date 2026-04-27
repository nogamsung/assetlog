"use client";

import { useFieldArray, useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Trash2, Plus } from "lucide-react";
import { Button } from "@/components/ui/button";
import { BulkErrorList } from "./bulk-error-list";
import { useBulkImportTransactions, extractBulkErrors } from "@/hooks/use-bulk-import-transactions";
import { useUserAssets } from "@/hooks/use-assets";
import { bulkRequestSchema, type BulkRequestInput } from "@/lib/schemas/bulk-transaction";
import type { BulkTransactionError } from "@/types/bulk-transaction";
import { useState } from "react";

const DEFAULT_ROW_COUNT = 5;

function makeEmptyRow() {
  const now = new Date();
  const localIso = new Date(now.getTime() - now.getTimezoneOffset() * 60000)
    .toISOString()
    .slice(0, 16);
  return {
    symbol: "",
    exchange: "",
    type: "buy" as const,
    quantity: "",
    price: "",
    traded_at: localIso,
    memo: "",
    tag: "",
  };
}

interface BulkGridTabProps {
  onSuccess?: () => void;
}

export function BulkGridTab({ onSuccess }: BulkGridTabProps) {
  const [serverErrors, setServerErrors] = useState<BulkTransactionError[]>([]);
  const mutation = useBulkImportTransactions();
  const { data: userAssets = [] } = useUserAssets();

  // datalist 데이터
  const symbolOptions = Array.from(
    new Set(userAssets.map((a) => a.assetSymbol.symbol)),
  );
  const exchangeOptions = Array.from(
    new Set(userAssets.map((a) => a.assetSymbol.exchange)),
  );

  const {
    register,
    control,
    handleSubmit,
    setError,
    formState: { errors },
  } = useForm<BulkRequestInput>({
    resolver: zodResolver(bulkRequestSchema),
    defaultValues: {
      rows: Array.from({ length: DEFAULT_ROW_COUNT }, makeEmptyRow),
    },
  });

  const { fields, append, remove } = useFieldArray({ control, name: "rows" });

  async function onSubmit(data: BulkRequestInput) {
    setServerErrors([]);

    try {
      await mutation.mutateAsync({ mode: "json", rows: data.rows });
      onSuccess?.();
    } catch (err) {
      if (err instanceof Error) {
        const errs = extractBulkErrors(err);
        if (errs) {
          setServerErrors(errs);
          for (const e of errs) {
            if (e.row > 0 && e.field) {
              const fieldName = e.field as keyof BulkRequestInput["rows"][number];
              setError(`rows.${e.row - 1}.${fieldName}`, {
                type: "server",
                message: e.message,
              });
            }
          }
        }
      }
    }
  }

  return (
    <div className="space-y-4">
      {/* 서버 422 오류 요약 */}
      {serverErrors.length > 0 && (
        <BulkErrorList errors={serverErrors} />
      )}

      {/* symbol / exchange datalist */}
      <datalist id="bulk-symbol-list">
        {symbolOptions.map((s) => (
          <option key={s} value={s} />
        ))}
      </datalist>
      <datalist id="bulk-exchange-list">
        {exchangeOptions.map((e) => (
          <option key={e} value={e} />
        ))}
      </datalist>

      <form
        onSubmit={handleSubmit(onSubmit)}
        noValidate
        aria-label="일괄 거래 직접 입력 폼"
      >
        <div className="overflow-x-auto rounded-md border">
          <table className="w-full text-xs" role="grid" aria-label="거래 입력 그리드">
            <thead className="bg-muted/50">
              <tr>
                <th className="border-b px-2 py-2 text-left font-medium text-muted-foreground w-8">#</th>
                <th className="border-b px-2 py-2 text-left font-medium text-muted-foreground min-w-[80px]">종목*</th>
                <th className="border-b px-2 py-2 text-left font-medium text-muted-foreground min-w-[80px]">거래소*</th>
                <th className="border-b px-2 py-2 text-left font-medium text-muted-foreground min-w-[70px]">유형*</th>
                <th className="border-b px-2 py-2 text-left font-medium text-muted-foreground min-w-[80px]">수량*</th>
                <th className="border-b px-2 py-2 text-left font-medium text-muted-foreground min-w-[80px]">단가*</th>
                <th className="border-b px-2 py-2 text-left font-medium text-muted-foreground min-w-[140px]">거래일*</th>
                <th className="border-b px-2 py-2 text-left font-medium text-muted-foreground min-w-[80px]">메모</th>
                <th className="border-b px-2 py-2 text-left font-medium text-muted-foreground min-w-[60px]">태그</th>
                <th className="border-b px-2 py-2 w-8" aria-label="삭제"></th>
              </tr>
            </thead>
            <tbody>
              {fields.map((field, index) => {
                const rowErrors = errors.rows?.[index];
                const hasRowError = !!rowErrors;
                return (
                  <tr
                    key={field.id}
                    className={hasRowError ? "bg-destructive/10" : "hover:bg-muted/20"}
                    aria-invalid={hasRowError}
                  >
                    <td className="border-b px-2 py-1 text-muted-foreground font-mono text-center">
                      {hasRowError && (
                        <span className="text-destructive mr-0.5" aria-hidden="true">●</span>
                      )}
                      {index + 1}
                    </td>

                    {/* symbol */}
                    <td className="border-b px-1 py-1">
                      <input
                        {...register(`rows.${index}.symbol`)}
                        list="bulk-symbol-list"
                        placeholder="BTC"
                        aria-label={`${index + 1}행 종목 코드`}
                        aria-invalid={!!rowErrors?.symbol}
                        aria-describedby={rowErrors?.symbol ? `err-${index}-symbol` : undefined}
                        className="w-full rounded border-0 bg-transparent px-1 py-0.5 text-xs focus:outline-none focus:ring-1 focus:ring-ring aria-[invalid=true]:text-destructive"
                      />
                      {rowErrors?.symbol && (
                        <p id={`err-${index}-symbol`} role="alert" className="text-destructive text-xs mt-0.5">
                          {rowErrors.symbol.message}
                        </p>
                      )}
                    </td>

                    {/* exchange */}
                    <td className="border-b px-1 py-1">
                      <input
                        {...register(`rows.${index}.exchange`)}
                        list="bulk-exchange-list"
                        placeholder="UPBIT"
                        aria-label={`${index + 1}행 거래소`}
                        aria-invalid={!!rowErrors?.exchange}
                        aria-describedby={rowErrors?.exchange ? `err-${index}-exchange` : undefined}
                        className="w-full rounded border-0 bg-transparent px-1 py-0.5 text-xs focus:outline-none focus:ring-1 focus:ring-ring aria-[invalid=true]:text-destructive"
                      />
                      {rowErrors?.exchange && (
                        <p id={`err-${index}-exchange`} role="alert" className="text-destructive text-xs mt-0.5">
                          {rowErrors.exchange.message}
                        </p>
                      )}
                    </td>

                    {/* type */}
                    <td className="border-b px-1 py-1">
                      <select
                        {...register(`rows.${index}.type`)}
                        aria-label={`${index + 1}행 거래 유형`}
                        aria-invalid={!!rowErrors?.type}
                        className="w-full rounded border-0 bg-transparent px-1 py-0.5 text-xs focus:outline-none focus:ring-1 focus:ring-ring"
                      >
                        <option value="buy">매수</option>
                        <option value="sell">매도</option>
                      </select>
                      {rowErrors?.type && (
                        <p role="alert" className="text-destructive text-xs mt-0.5">
                          {rowErrors.type.message}
                        </p>
                      )}
                    </td>

                    {/* quantity */}
                    <td className="border-b px-1 py-1">
                      <input
                        {...register(`rows.${index}.quantity`)}
                        type="text"
                        inputMode="decimal"
                        placeholder="0.5"
                        aria-label={`${index + 1}행 수량`}
                        aria-invalid={!!rowErrors?.quantity}
                        aria-describedby={rowErrors?.quantity ? `err-${index}-quantity` : undefined}
                        className="w-full rounded border-0 bg-transparent px-1 py-0.5 text-xs focus:outline-none focus:ring-1 focus:ring-ring aria-[invalid=true]:text-destructive"
                      />
                      {rowErrors?.quantity && (
                        <p id={`err-${index}-quantity`} role="alert" className="text-destructive text-xs mt-0.5">
                          {rowErrors.quantity.message}
                        </p>
                      )}
                    </td>

                    {/* price */}
                    <td className="border-b px-1 py-1">
                      <input
                        {...register(`rows.${index}.price`)}
                        type="text"
                        inputMode="decimal"
                        placeholder="85000000"
                        aria-label={`${index + 1}행 단가`}
                        aria-invalid={!!rowErrors?.price}
                        aria-describedby={rowErrors?.price ? `err-${index}-price` : undefined}
                        className="w-full rounded border-0 bg-transparent px-1 py-0.5 text-xs focus:outline-none focus:ring-1 focus:ring-ring aria-[invalid=true]:text-destructive"
                      />
                      {rowErrors?.price && (
                        <p id={`err-${index}-price`} role="alert" className="text-destructive text-xs mt-0.5">
                          {rowErrors.price.message}
                        </p>
                      )}
                    </td>

                    {/* traded_at */}
                    <td className="border-b px-1 py-1">
                      <input
                        {...register(`rows.${index}.traded_at`)}
                        type="datetime-local"
                        aria-label={`${index + 1}행 거래일`}
                        aria-invalid={!!rowErrors?.traded_at}
                        aria-describedby={rowErrors?.traded_at ? `err-${index}-traded_at` : undefined}
                        className="w-full rounded border-0 bg-transparent px-1 py-0.5 text-xs focus:outline-none focus:ring-1 focus:ring-ring aria-[invalid=true]:text-destructive"
                      />
                      {rowErrors?.traded_at && (
                        <p id={`err-${index}-traded_at`} role="alert" className="text-destructive text-xs mt-0.5">
                          {rowErrors.traded_at.message}
                        </p>
                      )}
                    </td>

                    {/* memo */}
                    <td className="border-b px-1 py-1">
                      <input
                        {...register(`rows.${index}.memo`)}
                        type="text"
                        placeholder="메모"
                        maxLength={255}
                        aria-label={`${index + 1}행 메모`}
                        className="w-full rounded border-0 bg-transparent px-1 py-0.5 text-xs focus:outline-none focus:ring-1 focus:ring-ring"
                      />
                    </td>

                    {/* tag */}
                    <td className="border-b px-1 py-1">
                      <input
                        {...register(`rows.${index}.tag`)}
                        type="text"
                        placeholder="태그"
                        maxLength={50}
                        aria-label={`${index + 1}행 태그`}
                        className="w-full rounded border-0 bg-transparent px-1 py-0.5 text-xs focus:outline-none focus:ring-1 focus:ring-ring"
                      />
                    </td>

                    {/* 삭제 버튼 */}
                    <td className="border-b px-1 py-1 text-center">
                      <button
                        type="button"
                        onClick={() => remove(index)}
                        disabled={fields.length === 1}
                        aria-label={`${index + 1}행 삭제`}
                        className="rounded p-0.5 text-muted-foreground hover:text-destructive hover:bg-destructive/10 transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
                      >
                        <Trash2 className="h-3.5 w-3.5" aria-hidden="true" />
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        {/* 전체 rows 레벨 에러 */}
        {errors.rows?.root && (
          <p role="alert" className="text-sm text-destructive mt-1">
            {errors.rows.root.message}
          </p>
        )}
        {errors.rows && !Array.isArray(errors.rows) && "message" in errors.rows && (
          <p role="alert" className="text-sm text-destructive mt-1">
            {(errors.rows as { message?: string }).message}
          </p>
        )}

        <div className="flex items-center justify-between pt-3">
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => append(makeEmptyRow())}
            aria-label="행 추가"
            className="gap-1.5"
          >
            <Plus className="h-3.5 w-3.5" aria-hidden="true" />
            행 추가
          </Button>

          <div className="flex gap-2">
            <Button
              type="submit"
              size="sm"
              disabled={mutation.isPending}
              aria-busy={mutation.isPending}
            >
              {mutation.isPending ? "저장 중..." : "저장"}
            </Button>
          </div>
        </div>
      </form>
    </div>
  );
}
