import { apiClient } from "@/lib/api-client";
import { snakeToCamel } from "@/lib/case";
import type { AssetType } from "@/types/asset";
import type {
  PortfolioSummary,
  HoldingResponse,
  CurrencyAmountMap,
  PnlEntry,
  AllocationEntry,
} from "@/types/portfolio";

// ── Raw shapes (snake_case from backend) ──────────────────────────────────────

interface RawPnlEntry {
  abs: string;
  pct: number;
}

interface RawAllocationEntry {
  asset_type: AssetType | "cash";
  pct: number;
}

interface RawPortfolioSummary {
  total_value_by_currency: CurrencyAmountMap;
  total_cost_by_currency: CurrencyAmountMap;
  pnl_by_currency: Record<string, RawPnlEntry>;
  realized_pnl_by_currency: CurrencyAmountMap;
  allocation: RawAllocationEntry[];
  last_price_refreshed_at: string | null;
  pending_count: number;
  stale_count: number;
  converted_total_value: string | null;
  converted_total_cost: string | null;
  converted_pnl_abs: string | null;
  converted_realized_pnl: string | null;
  display_currency: string | null;
  cash_total_by_currency?: CurrencyAmountMap;
}

interface RawAssetSymbol {
  id: number;
  asset_type: AssetType;
  symbol: string;
  exchange: string;
  name: string;
  currency: string;
  created_at: string;
  updated_at: string;
}

interface RawHolding {
  user_asset_id: number;
  asset_symbol: RawAssetSymbol;
  quantity: string;
  avg_cost: string;
  cost_basis: string;
  realized_pnl: string; // ADDED
  latest_price: string | null;
  latest_value: string | null;
  pnl_abs: string | null;
  pnl_pct: number | null;
  weight_pct: number;
  last_price_refreshed_at: string | null;
  is_stale: boolean;
  is_pending: boolean;
  // 환산 필드 (convert_to 파라미터 사용 시) — ADDED
  converted_latest_value: string | null;
  converted_cost_basis: string | null;
  converted_pnl_abs: string | null;
  converted_realized_pnl: string | null;
  display_currency: string | null;
}

// ── Converters ─────────────────────────────────────────────────────────────────

function toPortfolioSummary(raw: RawPortfolioSummary): PortfolioSummary {
  const pnlByCurrency: Record<string, PnlEntry> = {};
  for (const [currency, rawPnl] of Object.entries(raw.pnl_by_currency)) {
    pnlByCurrency[currency] = { abs: rawPnl.abs, pct: rawPnl.pct };
  }

  const allocation: AllocationEntry[] = raw.allocation.map((a) => ({
    assetType: a.asset_type,
    pct: a.pct,
  }));

  return {
    totalValueByCurrency: raw.total_value_by_currency,
    totalCostByCurrency: raw.total_cost_by_currency,
    pnlByCurrency,
    realizedPnlByCurrency: raw.realized_pnl_by_currency,
    allocation,
    lastPriceRefreshedAt: raw.last_price_refreshed_at,
    pendingCount: raw.pending_count,
    staleCount: raw.stale_count,
    convertedTotalValue: raw.converted_total_value ?? null,
    convertedTotalCost: raw.converted_total_cost ?? null,
    convertedPnlAbs: raw.converted_pnl_abs ?? null,
    convertedRealizedPnl: raw.converted_realized_pnl ?? null,
    displayCurrency: raw.display_currency ?? null,
    cashTotalByCurrency: raw.cash_total_by_currency ?? {},
  };
}

function toHolding(raw: RawHolding): HoldingResponse {
  return snakeToCamel(raw) as unknown as HoldingResponse;
}

// ── Public API helpers ─────────────────────────────────────────────────────────

export async function getPortfolioSummary(
  options: { convertTo?: string } = {},
): Promise<PortfolioSummary> {
  const url =
    options.convertTo != null
      ? `/api/portfolio/summary?convert_to=${encodeURIComponent(options.convertTo)}`
      : "/api/portfolio/summary";
  const response = await apiClient.get<RawPortfolioSummary>(url);
  return toPortfolioSummary(response.data);
}

export async function getPortfolioHoldings( // MODIFIED
  options: { convertTo?: string } = {},
): Promise<HoldingResponse[]> {
  const url =
    options.convertTo != null
      ? `/api/portfolio/holdings?convert_to=${encodeURIComponent(options.convertTo)}`
      : "/api/portfolio/holdings";
  const response = await apiClient.get<RawHolding[]>(url);
  return response.data.map(toHolding);
}
