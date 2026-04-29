export interface IndexQuote {
  symbol: string;
  name: string;
  currency: string;
  price: string;
  change: string;
  changePct: string;
  fetchedAt: string;
}

export interface IndicesResponse {
  indices: IndexQuote[];
}
