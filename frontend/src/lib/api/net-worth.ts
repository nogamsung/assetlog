import { apiClient } from "@/lib/api-client";
import type { NetWorthResponse } from "@/types/net-worth";

interface RawCurrencyEntry {
  cash: string;
  assets: string;
  total: string;
}

interface RawNetWorthResponse {
  by_currency: Record<string, RawCurrencyEntry>;
  by_account: Record<string, Record<string, string>>;
  display_currency: string | null;
  converted_total: string | null;
  converted_partial?: boolean;
  missing_fx_currencies?: string[];
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
    byAccount: data.by_account ?? {},
    displayCurrency: data.display_currency,
    convertedTotal: data.converted_total,
    convertedPartial: data.converted_partial ?? false,
    missingFxCurrencies: data.missing_fx_currencies ?? [],
  };
}
