import { apiClient } from "@/lib/api-client";
import type { IndexQuote } from "@/types/market-index";

interface RawIndexQuote {
  symbol: string;
  name: string;
  currency: string;
  price: string;
  change: string;
  change_pct: string;
  fetched_at: string;
}

interface RawIndicesResponse {
  indices: RawIndexQuote[];
}

function toIndexQuote(raw: RawIndexQuote): IndexQuote {
  return {
    symbol: raw.symbol,
    name: raw.name,
    currency: raw.currency,
    price: raw.price,
    change: raw.change,
    changePct: raw.change_pct,
    fetchedAt: raw.fetched_at,
  };
}

export async function getMarketIndices(): Promise<IndexQuote[]> {
  const response = await apiClient.get<RawIndicesResponse>("/api/market/indices");
  return response.data.indices.map(toIndexQuote);
}
