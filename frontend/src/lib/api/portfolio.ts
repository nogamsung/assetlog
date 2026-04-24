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
  asset_type: AssetType;
  pct: number;
}

interface RawPortfolioSummary {
  total_value_by_currency: CurrencyAmountMap;
  total_cost_by_currency: CurrencyAmountMap;
  pnl_by_currency: Record<string, RawPnlEntry>;
  allocation: RawAllocationEntry[];
  last_price_refreshed_at: string | null;
  pending_count: number;
  stale_count: number;
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
  latest_price: string | null;
  latest_value: string | null;
  pnl_abs: string | null;
  pnl_pct: number | null;
  weight_pct: number;
  last_price_refreshed_at: string | null;
  is_stale: boolean;
  is_pending: boolean;
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
    allocation,
    lastPriceRefreshedAt: raw.last_price_refreshed_at,
    pendingCount: raw.pending_count,
    staleCount: raw.stale_count,
  };
}

function toHolding(raw: RawHolding): HoldingResponse {
  return snakeToCamel(raw) as unknown as HoldingResponse;
}

// ── Public API helpers ─────────────────────────────────────────────────────────

export async function getPortfolioSummary(): Promise<PortfolioSummary> {
  const response = await apiClient.get<RawPortfolioSummary>(
    "/api/portfolio/summary",
  );
  return toPortfolioSummary(response.data);
}

export async function getPortfolioHoldings(): Promise<HoldingResponse[]> {
  const response = await apiClient.get<RawHolding[]>("/api/portfolio/holdings");
  return response.data.map(toHolding);
}
