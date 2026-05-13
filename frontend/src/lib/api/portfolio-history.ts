import { apiClient } from "@/lib/api-client";
import type {
  HistoryPeriod,
  HistoryBucket,
  HistoryPoint,
  PortfolioHistoryResponse,
} from "@/types/portfolio-history";

// ── Raw shapes (snake_case from backend) ──────────────────────────────────────

interface RawHistoryPoint {
  timestamp: string;   // ISO 8601 string
  value: string;       // Decimal as string
  cost_basis: string;  // Decimal as string
}

interface RawPortfolioHistoryResponse {
  currency: string;
  period: HistoryPeriod;
  bucket: HistoryBucket;
  points: RawHistoryPoint[];
}

// ── Converters ─────────────────────────────────────────────────────────────────

function toHistoryPoint(raw: RawHistoryPoint): HistoryPoint {
  return {
    timestamp: new Date(raw.timestamp),
    value: raw.value,
    costBasis: raw.cost_basis,
  };
}

// ── Public API helpers ─────────────────────────────────────────────────────────

export interface GetPortfolioHistoryParams {
  period: HistoryPeriod;
  currency: string;
}

export async function getPortfolioHistory(
  params: GetPortfolioHistoryParams,
): Promise<PortfolioHistoryResponse> {
  const response = await apiClient.get<RawPortfolioHistoryResponse>(
    "/api/portfolio/history",
    {
      params: {
        period: params.period,
        currency: params.currency,
      },
    },
  );
  const raw = response.data;
  return {
    currency: raw.currency,
    period: raw.period,
    bucket: raw.bucket,
    points: raw.points.map(toHistoryPoint),
  };
}

export interface BackfillResult {
  symbolsAttempted: number;
  symbolsSkipped: number;
  pointsInserted: number;
}

interface RawBackfillResult {
  symbols_attempted: number;
  symbols_skipped: number;
  points_inserted: number;
}

export async function backfillPortfolioHistory(): Promise<BackfillResult> {
  const response = await apiClient.post<RawBackfillResult>(
    "/api/portfolio/history/backfill",
  );
  const r = response.data;
  return {
    symbolsAttempted: r.symbols_attempted,
    symbolsSkipped: r.symbols_skipped,
    pointsInserted: r.points_inserted,
  };
}
