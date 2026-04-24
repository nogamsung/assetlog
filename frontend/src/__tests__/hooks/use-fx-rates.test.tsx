import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";
import { useFxRates } from "@/hooks/use-fx-rates";
import * as fxRateApi from "@/lib/api/fx-rate";
import type { FxRateEntry } from "@/types/fx-rate";

jest.mock("@/lib/api/fx-rate");
const mockedGetFxRates = jest.mocked(fxRateApi.getFxRates);

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

const fakeFxRates: FxRateEntry[] = [
  {
    base: "USD",
    quote: "KRW",
    rate: "1380.25000000",
    fetchedAt: "2026-04-24T09:00:00Z",
  },
];

describe("useFxRates", () => {
  beforeEach(() => jest.clearAllMocks());

  it("getFxRates 호출 결과를 반환한다", async () => {
    mockedGetFxRates.mockResolvedValueOnce(fakeFxRates);
    const { Wrapper } = makeWrapper();
    const { result } = renderHook(() => useFxRates(), { wrapper: Wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toEqual(fakeFxRates);
  });

  it("빈 배열을 반환할 수 있다", async () => {
    mockedGetFxRates.mockResolvedValueOnce([]);
    const { Wrapper } = makeWrapper();
    const { result } = renderHook(() => useFxRates(), { wrapper: Wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toEqual([]);
  });

  it("에러 시 isError 가 true 다", async () => {
    mockedGetFxRates.mockRejectedValueOnce(new Error("503 Service Unavailable"));
    const { Wrapper } = makeWrapper();
    const { result } = renderHook(() => useFxRates(), { wrapper: Wrapper });

    await waitFor(() => expect(result.current.isError).toBe(true));
  });

  it("query key 가 ['fx', 'rates'] 이다", async () => {
    mockedGetFxRates.mockResolvedValueOnce(fakeFxRates);
    const { Wrapper, queryClient } = makeWrapper();
    const { result } = renderHook(() => useFxRates(), { wrapper: Wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    const queryState = queryClient.getQueryState(["fx", "rates"]);
    expect(queryState).toBeDefined();
  });
});
