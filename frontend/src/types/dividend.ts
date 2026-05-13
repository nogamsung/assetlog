export interface DividendEntry {
  id: number;
  assetSymbolId: number;
  exDate: string;
  payDate: string | null;
  amount: string;
  currency: string;
}

export interface DividendSummaryEntry {
  assetSymbolId: number;
  totalAmount: string;
  currency: string;
}

export interface DividendListResponse {
  dividends: DividendEntry[];
  summary: DividendSummaryEntry[];
}
