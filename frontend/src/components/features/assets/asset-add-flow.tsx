"use client";

import { useReducer, useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { type AxiosError } from "axios";
import { useCreateUserAsset } from "@/hooks/use-assets";
import { useCreateTransaction } from "@/hooks/use-transactions";
import { transactionCreateSchema, type TransactionCreateInput } from "@/lib/schemas/transaction";
import { SymbolSearch } from "./symbol-search";
import { SymbolCreateForm } from "./symbol-create-form";
import { AssetTypeBadge } from "./asset-type-badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ArrowLeft } from "lucide-react";
import type { AssetSymbolResponse } from "@/types/asset";

// ── State machine ─────────────────────────────────────────────────────────────

type Step =
  | { kind: "search" }
  | { kind: "manual" }
  | { kind: "confirm"; symbol: AssetSymbolResponse };

type Action =
  | { type: "SELECT_SYMBOL"; symbol: AssetSymbolResponse }
  | { type: "REQUEST_MANUAL" }
  | { type: "BACK_TO_SEARCH" }
  | { type: "SYMBOL_CREATED"; symbol: AssetSymbolResponse };

function stepReducer(state: Step, action: Action): Step {
  switch (action.type) {
    case "SELECT_SYMBOL":
      return { kind: "confirm", symbol: action.symbol };
    case "REQUEST_MANUAL":
      return { kind: "manual" };
    case "BACK_TO_SEARCH":
      return { kind: "search" };
    case "SYMBOL_CREATED":
      return { kind: "confirm", symbol: action.symbol };
    default:
      return state;
  }
}

// ── Step labels ───────────────────────────────────────────────────────────────

const STEP_LABELS: Record<Step["kind"], string> = {
  search: "1. 심볼 검색",
  manual: "1b. 심볼 직접 등록",
  confirm: "2. 자산 등록 확정",
};

// ── Confirm step ──────────────────────────────────────────────────────────────

interface ConfirmStepProps {
  symbol: AssetSymbolResponse;
  onBack: () => void;
}

function ConfirmStep({ symbol, onBack }: ConfirmStepProps) {
  const createAssetMutation = useCreateUserAsset();
  const createTransactionMutation = useCreateTransaction();
  const [txError, setTxError] = useState<string | null>(null);
  const [skipTransaction, setSkipTransaction] = useState(false);

  // Used only to access the zodResolver — actual submission is handled manually
  // to allow sequential asset-create → transaction-create flow.
  const _txForm = useForm<TransactionCreateInput>({
    resolver: zodResolver(transactionCreateSchema),
    defaultValues: {
      type: "buy",
      quantity: "",
      price: "",
      tradedAt: new Date(),
      memo: null,
    },
  });
  void _txForm;

  function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const formData = new FormData(e.currentTarget);
    const memoValue = (formData.get("memo") as string | null) ?? "";
    const memo = memoValue.trim() === "" ? null : memoValue.trim();

    if (skipTransaction) {
      createAssetMutation.mutate({ assetSymbolId: symbol.id, memo });
      return;
    }

    // Validate transaction fields manually before mutating
    const quantity = (formData.get("quantity") as string | null) ?? "";
    const price = (formData.get("price") as string | null) ?? "";
    const tradedAtStr = (formData.get("tradedAt") as string | null) ?? "";
    const tradedAt = tradedAtStr ? new Date(tradedAtStr) : new Date();
    const txMemoValue = (formData.get("txMemo") as string | null) ?? "";
    const txMemo = txMemoValue.trim() === "" ? null : txMemoValue.trim();

    const txParseResult = transactionCreateSchema.safeParse({
      type: "buy",
      quantity,
      price,
      tradedAt,
      memo: txMemo,
    });

    if (!txParseResult.success) {
      const firstError = txParseResult.error.errors[0];
      setTxError(firstError?.message ?? "거래 정보를 확인하세요");
      return;
    }

    setTxError(null);
    const txData = txParseResult.data;

    createAssetMutation.mutate(
      { assetSymbolId: symbol.id, memo },
      {
        onSuccess: (userAsset) => {
          createTransactionMutation.mutate(
            { userAssetId: userAsset.id, data: txData },
            {
              onError: () => {
                setTxError(
                  `자산은 생성됐으나 거래 기록 실패 — 자산 상세(ID: ${userAsset.id})에서 다시 추가하세요`,
                );
              },
            },
          );
        },
      },
    );
  }

  const assetErrorMessage = (() => {
    if (!createAssetMutation.isError) return null;
    const axiosErr = createAssetMutation.error as AxiosError<{ detail: string }>;
    const status = axiosErr.response?.status;
    if (status === 409) return "이미 등록된 자산입니다.";
    if (status === 404) return "심볼을 다시 선택하세요.";
    return axiosErr.response?.data?.detail ?? "자산 등록에 실패했습니다.";
  })();

  const isPending =
    createAssetMutation.isPending || createTransactionMutation.isPending;

  const today = new Date();
  const todayLocal = new Date(
    today.getTime() - today.getTimezoneOffset() * 60000,
  )
    .toISOString()
    .slice(0, 16);

  return (
    <div className="space-y-4">
      <Button
        type="button"
        variant="ghost"
        size="sm"
        onClick={onBack}
        className="gap-2"
        aria-label="심볼 검색으로 돌아가기"
      >
        <ArrowLeft className="h-4 w-4" aria-hidden="true" />
        돌아가기
      </Button>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">선택된 심볼</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          <div className="flex items-center gap-3">
            <div>
              <p className="font-semibold">{symbol.symbol}</p>
              <p className="text-sm text-muted-foreground">{symbol.name}</p>
            </div>
            <AssetTypeBadge assetType={symbol.assetType} />
          </div>
          <dl className="grid grid-cols-2 gap-x-4 gap-y-1 text-sm">
            <dt className="text-muted-foreground">거래소</dt>
            <dd>{symbol.exchange}</dd>
            <dt className="text-muted-foreground">통화</dt>
            <dd>{symbol.currency}</dd>
          </dl>
        </CardContent>
      </Card>

      <form onSubmit={handleSubmit} className="space-y-4" noValidate>
        {assetErrorMessage && (
          <p role="alert" className="text-sm font-medium text-destructive">
            {assetErrorMessage}
          </p>
        )}

        <div className="space-y-2">
          <Label htmlFor="memo">메모 (선택)</Label>
          <Input
            id="memo"
            name="memo"
            placeholder="예: 장기 보유, 분할 매수 예정..."
            maxLength={255}
          />
        </div>

        <div className="flex items-center gap-2">
          <input
            type="checkbox"
            id="skipTransaction"
            name="skipTransaction"
            checked={skipTransaction}
            onChange={(e) => setSkipTransaction(e.target.checked)}
            className="h-4 w-4 rounded border border-input"
          />
          <Label htmlFor="skipTransaction" className="cursor-pointer font-normal">
            첫 거래 기록 건너뛰기
          </Label>
        </div>

        {!skipTransaction && (
          <Card>
            <CardHeader>
              <CardTitle className="text-base">첫 거래 정보</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {txError && (
                <p role="alert" className="text-sm font-medium text-destructive">
                  {txError}
                </p>
              )}

              <div className="space-y-2">
                <Label htmlFor="quantity">수량</Label>
                <Input
                  id="quantity"
                  name="quantity"
                  type="text"
                  inputMode="decimal"
                  placeholder="예: 1.5"
                  aria-label="거래 수량"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="price">매수 단가</Label>
                <Input
                  id="price"
                  name="price"
                  type="text"
                  inputMode="decimal"
                  placeholder="예: 50000"
                  aria-label="매수 단가"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="tradedAt">매수일</Label>
                <Input
                  id="tradedAt"
                  name="tradedAt"
                  type="datetime-local"
                  defaultValue={todayLocal}
                  max={todayLocal}
                  aria-label="매수일"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="txMemo">거래 메모 (선택)</Label>
                <Input
                  id="txMemo"
                  name="txMemo"
                  placeholder="거래 관련 메모..."
                  maxLength={255}
                  aria-label="거래 메모"
                />
              </div>
            </CardContent>
          </Card>
        )}

        <Button
          type="submit"
          className="w-full"
          disabled={isPending}
          aria-busy={isPending}
        >
          {isPending ? "등록 중..." : "보유 자산으로 등록"}
        </Button>
      </form>
    </div>
  );
}

// ── Root component ────────────────────────────────────────────────────────────

export function AssetAddFlow() {
  const [step, dispatch] = useReducer(stepReducer, { kind: "search" });

  return (
    <div className="space-y-4">
      <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
        {STEP_LABELS[step.kind]}
      </p>

      {step.kind === "search" && (
        <SymbolSearch
          onSelect={(symbol) =>
            dispatch({ type: "SELECT_SYMBOL", symbol })
          }
          onRequestManualAdd={() => dispatch({ type: "REQUEST_MANUAL" })}
        />
      )}

      {step.kind === "manual" && (
        <SymbolCreateForm
          onCreated={(symbol) =>
            dispatch({ type: "SYMBOL_CREATED", symbol })
          }
          onBack={() => dispatch({ type: "BACK_TO_SEARCH" })}
        />
      )}

      {step.kind === "confirm" && (
        <ConfirmStep
          symbol={step.symbol}
          onBack={() => dispatch({ type: "BACK_TO_SEARCH" })}
        />
      )}
    </div>
  );
}
