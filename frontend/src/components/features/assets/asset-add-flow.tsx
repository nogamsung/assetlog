"use client";

import { useReducer } from "react";
import { type AxiosError } from "axios";
import { useCreateUserAsset } from "@/hooks/use-assets";
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
  const createMutation = useCreateUserAsset();

  function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const formData = new FormData(e.currentTarget);
    const memoValue = (formData.get("memo") as string | null) ?? "";
    const memo = memoValue.trim() === "" ? null : memoValue.trim();

    createMutation.mutate({ assetSymbolId: symbol.id, memo });
  }

  const errorMessage = (() => {
    if (!createMutation.isError) return null;
    const axiosErr = createMutation.error as AxiosError<{ detail: string }>;
    const status = axiosErr.response?.status;
    if (status === 409) return "이미 등록된 자산입니다.";
    if (status === 404) return "심볼을 다시 선택하세요.";
    return axiosErr.response?.data?.detail ?? "자산 등록에 실패했습니다.";
  })();

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
        {errorMessage && (
          <p role="alert" className="text-sm font-medium text-destructive">
            {errorMessage}
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

        <Button
          type="submit"
          className="w-full"
          disabled={createMutation.isPending}
          aria-busy={createMutation.isPending}
        >
          {createMutation.isPending ? "등록 중..." : "보유 자산으로 등록"}
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
