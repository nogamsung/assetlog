import { apiClient } from "@/lib/api-client";
import { snakeToCamel } from "@/lib/case";
import type {
  TransactionResponse,
  UserAssetSummaryResponse,
  TransactionImportResponse,
} from "@/types/transaction";
import type { TransactionCreateInput } from "@/lib/schemas/transaction";

// ── Raw shapes (snake_case from backend) ──────────────────────────────────────

interface RawTransactionImportResponse {
  imported_count: number;
  preview: RawTransactionResponse[];
}

interface RawTransactionResponse {
  id: number;
  user_asset_id: number;
  type: "buy" | "sell";
  quantity: string;
  price: string;
  traded_at: string;
  memo: string | null;
  tag: string | null;     // ADDED
  created_at: string;
}

interface RawUserAssetSummaryResponse {
  user_asset_id: number;
  total_bought_quantity: string; // MODIFIED
  total_sold_quantity: string;   // ADDED
  remaining_quantity: string;    // ADDED
  avg_buy_price: string;         // ADDED
  total_invested: string;        // ADDED
  total_sold_value: string;      // ADDED
  realized_pnl: string;          // ADDED
  transaction_count: number;
  currency: string;              // ADDED
}

// ── Converters ─────────────────────────────────────────────────────────────────

function toTransaction(raw: RawTransactionResponse): TransactionResponse {
  return snakeToCamel(raw) as unknown as TransactionResponse;
}

function toUserAssetSummary(raw: RawUserAssetSummaryResponse): UserAssetSummaryResponse {
  return snakeToCamel(raw) as unknown as UserAssetSummaryResponse;
}

// ── Public API helpers ─────────────────────────────────────────────────────────

export interface ListTransactionsParams {
  limit?: number;
  offset?: number;
  tag?: string;           // ADDED
}

export async function listUserTags(): Promise<string[]> {  // ADDED
  const response = await apiClient.get<string[]>("/api/user-assets/transactions/tags");
  return response.data;
}

export async function createTransaction(
  userAssetId: number,
  data: TransactionCreateInput,
): Promise<TransactionResponse> {
  const payload = {
    type: data.type,
    quantity: data.quantity,
    price: data.price,
    traded_at: data.tradedAt.toISOString(),
    memo: data.memo ?? null,
    tag: data.tag?.trim() || null,  // ADDED — 빈 문자열 → null
  };
  const response = await apiClient.post<RawTransactionResponse>(
    `/api/user-assets/${userAssetId}/transactions`,
    payload,
  );
  return toTransaction(response.data);
}

export async function listTransactions(
  userAssetId: number,
  params: ListTransactionsParams = {},
): Promise<TransactionResponse[]> {
  const query: Record<string, number | string> = {};
  if (params.limit !== undefined) query["limit"] = params.limit;
  if (params.offset !== undefined) query["offset"] = params.offset;
  if (params.tag !== undefined) query["tag"] = params.tag;  // ADDED

  const response = await apiClient.get<RawTransactionResponse[]>(
    `/api/user-assets/${userAssetId}/transactions`,
    { params: query },
  );
  return response.data.map(toTransaction);
}

export async function updateTransaction( // ADDED
  userAssetId: number,
  transactionId: number,
  data: TransactionCreateInput,
): Promise<TransactionResponse> {
  const payload = {
    type: data.type,
    quantity: data.quantity,
    price: data.price,
    traded_at: data.tradedAt.toISOString(),
    memo: data.memo ?? null,
    tag: data.tag?.trim() || null,  // ADDED — 빈 문자열 → null
  };
  const response = await apiClient.put<RawTransactionResponse>(
    `/api/user-assets/${userAssetId}/transactions/${transactionId}`,
    payload,
  );
  return toTransaction(response.data);
}

export async function deleteTransaction(
  userAssetId: number,
  txId: number,
): Promise<void> {
  await apiClient.delete(`/api/user-assets/${userAssetId}/transactions/${txId}`);
}

export async function importTransactionsCsv(
  userAssetId: number,
  file: File,
): Promise<TransactionImportResponse> {
  const form = new FormData();
  form.append("file", file);
  const response = await apiClient.post<RawTransactionImportResponse>(
    `/api/user-assets/${userAssetId}/transactions/import`,
    form,
    { headers: { "Content-Type": "multipart/form-data" } },
  );
  return {
    importedCount: response.data.imported_count,
    preview: response.data.preview.map(toTransaction),
  };
}

export async function getAssetSummary(
  userAssetId: number,
): Promise<UserAssetSummaryResponse> {
  const response = await apiClient.get<RawUserAssetSummaryResponse>(
    `/api/user-assets/${userAssetId}/summary`,
  );
  return toUserAssetSummary(response.data);
}
