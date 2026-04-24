export type TransactionType = "buy" | "sell";

export interface TransactionResponse {
  id: number;
  userAssetId: number;
  type: TransactionType;
  quantity: string;       // Decimal as string
  price: string;          // Decimal as string
  tradedAt: string;       // ISO datetime string
  memo: string | null;
  createdAt: string;      // ISO datetime string
}

export interface UserAssetSummaryResponse {
  userAssetId: number;
  totalBoughtQuantity: string;  // MODIFIED — Decimal as string
  totalSoldQuantity: string;    // ADDED
  remainingQuantity: string;    // ADDED
  avgBuyPrice: string;          // ADDED — Decimal as string
  totalInvested: string;        // ADDED — Decimal as string
  totalSoldValue: string;       // ADDED — Decimal as string
  realizedPnl: string;          // ADDED — Decimal as string
  transactionCount: number;
  currency: string;             // ADDED
}
