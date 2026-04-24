export type HistoryPeriod = "1D" | "1W" | "1M" | "1Y" | "ALL";

export type HistoryBucket = "HOUR" | "DAY" | "WEEK" | "MONTH";

export interface HistoryPoint {
  timestamp: Date;
  value: string;       // Decimal as string
  costBasis: string;   // Decimal as string
}

export interface PortfolioHistoryResponse {
  currency: string;
  period: HistoryPeriod;
  bucket: HistoryBucket;
  points: HistoryPoint[];
}
