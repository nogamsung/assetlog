import type { TransactionResponse } from "@/types/transaction";

export interface BulkTransactionRow {
  symbol: string;
  exchange: string;
  type: "buy" | "sell";
  quantity: string;
  price: string;
  traded_at: string;
  memo?: string | null;
  tag?: string | null;
}

export interface BulkTransactionRequest {
  rows: BulkTransactionRow[];
}

export interface BulkTransactionResponse {
  imported_count: number;
  preview: TransactionResponse[];
}

export interface BulkTransactionError {
  row: number;
  field: string | null;
  message: string;
}

export interface BulkTransactionErrorBody {
  detail: string;
  errors: BulkTransactionError[];
}
