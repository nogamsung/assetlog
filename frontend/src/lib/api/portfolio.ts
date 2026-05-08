import { apiClient } from "@/lib/api-client";
import type { AssetType } from "@/types/asset";
import type {
  PortfolioSummary,
  HoldingResponse,
  CurrencyAmountMap,
  PnlEntry,
  AllocationEntry,
  FxWarning,
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
  converted_price_pnl: string | null;  // ADDED
  converted_fx_pnl: string | null;     // ADDED
  fx_warning: FxWarning;               // ADDED
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
  // 환차손익 분리 필드 — ADDED
  price_pnl: string | null;  // ADDED
  fx_pnl: string | null;     // ADDED
  fx_warning: FxWarning;     // ADDED
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
    convertedPricePnl: raw.converted_price_pnl ?? null,  // ADDED
    convertedFxPnl:    raw.converted_fx_pnl ?? null,     // ADDED
    fxWarning:         raw.fx_warning ?? null,            // ADDED
  };
}

function toHolding(raw: RawHolding): HoldingResponse { // MODIFIED — explicit mapping for type safety
  return {
    userAssetId:          raw.user_asset_id,
    assetSymbol: {
      id:        raw.asset_symbol.id,
      assetType: raw.asset_symbol.asset_type,
      symbol:    raw.asset_symbol.symbol,
      exchange:  raw.asset_symbol.exchange,
      name:      raw.asset_symbol.name,
      currency:  raw.asset_symbol.currency,
      createdAt: raw.asset_symbol.created_at,
      updatedAt: raw.asset_symbol.updated_at,
    },
    quantity:             raw.quantity,
    avgCost:              raw.avg_cost,
    costBasis:            raw.cost_basis,
    realizedPnl:          raw.realized_pnl,
    latestPrice:          raw.latest_price,
    latestValue:          raw.latest_value,
    pnlAbs:               raw.pnl_abs,
    pnlPct:               raw.pnl_pct,
    weightPct:            raw.weight_pct,
    lastPriceRefreshedAt: raw.last_price_refreshed_at,
    isStale:              raw.is_stale,
    isPending:            raw.is_pending,
    convertedLatestValue: raw.converted_latest_value ?? null,
    convertedCostBasis:   raw.converted_cost_basis ?? null,
    convertedPnlAbs:      raw.converted_pnl_abs ?? null,
    convertedRealizedPnl: raw.converted_realized_pnl ?? null,
    displayCurrency:      raw.display_currency ?? null,
    pricePnl:             raw.price_pnl ?? null,  // ADDED
    fxPnl:                raw.fx_pnl ?? null,     // ADDED
    fxWarning:            raw.fx_warning ?? null,  // ADDED
  };
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
