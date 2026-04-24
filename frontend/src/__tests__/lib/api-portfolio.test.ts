import { getPortfolioSummary, getPortfolioHoldings } from "@/lib/api/portfolio";
import { apiClient } from "@/lib/api-client";
import type { PortfolioSummary, HoldingResponse } from "@/types/portfolio";

jest.mock("@/lib/api-client", () => ({
  apiClient: {
    get: jest.fn(),
  },
}));

const mockedGet = jest.mocked(apiClient.get);

const rawSummary = {
  total_value_by_currency: { KRW: "12500000.00", USD: "8200.12" },
  total_cost_by_currency: { KRW: "11000000.00", USD: "7500.00" },
  pnl_by_currency: {
    KRW: { abs: "1500000.00", pct: 13.64 },
    USD: { abs: "700.12", pct: 9.34 },
  },
  realized_pnl_by_currency: { KRW: "0.000000", USD: "0.000000" },
  allocation: [
    { asset_type: "kr_stock", pct: 42.1 },
    { asset_type: "us_stock", pct: 57.9 },
  ],
  last_price_refreshed_at: "2026-04-24T09:00:00+09:00",
  pending_count: 1,
  stale_count: 0,
};

const expectedSummary: PortfolioSummary = {
  totalValueByCurrency: { KRW: "12500000.00", USD: "8200.12" },
  totalCostByCurrency: { KRW: "11000000.00", USD: "7500.00" },
  pnlByCurrency: {
    KRW: { abs: "1500000.00", pct: 13.64 },
    USD: { abs: "700.12", pct: 9.34 },
  },
  realizedPnlByCurrency: { KRW: "0.000000", USD: "0.000000" },
  allocation: [
    { assetType: "kr_stock", pct: 42.1 },
    { assetType: "us_stock", pct: 57.9 },
  ],
  lastPriceRefreshedAt: "2026-04-24T09:00:00+09:00",
  pendingCount: 1,
  staleCount: 0,
};

const rawHolding = {
  user_asset_id: 12,
  asset_symbol: {
    id: 1,
    asset_type: "us_stock",
    symbol: "AAPL",
    exchange: "NASDAQ",
    name: "Apple Inc.",
    currency: "USD",
    created_at: "2024-01-01T00:00:00Z",
    updated_at: "2024-01-01T00:00:00Z",
  },
  quantity: "10.0000000000",
  avg_cost: "170.500000",
  cost_basis: "1705.00",
  realized_pnl: "0.000000",
  latest_price: "175.200000",
  latest_value: "1752.00",
  pnl_abs: "47.00",
  pnl_pct: 2.76,
  weight_pct: 21.4,
  last_price_refreshed_at: "2026-04-24T09:00:00+09:00",
  is_stale: false,
  is_pending: false,
};

const expectedHolding: HoldingResponse = {
  userAssetId: 12,
  assetSymbol: {
    id: 1,
    assetType: "us_stock",
    symbol: "AAPL",
    exchange: "NASDAQ",
    name: "Apple Inc.",
    currency: "USD",
    createdAt: "2024-01-01T00:00:00Z",
    updatedAt: "2024-01-01T00:00:00Z",
  },
  quantity: "10.0000000000",
  avgCost: "170.500000",
  costBasis: "1705.00",
  realizedPnl: "0.000000",
  latestPrice: "175.200000",
  latestValue: "1752.00",
  pnlAbs: "47.00",
  pnlPct: 2.76,
  weightPct: 21.4,
  lastPriceRefreshedAt: "2026-04-24T09:00:00+09:00",
  isStale: false,
  isPending: false,
};

describe("getPortfolioSummary", () => {
  beforeEach(() => jest.clearAllMocks());

  it("GET /api/portfolio/summary 를 호출하고 camelCase 변환된 객체를 반환한다", async () => {
    mockedGet.mockResolvedValueOnce({ data: rawSummary });
    const result = await getPortfolioSummary();
    expect(mockedGet).toHaveBeenCalledWith("/api/portfolio/summary");
    expect(result).toEqual(expectedSummary);
  });

  it("allocation 의 asset_type 을 assetType 으로 변환한다", async () => {
    mockedGet.mockResolvedValueOnce({ data: rawSummary });
    const result = await getPortfolioSummary();
    expect(result.allocation[0].assetType).toBe("kr_stock");
    expect(result.allocation[1].assetType).toBe("us_stock");
  });

  it("pnl_by_currency 를 pnlByCurrency 로 변환한다", async () => {
    mockedGet.mockResolvedValueOnce({ data: rawSummary });
    const result = await getPortfolioSummary();
    expect(result.pnlByCurrency).toBeDefined();
    expect(result.pnlByCurrency["KRW"]).toEqual({ abs: "1500000.00", pct: 13.64 });
  });

  it("빈 allocation 배열을 처리한다", async () => {
    mockedGet.mockResolvedValueOnce({
      data: { ...rawSummary, allocation: [] },
    });
    const result = await getPortfolioSummary();
    expect(result.allocation).toEqual([]);
  });

  it("API 에러 시 에러를 그대로 throw 한다", async () => {
    mockedGet.mockRejectedValueOnce(new Error("Network error"));
    await expect(getPortfolioSummary()).rejects.toThrow("Network error");
  });
});

describe("getPortfolioHoldings", () => {
  beforeEach(() => jest.clearAllMocks());

  it("GET /api/portfolio/holdings 를 호출하고 camelCase 변환된 배열을 반환한다", async () => {
    mockedGet.mockResolvedValueOnce({ data: [rawHolding] });
    const result = await getPortfolioHoldings();
    expect(mockedGet).toHaveBeenCalledWith("/api/portfolio/holdings");
    expect(result).toEqual([expectedHolding]);
  });

  it("빈 배열을 반환할 수 있다", async () => {
    mockedGet.mockResolvedValueOnce({ data: [] });
    const result = await getPortfolioHoldings();
    expect(result).toEqual([]);
  });

  it("is_pending: true 인 holding 을 처리한다", async () => {
    const pendingRaw = {
      ...rawHolding,
      latest_price: null,
      latest_value: null,
      pnl_abs: null,
      pnl_pct: null,
      is_pending: true,
    };
    mockedGet.mockResolvedValueOnce({ data: [pendingRaw] });
    const result = await getPortfolioHoldings();
    expect(result[0].isPending).toBe(true);
    expect(result[0].latestPrice).toBeNull();
    expect(result[0].pnlAbs).toBeNull();
  });

  it("API 에러 시 에러를 그대로 throw 한다", async () => {
    mockedGet.mockRejectedValueOnce(new Error("Server error"));
    await expect(getPortfolioHoldings()).rejects.toThrow("Server error");
  });
});
