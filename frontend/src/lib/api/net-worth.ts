import { apiClient } from "@/lib/api-client";
import type { NetWorthResponse } from "@/types/net-worth";

interface RawCurrencyEntry {
  cash: string;
  assets: string;
  total: string;
}

interface RawNetWorthResponse {
  by_currency: Record<string, RawCurrencyEntry>;
  display_currency: string | null;
  converted_total: string | null;
}

export async function getNetWorth(
  displayCurrency?: string,
): Promise<NetWorthResponse> {
  const { data } = await apiClient.get<RawNetWorthResponse>(
    "/api/portfolio/net-worth",
    { params: { display_currency: displayCurrency } },
  );
  return {
    byCurrency: data.by_currency,
    displayCurrency: data.display_currency,
    convertedTotal: data.converted_total,
  };
}
