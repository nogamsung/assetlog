import { apiClient } from "@/lib/api-client";
import { snakeToCamel } from "@/lib/case";
import type { TagBreakdownEntry, TagBreakdownResponse } from "@/types/tag-breakdown";

// ── Raw shapes (snake_case from backend) ──────────────────────────────────────

interface RawTagBreakdownEntry {
  tag: string | null;
  transaction_count: number;
  buy_count: number;
  sell_count: number;
  total_bought_value_by_currency: Record<string, string>;
  total_sold_value_by_currency: Record<string, string>;
}

interface RawTagBreakdownResponse {
  entries: RawTagBreakdownEntry[];
}

// ── Converters ─────────────────────────────────────────────────────────────────

function toTagBreakdownResponse(raw: RawTagBreakdownResponse): TagBreakdownResponse {
  return {
    entries: raw.entries.map(
      (entry) => snakeToCamel(entry) as unknown as TagBreakdownEntry,
    ),
  };
}

// ── Public API helpers ─────────────────────────────────────────────────────────

export async function getTagBreakdown(): Promise<TagBreakdownResponse> {
  const response = await apiClient.get<RawTagBreakdownResponse>(
    "/api/portfolio/tags/breakdown",
  );
  return toTagBreakdownResponse(response.data);
}
