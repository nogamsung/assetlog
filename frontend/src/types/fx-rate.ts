export interface FxRateEntry {
  base: string;
  quote: string;
  rate: string;
  fetchedAt: string;
}

export interface FxRatesResponse {
  rates: FxRateEntry[];
}
