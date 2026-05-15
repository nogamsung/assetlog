import { apiClient } from "@/lib/api-client";

export type ImportSource =
  | "toss_investment"
  | "shinhan_investment"
  | "k_bank"
  | "upbit";

export interface ImportPreviewItem {
  type: "ParsedTrade" | "ParsedDividend" | "ParsedCashTx";
  externalId: string;
  tradedAt: string;
}

export interface ImportFileResult {
  insertedTrades: number;
  insertedDividends: number;
  insertedCashTxs: number;
  skippedDuplicate: number;
  skippedUnsupported: number;
  dryRun: boolean;
  preview: ImportPreviewItem[];
}

export interface ImportFileArgs {
  source: ImportSource;
  file: File;
  password?: string;
  dryRun: boolean;
}

// ── Raw snake_case shape ───────────────────────────────────────────────────────

interface RawImportPreviewItem {
  type: "ParsedTrade" | "ParsedDividend" | "ParsedCashTx";
  external_id: string;
  traded_at: string;
}

interface RawImportFileResult {
  inserted_trades: number;
  inserted_dividends: number;
  inserted_cash_txs: number;
  skipped_duplicate: number;
  skipped_unsupported: number;
  dry_run: boolean;
  preview: RawImportPreviewItem[];
}

function mapRaw(raw: RawImportFileResult): ImportFileResult {
  return {
    insertedTrades: raw.inserted_trades,
    insertedDividends: raw.inserted_dividends,
    insertedCashTxs: raw.inserted_cash_txs,
    skippedDuplicate: raw.skipped_duplicate,
    skippedUnsupported: raw.skipped_unsupported,
    dryRun: raw.dry_run,
    preview: raw.preview.map((p) => ({
      type: p.type,
      externalId: p.external_id,
      tradedAt: p.traded_at,
    })),
  };
}

// ── Public API ─────────────────────────────────────────────────────────────────

export async function importFile(args: ImportFileArgs): Promise<ImportFileResult> {
  const form = new FormData();
  form.append("file", args.file);
  if (args.password) form.append("password", args.password);

  const params = new URLSearchParams({
    source: args.source,
    dry_run: String(args.dryRun),
  });

  const response = await apiClient.post<RawImportFileResult>(
    `/api/integrations/import-file?${params.toString()}`,
    form,
    { headers: { "Content-Type": "multipart/form-data" } },
  );
  return mapRaw(response.data);
}

// ── Upbit sync ─────────────────────────────────────────────────────────────────

export interface UpbitSyncResult {
  fetched: number;
  inserted: number;
  skippedDuplicate: number;
  skippedNoSymbol: number;
}

interface RawUpbitSyncResult {
  fetched: number;
  inserted: number;
  skipped_duplicate: number;
  skipped_no_symbol: number;
}

export async function syncUpbit(): Promise<UpbitSyncResult> {
  const response = await apiClient.post<RawUpbitSyncResult>("/api/integrations/upbit/sync");
  const raw = response.data;
  return {
    fetched: raw.fetched,
    inserted: raw.inserted,
    skippedDuplicate: raw.skipped_duplicate,
    skippedNoSymbol: raw.skipped_no_symbol,
  };
}
