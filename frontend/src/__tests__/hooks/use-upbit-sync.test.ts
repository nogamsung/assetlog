import { renderHook, waitFor, act } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";
import { AxiosError, type AxiosResponse } from "axios";
import { useUpbitSync } from "@/hooks/use-upbit-sync";
import * as integrationsApi from "@/lib/api/integrations";
import type { UpbitSyncResult } from "@/lib/api/integrations";

jest.mock("@/lib/api/integrations", () => ({
  syncUpbit: jest.fn(),
}));

jest.mock("sonner", () => ({
  toast: { success: jest.fn(), error: jest.fn() },
}));

const mockedSyncUpbit = jest.mocked(integrationsApi.syncUpbit);

// eslint-disable-next-line @typescript-eslint/no-require-imports
const mockedToast = jest.mocked(require("sonner").toast) as {
  success: jest.Mock;
  error: jest.Mock;
};

function makeWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  function Wrapper({ children }: { children: React.ReactNode }) {
    return React.createElement(QueryClientProvider, { client: queryClient }, children);
  }
  return { Wrapper, queryClient };
}

const successResult: UpbitSyncResult = {
  fetched: 50,
  inserted: 12,
  skippedDuplicate: 38,
  skippedNoSymbol: 0,
};

const allDuplicateResult: UpbitSyncResult = {
  fetched: 50,
  inserted: 0,
  skippedDuplicate: 50,
  skippedNoSymbol: 0,
};

function makeAxiosError(status: number, detail?: string): AxiosError {
  const err = new AxiosError("HTTP error");
  err.response = {
    status,
    data: detail ? { detail } : {},
    statusText: "",
    headers: {},
    config: {} as unknown as AxiosResponse["config"],
  } as AxiosResponse;
  return err;
}

describe("useUpbitSync", () => {
  beforeEach(() => jest.clearAllMocks());

  it("성공 시 transactions/portfolio 캐시를 무효화한다", async () => {
    mockedSyncUpbit.mockResolvedValueOnce(successResult);
    const { Wrapper, queryClient } = makeWrapper();
    const invalidateSpy = jest.spyOn(queryClient, "invalidateQueries");
    const { result } = renderHook(() => useUpbitSync(), { wrapper: Wrapper });

    act(() => result.current.mutate());

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ["transactions"] });
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ["portfolioSummary"] });
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ["portfolio", "holdings"] });
  });

  it("신규 입력 건이 있을 때 inserted 건수가 토스트에 포함된다", async () => {
    mockedSyncUpbit.mockResolvedValueOnce(successResult);
    const { Wrapper } = makeWrapper();
    const { result } = renderHook(() => useUpbitSync(), { wrapper: Wrapper });

    act(() => result.current.mutate());

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(mockedToast.success).toHaveBeenCalledWith(expect.stringContaining("12"));
  });

  it("모두 중복일 때 중복 안내 토스트", async () => {
    mockedSyncUpbit.mockResolvedValueOnce(allDuplicateResult);
    const { Wrapper } = makeWrapper();
    const { result } = renderHook(() => useUpbitSync(), { wrapper: Wrapper });

    act(() => result.current.mutate());

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(mockedToast.success).toHaveBeenCalledWith(expect.stringContaining("이미"));
  });

  it("502 에러 시 키 미설정 안내 토스트", async () => {
    mockedSyncUpbit.mockRejectedValueOnce(makeAxiosError(502, "Upbit API keys are not configured."));
    const { Wrapper } = makeWrapper();
    const { result } = renderHook(() => useUpbitSync(), { wrapper: Wrapper });

    act(() => result.current.mutate());

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(mockedToast.error).toHaveBeenCalledWith(expect.stringContaining("Upbit"));
  });

  it("401 에러 시 로그인 안내 토스트", async () => {
    mockedSyncUpbit.mockRejectedValueOnce(makeAxiosError(401));
    const { Wrapper } = makeWrapper();
    const { result } = renderHook(() => useUpbitSync(), { wrapper: Wrapper });

    act(() => result.current.mutate());

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(mockedToast.error).toHaveBeenCalledWith("로그인이 필요합니다.");
  });

  it("axios 외 에러 시 일반 실패 토스트", async () => {
    mockedSyncUpbit.mockRejectedValueOnce(new Error("network down"));
    const { Wrapper } = makeWrapper();
    const { result } = renderHook(() => useUpbitSync(), { wrapper: Wrapper });

    act(() => result.current.mutate());

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(mockedToast.error).toHaveBeenCalledWith("업비트 동기화에 실패했습니다.");
  });
});
