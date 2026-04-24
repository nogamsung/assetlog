import { apiClient } from "@/lib/api-client";
import type { FxRateEntry, FxRatesResponse } from "@/types/fx-rate";

// ── Raw shapes (snake_case from backend) ──────────────────────────────────────

interface RawFxRateEntry {
  base: string;
  quote: string;
  rate: string;
  fetched_at: string;
}

interface RawFxRatesResponse {
  rates: RawFxRateEntry[];
}

// ── Converter ─────────────────────────────────────────────────────────────────

function toFxRate(raw: RawFxRateEntry): FxRateEntry {
  return {
    base: raw.base,
    quote: raw.quote,
    rate: raw.rate,
    fetchedAt: raw.fetched_at,
  };
}

// ── Public API helper ─────────────────────────────────────────────────────────

export async function getFxRates(): Promise<FxRateEntry[]> {
  const response = await apiClient.get<RawFxRatesResponse>("/api/fx/rates");
  return response.data.rates.map(toFxRate);
}

// Re-export for convenience
export type { FxRatesResponse };
