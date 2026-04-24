import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";
import { usePortfolioHistory } from "@/hooks/use-portfolio-history";
import * as historyApi from "@/lib/api/portfolio-history";
import type { PortfolioHistoryResponse } from "@/types/portfolio-history";

jest.mock("@/lib/api/portfolio-history");
const mockedGetPortfolioHistory = jest.mocked(historyApi.getPortfolioHistory);

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

const fakeHistory: PortfolioHistoryResponse = {
  currency: "KRW",
  period: "1M",
  bucket: "DAY",
  points: [
    {
      timestamp: new Date("2026-03-25T00:00:00Z"),
      value: "1234567.000000",
      costBasis: "1000000.000000",
    },
  ],
};

describe("usePortfolioHistory", () => {
  beforeEach(() => jest.clearAllMocks());

  it("getPortfolioHistory 호출 결과를 반환한다", async () => {
    mockedGetPortfolioHistory.mockResolvedValueOnce(fakeHistory);
    const { Wrapper } = makeWrapper();
    const { result } = renderHook(
      () => usePortfolioHistory({ period: "1M", currency: "KRW" }),
      { wrapper: Wrapper },
    );

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toEqual(fakeHistory);
    expect(mockedGetPortfolioHistory).toHaveBeenCalledWith({
      period: "1M",
      currency: "KRW",
    });
  });

  it("currency 가 빈 문자열이면 쿼리가 비활성화된다", () => {
    const { Wrapper } = makeWrapper();
    const { result } = renderHook(
      () => usePortfolioHistory({ period: "1M", currency: "" }),
      { wrapper: Wrapper },
    );

    expect(result.current.fetchStatus).toBe("idle");
    expect(mockedGetPortfolioHistory).not.toHaveBeenCalled();
  });

  it("에러 시 isError 가 true 다", async () => {
    mockedGetPortfolioHistory.mockRejectedValueOnce(new Error("API error"));
    const { Wrapper } = makeWrapper();
    const { result } = renderHook(
      () => usePortfolioHistory({ period: "1W", currency: "USD" }),
      { wrapper: Wrapper },
    );

    await waitFor(() => expect(result.current.isError).toBe(true));
  });

  it("period 와 currency 가 query key 에 포함된다", async () => {
    mockedGetPortfolioHistory.mockResolvedValueOnce(fakeHistory);
    const { Wrapper, queryClient } = makeWrapper();
    const { result } = renderHook(
      () => usePortfolioHistory({ period: "1Y", currency: "KRW" }),
      { wrapper: Wrapper },
    );

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    const cachedData = queryClient.getQueryData(["portfolioHistory", "1Y", "KRW"]);
    expect(cachedData).toEqual(fakeHistory);
  });
});
