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
  converted_total_value: null,
  converted_total_cost: null,
  converted_pnl_abs: null,
  converted_realized_pnl: null,
  display_currency: null,
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
  convertedTotalValue: null,
  convertedTotalCost: null,
  convertedPnlAbs: null,
  convertedRealizedPnl: null,
  displayCurrency: null,
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
  // 환산 필드 — ADDED
  converted_latest_value: null,
  converted_cost_basis: null,
  converted_pnl_abs: null,
  converted_realized_pnl: null,
  display_currency: null,
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
  // 환산 필드 — ADDED
  convertedLatestValue: null,
  convertedCostBasis: null,
  convertedPnlAbs: null,
  convertedRealizedPnl: null,
  displayCurrency: null,
};

describe("getPortfolioSummary", () => {
  beforeEach(() => jest.clearAllMocks());

  it("GET /api/portfolio/summary 를 호출하고 camelCase 변환된 객체를 반환한다", async () => {
    mockedGet.mockResolvedValueOnce({ data: rawSummary });
    const result = await getPortfolioSummary();
    expect(mockedGet).toHaveBeenCalledWith("/api/portfolio/summary");
    expect(result).toEqual(expectedSummary);
  });

  it("convertTo 옵션이 있으면 query string 을 붙인다", async () => {
    mockedGet.mockResolvedValueOnce({ data: rawSummary });
    await getPortfolioSummary({ convertTo: "KRW" });
    expect(mockedGet).toHaveBeenCalledWith(
      "/api/portfolio/summary?convert_to=KRW",
    );
  });

  it("convertTo 가 없으면 기본 URL 을 사용한다", async () => {
    mockedGet.mockResolvedValueOnce({ data: rawSummary });
    await getPortfolioSummary({});
    expect(mockedGet).toHaveBeenCalledWith("/api/portfolio/summary");
  });

  it("converted_* 필드를 camelCase 로 매핑한다", async () => {
    const rawWithConverted = {
      ...rawSummary,
      converted_total_value: "51380000.00",
      converted_total_cost: "41104000.00",
      converted_pnl_abs: "10276000.00",
      converted_realized_pnl: "369000.00",
      display_currency: "KRW",
    };
    mockedGet.mockResolvedValueOnce({ data: rawWithConverted });
    const result = await getPortfolioSummary({ convertTo: "KRW" });
    expect(result.convertedTotalValue).toBe("51380000.00");
    expect(result.convertedTotalCost).toBe("41104000.00");
    expect(result.convertedPnlAbs).toBe("10276000.00");
    expect(result.convertedRealizedPnl).toBe("369000.00");
    expect(result.displayCurrency).toBe("KRW");
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

  it("convertTo 옵션이 있으면 query string 을 붙인다", async () => { // ADDED
    mockedGet.mockResolvedValueOnce({ data: [rawHolding] });
    await getPortfolioHoldings({ convertTo: "KRW" });
    expect(mockedGet).toHaveBeenCalledWith(
      "/api/portfolio/holdings?convert_to=KRW",
    );
  });

  it("convertTo 가 없으면 기본 URL 을 사용한다", async () => { // ADDED
    mockedGet.mockResolvedValueOnce({ data: [rawHolding] });
    await getPortfolioHoldings({});
    expect(mockedGet).toHaveBeenCalledWith("/api/portfolio/holdings");
  });

  it("converted_* 필드를 camelCase 로 매핑한다", async () => { // ADDED
    const rawWithConverted = {
      ...rawHolding,
      converted_latest_value: "2437280.00",
      converted_cost_basis: "2370415.00",
      converted_pnl_abs: "65345.00",
      converted_realized_pnl: "0.00",
      display_currency: "KRW",
    };
    mockedGet.mockResolvedValueOnce({ data: [rawWithConverted] });
    const result = await getPortfolioHoldings({ convertTo: "KRW" });
    expect(result[0].convertedLatestValue).toBe("2437280.00");
    expect(result[0].convertedCostBasis).toBe("2370415.00");
    expect(result[0].convertedPnlAbs).toBe("65345.00");
    expect(result[0].convertedRealizedPnl).toBe("0.00");
    expect(result[0].displayCurrency).toBe("KRW");
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
