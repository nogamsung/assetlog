export interface NetWorthCurrencyEntry {
  cash: string;
  assets: string;
  total: string;
}

export interface NetWorthResponse {
  byCurrency: Record<string, NetWorthCurrencyEntry>;
  displayCurrency: string | null;
  convertedTotal: string | null;
}
