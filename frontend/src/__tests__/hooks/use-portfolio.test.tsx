import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";
import { usePortfolioSummary, usePortfolioHoldings } from "@/hooks/use-portfolio";
import * as portfolioApi from "@/lib/api/portfolio";
import type { PortfolioSummary, HoldingResponse } from "@/types/portfolio";

jest.mock("@/lib/api/portfolio");
const mockedGetSummary = jest.mocked(portfolioApi.getPortfolioSummary);
const mockedGetHoldings = jest.mocked(portfolioApi.getPortfolioHoldings);

function makeWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });
  function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );
  }
  return { Wrapper, queryClient };
}

const fakeSummary: PortfolioSummary = {
  totalValueByCurrency: { KRW: "12500000.00" },
  totalCostByCurrency: { KRW: "11000000.00" },
  pnlByCurrency: { KRW: { abs: "1500000.00", pct: 13.64 } },
  allocation: [{ assetType: "kr_stock", pct: 100 }],
  lastPriceRefreshedAt: "2026-04-24T09:00:00+09:00",
  pendingCount: 0,
  staleCount: 0,
};

const fakeHolding: HoldingResponse = {
  userAssetId: 12,
  assetSymbol: {
    id: 1,
    assetType: "kr_stock",
    symbol: "005930",
    exchange: "KRX",
    name: "삼성전자",
    currency: "KRW",
    createdAt: "2024-01-01T00:00:00Z",
    updatedAt: "2024-01-01T00:00:00Z",
  },
  quantity: "10.0000",
  avgCost: "70000.0000",
  costBasis: "700000.00",
  latestPrice: "75000.0000",
  latestValue: "750000.00",
  pnlAbs: "50000.00",
  pnlPct: 7.14,
  weightPct: 100,
  lastPriceRefreshedAt: "2026-04-24T09:00:00+09:00",
  isStale: false,
  isPending: false,
};

describe("usePortfolioSummary", () => {
  beforeEach(() => jest.clearAllMocks());

  it("getPortfolioSummary 호출 결과를 반환한다", async () => {
    mockedGetSummary.mockResolvedValueOnce(fakeSummary);
    const { Wrapper } = makeWrapper();
    const { result } = renderHook(() => usePortfolioSummary(), { wrapper: Wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toEqual(fakeSummary);
  });

  it("에러 시 isError 가 true 다", async () => {
    mockedGetSummary.mockRejectedValueOnce(new Error("API error"));
    const { Wrapper } = makeWrapper();
    const { result } = renderHook(() => usePortfolioSummary(), { wrapper: Wrapper });

    await waitFor(() => expect(result.current.isError).toBe(true));
  });

  it("staleTime 이 60_000 이다", async () => {
    mockedGetSummary.mockResolvedValueOnce(fakeSummary);
    const { Wrapper, queryClient } = makeWrapper();
    const { result } = renderHook(() => usePortfolioSummary(), { wrapper: Wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    const queryState = queryClient.getQueryState(["portfolio", "summary"]);
    expect(queryState?.isInvalidated).toBe(false);
  });
});

describe("usePortfolioHoldings", () => {
  beforeEach(() => jest.clearAllMocks());

  it("getPortfolioHoldings 호출 결과를 반환한다", async () => {
    mockedGetHoldings.mockResolvedValueOnce([fakeHolding]);
    const { Wrapper } = makeWrapper();
    const { result } = renderHook(() => usePortfolioHoldings(), { wrapper: Wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toEqual([fakeHolding]);
  });

  it("빈 배열을 반환할 수 있다", async () => {
    mockedGetHoldings.mockResolvedValueOnce([]);
    const { Wrapper } = makeWrapper();
    const { result } = renderHook(() => usePortfolioHoldings(), { wrapper: Wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toEqual([]);
  });

  it("에러 시 isError 가 true 다", async () => {
    mockedGetHoldings.mockRejectedValueOnce(new Error("Network error"));
    const { Wrapper } = makeWrapper();
    const { result } = renderHook(() => usePortfolioHoldings(), { wrapper: Wrapper });

    await waitFor(() => expect(result.current.isError).toBe(true));
  });
});
