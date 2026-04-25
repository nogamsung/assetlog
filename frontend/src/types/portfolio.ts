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
  realizedPnlByCurrency: CurrencyAmountMap;
  allocation: AllocationEntry[];
  lastPriceRefreshedAt: string | null;
  pendingCount: number;
  staleCount: number;
  // 환산 필드 (convert_to 파라미터 사용 시)
  convertedTotalValue: string | null;
  convertedTotalCost: string | null;
  convertedPnlAbs: string | null;
  convertedRealizedPnl: string | null;
  displayCurrency: string | null;
}

export interface HoldingResponse {
  userAssetId: number;
  assetSymbol: AssetSymbolResponse;
  quantity: string;           // Decimal as string — remaining qty
  avgCost: string;            // Decimal as string
  costBasis: string;          // Decimal as string — remaining basis
  realizedPnl: string;        // ADDED — Decimal as string
  latestPrice: string | null; // Decimal as string | null
  latestValue: string | null; // Decimal as string | null
  pnlAbs: string | null;      // Decimal as string | null — unrealized
  pnlPct: number | null;
  weightPct: number;
  lastPriceRefreshedAt: string | null;
  isStale: boolean;
  isPending: boolean;
  // 환산 필드 (convert_to 파라미터 사용 시) — ADDED
  convertedLatestValue: string | null;
  convertedCostBasis: string | null;
  convertedPnlAbs: string | null;
  convertedRealizedPnl: string | null;
  displayCurrency: string | null;
}
