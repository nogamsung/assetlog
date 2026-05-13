import { apiClient } from "@/lib/api-client";
import { snakeToCamel } from "@/lib/case";
import type {
  DividendListResponse,
  DividendEntry,
  DividendSummaryEntry,
} from "@/types/dividend";

interface RawDividendEntry {
  id: number;
  asset_symbol_id: number;
  ex_date: string;
  pay_date: string | null;
  amount: string;
  currency: string;
}

interface RawDividendSummary {
  asset_symbol_id: number;
  total_amount: string;
  currency: string;
}

interface RawDividendListResponse {
  dividends: RawDividendEntry[];
  summary: RawDividendSummary[];
}

export async function listDividends(params: {
  assetSymbolId?: number;
  from?: string;
  to?: string;
}): Promise<DividendListResponse> {
  const { data } = await apiClient.get<RawDividendListResponse>("/api/dividends", {
    params: {
      asset_symbol_id: params.assetSymbolId,
      from: params.from,
      to: params.to,
    },
  });
  return {
    dividends: data.dividends.map(
      (d) => snakeToCamel(d) as unknown as DividendEntry,
    ),
    summary: data.summary.map(
      (s) => snakeToCamel(s) as unknown as DividendSummaryEntry,
    ),
  };
}
