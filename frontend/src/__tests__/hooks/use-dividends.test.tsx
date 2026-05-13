import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";
import { useDividendsBySymbol } from "@/hooks/use-dividends";
import * as dividendApi from "@/lib/api/dividend";
import type { DividendListResponse } from "@/types/dividend";

jest.mock("@/lib/api/dividend");
const mockedListDividends = jest.mocked(dividendApi.listDividends);

function makeWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );
  }
  return { Wrapper };
}

const fakeResponse: DividendListResponse = {
  dividends: [
    {
      id: 1,
      assetSymbolId: 42,
      exDate: "2026-02-07",
      payDate: "2026-03-01",
      amount: "0.50",
      currency: "USD",
    },
  ],
  summary: [{ assetSymbolId: 42, totalAmount: "1.20", currency: "USD" }],
};

describe("useDividendsBySymbol", () => {
  beforeEach(() => jest.clearAllMocks());

  it("assetSymbolId 가 있을 때 listDividends 호출 결과를 반환한다", async () => {
    mockedListDividends.mockResolvedValueOnce(fakeResponse);
    const { Wrapper } = makeWrapper();
    const { result } = renderHook(() => useDividendsBySymbol(42), {
      wrapper: Wrapper,
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toEqual(fakeResponse);
    expect(mockedListDividends).toHaveBeenCalledWith({ assetSymbolId: 42 });
  });

  it("assetSymbolId 가 undefined 면 호출하지 않는다 (enabled=false)", () => {
    const { Wrapper } = makeWrapper();
    renderHook(() => useDividendsBySymbol(undefined), { wrapper: Wrapper });
    expect(mockedListDividends).not.toHaveBeenCalled();
  });
});
