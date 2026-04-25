import { apiClient } from "@/lib/api-client";
import type { SampleSeedResponse } from "@/types/sample";

// ── Raw shapes (snake_case from backend) ──────────────────────────────────────

interface RawSampleSeedResponse {
  seeded: boolean;
  reason: string | null;
  user_assets_created: number;
  transactions_created: number;
  symbols_created: number;
  symbols_reused: number;
}

// ── Converter ─────────────────────────────────────────────────────────────────

function toSampleSeedResponse(raw: RawSampleSeedResponse): SampleSeedResponse {
  return {
    seeded: raw.seeded,
    reason: raw.reason,
    userAssetsCreated: raw.user_assets_created,
    transactionsCreated: raw.transactions_created,
    symbolsCreated: raw.symbols_created,
    symbolsReused: raw.symbols_reused,
  };
}

// ── Public API helper ──────────────────────────────────────────────────────────

export async function seedSampleData(): Promise<SampleSeedResponse> {
  const response = await apiClient.post<RawSampleSeedResponse>(
    "/api/sample/seed",
  );
  return toSampleSeedResponse(response.data);
}
