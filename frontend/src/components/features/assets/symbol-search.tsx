"use client";

import { useState } from "react";
import { useSymbolSearch } from "@/hooks/use-assets";
import { AssetTypeBadge } from "./asset-type-badge";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Search, Plus } from "lucide-react";
import type { AssetSymbolResponse, AssetType } from "@/types/asset";

const ASSET_TYPE_OPTIONS: { label: string; value: AssetType | "" }[] = [
  { label: "전체", value: "" },
  { label: "암호화폐", value: "crypto" },
  { label: "국내주식", value: "kr_stock" },
  { label: "미국주식", value: "us_stock" },
];

interface SymbolSearchProps {
  onSelect: (symbol: AssetSymbolResponse) => void;
  onRequestManualAdd: () => void;
}

export function SymbolSearch({ onSelect, onRequestManualAdd }: SymbolSearchProps) {
  const [query, setQuery] = useState("");
  const [assetTypeFilter, setAssetTypeFilter] = useState<AssetType | "">("");

  const assetType: AssetType | undefined =
    assetTypeFilter === "" ? undefined : assetTypeFilter;

  const { data: results, isFetching } = useSymbolSearch(query, assetType);

  const hasQuery = query.length >= 1 || assetType != null;
  const hasResults = (results?.length ?? 0) > 0;

  return (
    <div className="space-y-4">
      <div className="space-y-2">
        <Label htmlFor="symbol-query">심볼 / 종목명 검색</Label>
        <div className="relative">
          <Search
            className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground"
            aria-hidden="true"
          />
          <Input
            id="symbol-query"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="BTC, AAPL, 삼성전자 ..."
            className="pl-9"
            aria-label="심볼 또는 종목명을 입력하세요"
          />
        </div>
      </div>

      <div className="space-y-2">
        <Label htmlFor="asset-type-filter">자산 유형</Label>
        <select
          id="asset-type-filter"
          value={assetTypeFilter}
          onChange={(e) =>
            setAssetTypeFilter(e.target.value as AssetType | "")
          }
          className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
          aria-label="자산 유형 필터"
        >
          {ASSET_TYPE_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
      </div>

      {hasQuery && (
        <div className="rounded-md border">
          {isFetching && (
            <p className="p-4 text-sm text-muted-foreground" role="status">
              검색 중...
            </p>
          )}

          {!isFetching && hasResults && (
            <ul role="listbox" aria-label="검색 결과">
              {results?.map((symbol) => (
                <li key={symbol.id}>
                  <button
                    type="button"
                    role="option"
                    aria-selected={false}
                    className="flex w-full items-center gap-3 px-4 py-3 text-left hover:bg-accent transition-colors border-b last:border-b-0"
                    onClick={() => onSelect(symbol)}
                  >
                    <div className="flex-1">
                      <p className="font-semibold text-sm">{symbol.symbol}</p>
                      <p className="text-xs text-muted-foreground">
                        {symbol.name}
                      </p>
                    </div>
                    <AssetTypeBadge assetType={symbol.assetType} />
                    <span className="text-xs text-muted-foreground">
                      {symbol.exchange}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          )}

          {!isFetching && !hasResults && (
            <div className="p-4 text-center space-y-3">
              <p className="text-sm text-muted-foreground">
                검색 결과가 없습니다.
              </p>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={onRequestManualAdd}
                className="gap-2"
              >
                <Plus className="h-4 w-4" aria-hidden="true" />
                직접 등록하기
              </Button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
