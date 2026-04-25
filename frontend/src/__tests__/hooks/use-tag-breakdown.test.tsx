import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";
import { useTagBreakdown } from "@/hooks/use-tag-breakdown";
import * as tagBreakdownApi from "@/lib/api/tag-breakdown";
import type { TagBreakdownResponse } from "@/types/tag-breakdown";

jest.mock("@/lib/api/tag-breakdown");
const mockedGetTagBreakdown = jest.mocked(tagBreakdownApi.getTagBreakdown);

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

const fakeResponse: TagBreakdownResponse = {
  entries: [
    {
      tag: "DCA",
      transactionCount: 12,
      buyCount: 10,
      sellCount: 2,
      totalBoughtValueByCurrency: { USD: "1500.00" },
      totalSoldValueByCurrency: { USD: "100.00" },
    },
  ],
};

describe("useTagBreakdown", () => {
  beforeEach(() => jest.clearAllMocks());

  it("getTagBreakdown 호출 결과를 반환한다", async () => {
    mockedGetTagBreakdown.mockResolvedValueOnce(fakeResponse);
    const { Wrapper } = makeWrapper();
    const { result } = renderHook(() => useTagBreakdown(), { wrapper: Wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toEqual(fakeResponse);
  });

  it("에러 시 isError 가 true 다", async () => {
    mockedGetTagBreakdown.mockRejectedValueOnce(new Error("API error"));
    const { Wrapper } = makeWrapper();
    const { result } = renderHook(() => useTagBreakdown(), { wrapper: Wrapper });

    await waitFor(() => expect(result.current.isError).toBe(true));
  });

  it("queryKey 가 ['portfolio', 'tagBreakdown'] 이다", async () => {
    mockedGetTagBreakdown.mockResolvedValueOnce(fakeResponse);
    const { Wrapper, queryClient } = makeWrapper();
    const { result } = renderHook(() => useTagBreakdown(), { wrapper: Wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    const queryState = queryClient.getQueryState(["portfolio", "tagBreakdown"]);
    expect(queryState).toBeDefined();
  });

  it("staleTime 이 30_000 이다", async () => {
    mockedGetTagBreakdown.mockResolvedValueOnce(fakeResponse);
    const { Wrapper, queryClient } = makeWrapper();
    const { result } = renderHook(() => useTagBreakdown(), { wrapper: Wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    const queryState = queryClient.getQueryState(["portfolio", "tagBreakdown"]);
    expect(queryState?.isInvalidated).toBe(false);
  });
});
