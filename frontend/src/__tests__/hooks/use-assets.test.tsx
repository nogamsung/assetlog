import { renderHook, waitFor, act } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";
import {
  useUserAssets,
  useCreateUserAsset,
  useDeleteUserAsset,
  useSymbolSearch,
} from "@/hooks/use-assets";
import * as assetApi from "@/lib/api/asset";
import type { AssetSymbolResponse, UserAssetResponse } from "@/types/asset";

const mockPush = jest.fn();
jest.mock("next/navigation", () => ({
  useRouter: () => ({ push: mockPush }),
}));

jest.mock("@/lib/api/asset");
const mockedListUserAssets = jest.mocked(assetApi.listUserAssets);
const mockedCreateUserAsset = jest.mocked(assetApi.createUserAsset);
const mockedDeleteUserAsset = jest.mocked(assetApi.deleteUserAsset);
const mockedSearchSymbols = jest.mocked(assetApi.searchSymbols);

function makeWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );
  }
  return { Wrapper, queryClient };
}

const fakeSymbol: AssetSymbolResponse = {
  id: 1,
  assetType: "crypto",
  symbol: "BTC",
  exchange: "BINANCE",
  name: "Bitcoin",
  currency: "USDT",
  createdAt: "2024-01-01T00:00:00Z",
  updatedAt: "2024-01-01T00:00:00Z",
};

const fakeUserAsset: UserAssetResponse = {
  id: 10,
  assetSymbol: fakeSymbol,
  memo: null,
  createdAt: "2024-01-01T00:00:00Z",
};

describe("useUserAssets", () => {
  beforeEach(() => jest.clearAllMocks());

  it("listUserAssets 호출 결과를 반환한다", async () => {
    mockedListUserAssets.mockResolvedValueOnce([fakeUserAsset]);
    const { Wrapper } = makeWrapper();
    const { result } = renderHook(() => useUserAssets(), { wrapper: Wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toEqual([fakeUserAsset]);
  });

  it("에러 시 isError 가 true 다", async () => {
    mockedListUserAssets.mockRejectedValueOnce(new Error("Network error"));
    const { Wrapper } = makeWrapper();
    const { result } = renderHook(() => useUserAssets(), { wrapper: Wrapper });

    await waitFor(() => expect(result.current.isError).toBe(true));
  });
});

describe("useCreateUserAsset", () => {
  beforeEach(() => jest.clearAllMocks());

  it("성공 시 router.push('/assets') 가 호출된다", async () => {
    mockedCreateUserAsset.mockResolvedValueOnce(fakeUserAsset);
    const { Wrapper } = makeWrapper();
    const { result } = renderHook(() => useCreateUserAsset(), {
      wrapper: Wrapper,
    });

    act(() => {
      result.current.mutate({ assetSymbolId: 1, memo: null });
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(mockPush).toHaveBeenCalledWith("/assets");
  });

  it("에러 시 isError 가 true 다", async () => {
    mockedCreateUserAsset.mockRejectedValueOnce(new Error("Failed"));
    const { Wrapper } = makeWrapper();
    const { result } = renderHook(() => useCreateUserAsset(), {
      wrapper: Wrapper,
    });

    act(() => {
      result.current.mutate({ assetSymbolId: 1 });
    });

    await waitFor(() => expect(result.current.isError).toBe(true));
  });
});

describe("useDeleteUserAsset", () => {
  beforeEach(() => jest.clearAllMocks());

  it("낙관적 업데이트로 항목이 즉시 제거된다", async () => {
    mockedDeleteUserAsset.mockResolvedValueOnce(undefined);
    mockedListUserAssets.mockResolvedValue([fakeUserAsset]);

    const { Wrapper, queryClient } = makeWrapper();

    // 초기 캐시 세팅
    queryClient.setQueryData(["user-assets"], [fakeUserAsset]);

    const { result } = renderHook(() => useDeleteUserAsset(), {
      wrapper: Wrapper,
    });

    act(() => {
      result.current.mutate(10);
    });

    // 낙관적 업데이트 — 캐시에서 즉시 제거 확인
    await waitFor(() => {
      const cached = queryClient.getQueryData<UserAssetResponse[]>(["user-assets"]);
      expect(cached?.find((a) => a.id === 10)).toBeUndefined();
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
  });

  it("에러 시 이전 데이터로 롤백한다", async () => {
    mockedDeleteUserAsset.mockRejectedValueOnce(new Error("Delete failed"));
    mockedListUserAssets.mockResolvedValue([fakeUserAsset]);

    const { Wrapper, queryClient } = makeWrapper();
    queryClient.setQueryData(["user-assets"], [fakeUserAsset]);

    const { result } = renderHook(() => useDeleteUserAsset(), {
      wrapper: Wrapper,
    });

    act(() => {
      result.current.mutate(10);
    });

    await waitFor(() => expect(result.current.isError).toBe(true));

    // 롤백 확인
    const cached = queryClient.getQueryData<UserAssetResponse[]>(["user-assets"]);
    expect(cached).toEqual([fakeUserAsset]);
  });
});

describe("useSymbolSearch", () => {
  beforeEach(() => jest.clearAllMocks());

  it("q 가 비어있고 assetType 도 없으면 쿼리가 비활성화된다", () => {
    const { Wrapper } = makeWrapper();
    const { result } = renderHook(() => useSymbolSearch(""), { wrapper: Wrapper });

    // enabled: false → fetchStatus: 'idle'
    expect(result.current.fetchStatus).toBe("idle");
    expect(mockedSearchSymbols).not.toHaveBeenCalled();
  });

  it("q 가 1자 이상이면 searchSymbols 를 호출한다", async () => {
    mockedSearchSymbols.mockResolvedValueOnce([fakeSymbol]);
    const { Wrapper } = makeWrapper();
    const { result } = renderHook(() => useSymbolSearch("BTC"), {
      wrapper: Wrapper,
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toEqual([fakeSymbol]);
  });

  it("assetType 만 있어도 쿼리가 활성화된다", async () => {
    mockedSearchSymbols.mockResolvedValueOnce([fakeSymbol]);
    const { Wrapper } = makeWrapper();
    const { result } = renderHook(
      () => useSymbolSearch("", "crypto"),
      { wrapper: Wrapper },
    );

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(mockedSearchSymbols).toHaveBeenCalled();
  });
});
