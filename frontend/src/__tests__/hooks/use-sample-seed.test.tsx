import { renderHook, waitFor, act } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";
import { useSampleSeed } from "@/hooks/use-sample-seed";
import * as sampleApi from "@/lib/api/sample";
import type { SampleSeedResponse } from "@/types/sample";

jest.mock("@/lib/api/sample");
jest.mock("sonner", () => ({
  toast: Object.assign(jest.fn(), {
    success: jest.fn(),
    error: jest.fn(),
  }),
}));

const mockedSeedSampleData = jest.mocked(sampleApi.seedSampleData);

// eslint-disable-next-line @typescript-eslint/no-require-imports
const mockedToast = jest.mocked(require("sonner").toast) as jest.Mock & {
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
    return (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );
  }
  return { Wrapper, queryClient };
}

const seededResponse: SampleSeedResponse = {
  seeded: true,
  reason: null,
  userAssetsCreated: 5,
  transactionsCreated: 17,
  symbolsCreated: 5,
  symbolsReused: 0,
};

const skippedResponse: SampleSeedResponse = {
  seeded: false,
  reason: "user_already_has_assets",
  userAssetsCreated: 0,
  transactionsCreated: 0,
  symbolsCreated: 0,
  symbolsReused: 0,
};

describe("useSampleSeed", () => {
  beforeEach(() => jest.clearAllMocks());

  describe("seeded=true — 성공적으로 시드된 경우", () => {
    it("isSuccess 가 true 다", async () => {
      mockedSeedSampleData.mockResolvedValueOnce(seededResponse);
      const { Wrapper } = makeWrapper();
      const { result } = renderHook(() => useSampleSeed(), { wrapper: Wrapper });

      act(() => {
        result.current.mutate();
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
    });

    it("transactionsCreated 를 포함한 success toast 를 호출한다", async () => {
      mockedSeedSampleData.mockResolvedValueOnce(seededResponse);
      const { Wrapper } = makeWrapper();
      const { result } = renderHook(() => useSampleSeed(), { wrapper: Wrapper });

      act(() => {
        result.current.mutate();
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(mockedToast.success).toHaveBeenCalledWith(
        "샘플 자산 5개와 거래 17건이 추가되었습니다.",
      );
    });

    it("관련 쿼리들을 invalidate 한다", async () => {
      mockedSeedSampleData.mockResolvedValueOnce(seededResponse);
      const { Wrapper, queryClient } = makeWrapper();
      const invalidateSpy = jest.spyOn(queryClient, "invalidateQueries");
      const { result } = renderHook(() => useSampleSeed(), { wrapper: Wrapper });

      act(() => {
        result.current.mutate();
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(invalidateSpy).toHaveBeenCalledWith(
        expect.objectContaining({ queryKey: ["user-assets"] }),
      );
      expect(invalidateSpy).toHaveBeenCalledWith(
        expect.objectContaining({ queryKey: ["portfolio", "summary"] }),
      );
      expect(invalidateSpy).toHaveBeenCalledWith(
        expect.objectContaining({ queryKey: ["portfolio", "holdings"] }),
      );
      expect(invalidateSpy).toHaveBeenCalledWith(
        expect.objectContaining({ queryKey: ["portfolioSummary"] }),
      );
      expect(invalidateSpy).toHaveBeenCalledWith(
        expect.objectContaining({ queryKey: ["portfolioHistory"] }),
      );
      expect(invalidateSpy).toHaveBeenCalledWith(
        expect.objectContaining({ queryKey: ["userTags"] }),
      );
    });
  });

  describe("seeded=false — 이미 자산이 있어 스킵된 경우", () => {
    it("isSuccess 가 true 다 (성공 응답이므로)", async () => {
      mockedSeedSampleData.mockResolvedValueOnce(skippedResponse);
      const { Wrapper } = makeWrapper();
      const { result } = renderHook(() => useSampleSeed(), { wrapper: Wrapper });

      act(() => {
        result.current.mutate();
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
    });

    it("info toast (toast()) 를 호출한다", async () => {
      mockedSeedSampleData.mockResolvedValueOnce(skippedResponse);
      const { Wrapper } = makeWrapper();
      const { result } = renderHook(() => useSampleSeed(), { wrapper: Wrapper });

      act(() => {
        result.current.mutate();
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(mockedToast).toHaveBeenCalledWith(
        "이미 보유 자산이 있어 샘플 데이터를 추가하지 않았습니다.",
      );
      expect(mockedToast.success).not.toHaveBeenCalled();
    });

    it("쿼리 invalidate 를 호출하지 않는다", async () => {
      mockedSeedSampleData.mockResolvedValueOnce(skippedResponse);
      const { Wrapper, queryClient } = makeWrapper();
      const invalidateSpy = jest.spyOn(queryClient, "invalidateQueries");
      const { result } = renderHook(() => useSampleSeed(), { wrapper: Wrapper });

      act(() => {
        result.current.mutate();
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(invalidateSpy).not.toHaveBeenCalled();
    });
  });

  describe("에러 — API 호출 실패", () => {
    it("isError 가 true 다", async () => {
      mockedSeedSampleData.mockRejectedValueOnce(new Error("Server error"));
      const { Wrapper } = makeWrapper();
      const { result } = renderHook(() => useSampleSeed(), { wrapper: Wrapper });

      act(() => {
        result.current.mutate();
      });

      await waitFor(() => expect(result.current.isError).toBe(true));
    });

    it("error toast 를 호출한다", async () => {
      mockedSeedSampleData.mockRejectedValueOnce(new Error("Server error"));
      const { Wrapper } = makeWrapper();
      const { result } = renderHook(() => useSampleSeed(), { wrapper: Wrapper });

      act(() => {
        result.current.mutate();
      });

      await waitFor(() => expect(result.current.isError).toBe(true));
      expect(mockedToast.error).toHaveBeenCalledWith(
        "샘플 데이터 추가에 실패했습니다.",
      );
    });

    it("success toast 와 info toast 를 호출하지 않는다", async () => {
      mockedSeedSampleData.mockRejectedValueOnce(new Error("Server error"));
      const { Wrapper } = makeWrapper();
      const { result } = renderHook(() => useSampleSeed(), { wrapper: Wrapper });

      act(() => {
        result.current.mutate();
      });

      await waitFor(() => expect(result.current.isError).toBe(true));
      expect(mockedToast.success).not.toHaveBeenCalled();
      expect(mockedToast).not.toHaveBeenCalledWith(
        "이미 보유 자산이 있어 샘플 데이터를 추가하지 않았습니다.",
      );
    });
  });
});
