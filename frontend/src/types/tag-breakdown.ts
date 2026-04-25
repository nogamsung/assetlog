export interface TagBreakdownEntry {
  tag: string | null;
  transactionCount: number;
  buyCount: number;
  sellCount: number;
  totalBoughtValueByCurrency: Record<string, string>;
  totalSoldValueByCurrency: Record<string, string>;
}

export interface TagBreakdownResponse {
  entries: TagBreakdownEntry[];
}
