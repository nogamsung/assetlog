import type { AssetType, AssetSymbolResponse } from "@/types/asset";

export type CurrencyAmountMap = Record<string, string>; // Decimal as string

export interface PnlEntry {
  abs: string;
  pct: number;
}

export interface AllocationEntry {
  assetType: AssetType;
  pct: number;
}

export interface PortfolioSummary {
  totalValueByCurrency: CurrencyAmountMap;
  totalCostByCurrency: CurrencyAmountMap;
  pnlByCurrency: Record<string, PnlEntry>;
  allocation: AllocationEntry[];
  lastPriceRefreshedAt: string | null;
  pendingCount: number;
  staleCount: number;
}

export interface HoldingResponse {
  userAssetId: number;
  assetSymbol: AssetSymbolResponse;
  quantity: string;           // Decimal as string
  avgCost: string;            // Decimal as string
  costBasis: string;          // Decimal as string
  latestPrice: string | null; // Decimal as string | null
  latestValue: string | null; // Decimal as string | null
  pnlAbs: string | null;      // Decimal as string | null
  pnlPct: number | null;
  weightPct: number;
  lastPriceRefreshedAt: string | null;
  isStale: boolean;
  isPending: boolean;
}
