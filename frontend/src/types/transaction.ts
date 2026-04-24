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
  totalQuantity: string;  // Decimal as string
  avgCost: string;        // Decimal as string
  costBasis: string;      // Decimal as string
  transactionCount: number;
}
