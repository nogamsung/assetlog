"use client";

import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { type AxiosError } from "axios";
import { useMutation } from "@tanstack/react-query";
import { createSymbol } from "@/lib/api/asset";
import { symbolCreateSchema, type SymbolCreateInput } from "@/lib/schemas/asset";
import type { AssetSymbolResponse } from "@/types/asset";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import type { ApiError } from "@/lib/api-client";
import { ArrowLeft } from "lucide-react";

const ASSET_TYPE_OPTIONS = [
  { value: "crypto", label: "암호화폐" },
  { value: "kr_stock", label: "국내주식" },
  { value: "us_stock", label: "미국주식" },
] as const;

interface SymbolCreateFormProps {
  onCreated: (symbol: AssetSymbolResponse) => void;
  onBack: () => void;
}

export function SymbolCreateForm({ onCreated, onBack }: SymbolCreateFormProps) {
  const form = useForm<SymbolCreateInput>({
    resolver: zodResolver(symbolCreateSchema),
    defaultValues: {
      assetType: "crypto",
      symbol: "",
      exchange: "",
      name: "",
      currency: "",
    },
  });

  const createMutation = useMutation<AssetSymbolResponse, Error, SymbolCreateInput>({
    mutationFn: createSymbol,
    onSuccess: (created) => {
      onCreated(created);
    },
    onError: (err) => {
      const apiErr = err as unknown as ApiError;
      if (apiErr.status === 409) {
        form.setError("root", { message: "이미 등록된 심볼입니다." });
      } else {
        const axiosErr = err as AxiosError<{ detail: string }>;
        const message =
          axiosErr.response?.data?.detail ?? "심볼 등록에 실패했습니다.";
        form.setError("root", { message });
      }
    },
  });

  function onSubmit(data: SymbolCreateInput) {
    createMutation.mutate(data);
  }

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
        심볼 검색으로 돌아가기
      </Button>

      <Form {...form}>
        <form onSubmit={form.handleSubmit(onSubmit)} noValidate className="space-y-4">
          {form.formState.errors.root && (
            <p role="alert" className="text-sm font-medium text-destructive">
              {form.formState.errors.root.message}
            </p>
          )}

          <FormField
            control={form.control}
            name="assetType"
            render={({ field }) => (
              <FormItem>
                <FormLabel>자산 유형</FormLabel>
                <FormControl>
                  <select
                    {...field}
                    className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
                    aria-required="true"
                  >
                    {ASSET_TYPE_OPTIONS.map((opt) => (
                      <option key={opt.value} value={opt.value}>
                        {opt.label}
                      </option>
                    ))}
                  </select>
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />

          <FormField
            control={form.control}
            name="symbol"
            render={({ field }) => (
              <FormItem>
                <FormLabel>심볼</FormLabel>
                <FormControl>
                  <Input
                    {...field}
                    placeholder="예: BTC, 005930, AAPL"
                    aria-required="true"
                  />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />

          <FormField
            control={form.control}
            name="exchange"
            render={({ field }) => (
              <FormItem>
                <FormLabel>거래소</FormLabel>
                <FormControl>
                  <Input
                    {...field}
                    placeholder="예: BINANCE, KRX, NASDAQ"
                    aria-required="true"
                  />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />

          <FormField
            control={form.control}
            name="name"
            render={({ field }) => (
              <FormItem>
                <FormLabel>종목명</FormLabel>
                <FormControl>
                  <Input
                    {...field}
                    placeholder="예: Bitcoin, 삼성전자, Apple Inc."
                    aria-required="true"
                  />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />

          <FormField
            control={form.control}
            name="currency"
            render={({ field }) => (
              <FormItem>
                <FormLabel>통화</FormLabel>
                <FormControl>
                  <Input
                    {...field}
                    placeholder="예: USD, KRW, USDT"
                    aria-required="true"
                  />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />

          <Button
            type="submit"
            className="w-full"
            disabled={createMutation.isPending}
            aria-busy={createMutation.isPending}
          >
            {createMutation.isPending ? "등록 중..." : "심볼 등록"}
          </Button>
        </form>
      </Form>
    </div>
  );
}
