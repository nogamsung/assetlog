import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";
import { useMarketIndices } from "@/hooks/use-market-indices";
import * as marketIndexApi from "@/lib/api/market-index";
import type { IndexQuote } from "@/types/market-index";

jest.mock("@/lib/api/market-index");
const mockedGetMarketIndices = jest.mocked(marketIndexApi.getMarketIndices);

function makeWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );
  }
  return { Wrapper, queryClient };
}

const fakeIndices: IndexQuote[] = [
  {
    symbol: "^GSPC",
    name: "S&P 500",
    currency: "USD",
    price: "5123.41",
    change: "12.34",
    changePct: "0.24",
    fetchedAt: "2026-04-24T09:00:00Z",
  },
];

describe("useMarketIndices", () => {
  beforeEach(() => jest.clearAllMocks());

  it("getMarketIndices 호출 결과를 반환한다", async () => {
    mockedGetMarketIndices.mockResolvedValueOnce(fakeIndices);
    const { Wrapper } = makeWrapper();
    const { result } = renderHook(() => useMarketIndices(), { wrapper: Wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toEqual(fakeIndices);
  });

  it("빈 배열을 반환할 수 있다", async () => {
    mockedGetMarketIndices.mockResolvedValueOnce([]);
    const { Wrapper } = makeWrapper();
    const { result } = renderHook(() => useMarketIndices(), { wrapper: Wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toEqual([]);
  });

  it("에러 시 isError 가 true 다", async () => {
    mockedGetMarketIndices.mockRejectedValueOnce(new Error("network"));
    const { Wrapper } = makeWrapper();
    const { result } = renderHook(() => useMarketIndices(), { wrapper: Wrapper });

    await waitFor(() => expect(result.current.isError).toBe(true));
  });
});
