export type TransactionType = "buy" | "sell";

export interface CsvImportError {
  row: number;
  field: string | null;
  message: string;
}

export interface TransactionImportResponse {
  importedCount: number;
  preview: TransactionResponse[];
}

export interface CsvImportValidationErrorBody {
  detail: string;
  errors: CsvImportError[];
}

export interface TransactionResponse {
  id: number;
  userAssetId: number;
  type: TransactionType;
  quantity: string;       // Decimal as string
  price: string;          // Decimal as string
  tradedAt: string;       // ISO datetime string
  memo: string | null;
  tag: string | null;     // ADDED
  createdAt: string;      // ISO datetime string
}

export interface TransactionWithSymbolResponse extends TransactionResponse {
  externalSource: string | null;
  externalId: string | null;
  symbol: string;
  assetType: "kr_stock" | "us_stock" | "crypto";
  currency: string;
  name: string | null;
  exchange: string | null;
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
