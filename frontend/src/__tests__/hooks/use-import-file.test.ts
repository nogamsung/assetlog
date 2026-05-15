import { renderHook, waitFor, act } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";
import { useImportFile } from "@/hooks/use-import-file";
import * as integrationsApi from "@/lib/api/integrations";
import type { ImportFileResult } from "@/lib/api/integrations";

jest.mock("@/lib/api/integrations", () => ({
  importFile: jest.fn(),
}));

jest.mock("sonner", () => ({
  toast: { success: jest.fn(), error: jest.fn() },
}));

const mockedImportFile = jest.mocked(integrationsApi.importFile);

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

const fakeFile = new File(["pdf"], "test.pdf", { type: "application/pdf" });

const fakeDryRunResult: ImportFileResult = {
  insertedTrades: 5,
  insertedDividends: 2,
  insertedCashTxs: 1,
  skippedDuplicate: 0,
  skippedUnsupported: 3,
  dryRun: true,
  preview: [
    { type: "ParsedTrade", externalId: "ext-001", tradedAt: "2025-05-14T06:00:00Z" },
  ],
};

const fakeImportResult: ImportFileResult = {
  insertedTrades: 5,
  insertedDividends: 2,
  insertedCashTxs: 1,
  skippedDuplicate: 0,
  skippedUnsupported: 3,
  dryRun: false,
  preview: [],
};

describe("useImportFile", () => {
  beforeEach(() => jest.clearAllMocks());

  describe("dry-run 모드", () => {
    it("성공 시 cache invalidate 를 호출하지 않는다", async () => {
      mockedImportFile.mockResolvedValueOnce(fakeDryRunResult);
      const { Wrapper, queryClient } = makeWrapper();
      const invalidateSpy = jest.spyOn(queryClient, "invalidateQueries");
      const { result } = renderHook(() => useImportFile(), { wrapper: Wrapper });

      act(() => {
        result.current.mutate({ source: "toss_investment", file: fakeFile, dryRun: true });
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(invalidateSpy).not.toHaveBeenCalled();
    });

    it("dry-run 성공 시 toast.success 를 호출하지 않는다", async () => {
      mockedImportFile.mockResolvedValueOnce(fakeDryRunResult);
      const { Wrapper } = makeWrapper();
      const { result } = renderHook(() => useImportFile(), { wrapper: Wrapper });

      act(() => {
        result.current.mutate({ source: "toss_investment", file: fakeFile, dryRun: true });
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(mockedToast.success).not.toHaveBeenCalled();
    });

    it("결과 데이터를 반환한다", async () => {
      mockedImportFile.mockResolvedValueOnce(fakeDryRunResult);
      const { Wrapper } = makeWrapper();
      const { result } = renderHook(() => useImportFile(), { wrapper: Wrapper });

      act(() => {
        result.current.mutate({ source: "toss_investment", file: fakeFile, dryRun: true });
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(result.current.data?.insertedTrades).toBe(5);
      expect(result.current.data?.preview).toHaveLength(1);
    });
  });

  describe("실제 import 모드", () => {
    it("성공 시 transactions 쿼리를 invalidate 한다", async () => {
      mockedImportFile.mockResolvedValueOnce(fakeImportResult);
      const { Wrapper, queryClient } = makeWrapper();
      const invalidateSpy = jest.spyOn(queryClient, "invalidateQueries");
      const { result } = renderHook(() => useImportFile(), { wrapper: Wrapper });

      act(() => {
        result.current.mutate({ source: "toss_investment", file: fakeFile, dryRun: false });
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(invalidateSpy).toHaveBeenCalledWith(
        expect.objectContaining({ queryKey: ["transactions"] }),
      );
    });

    it("성공 시 portfolioSummary 쿼리를 invalidate 한다", async () => {
      mockedImportFile.mockResolvedValueOnce(fakeImportResult);
      const { Wrapper, queryClient } = makeWrapper();
      const invalidateSpy = jest.spyOn(queryClient, "invalidateQueries");
      const { result } = renderHook(() => useImportFile(), { wrapper: Wrapper });

      act(() => {
        result.current.mutate({ source: "toss_investment", file: fakeFile, dryRun: false });
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(invalidateSpy).toHaveBeenCalledWith(
        expect.objectContaining({ queryKey: ["portfolioSummary"] }),
      );
    });

    it("성공 시 success toast 를 호출한다", async () => {
      mockedImportFile.mockResolvedValueOnce(fakeImportResult);
      const { Wrapper } = makeWrapper();
      const { result } = renderHook(() => useImportFile(), { wrapper: Wrapper });

      act(() => {
        result.current.mutate({ source: "toss_investment", file: fakeFile, dryRun: false });
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(mockedToast.success).toHaveBeenCalledWith("8건의 거래내역이 가져오기 완료되었습니다.");
    });
  });

  describe("에러 처리", () => {
    function makeAxiosError(status: number, detail: string) {
      return Object.assign(new Error("AxiosError"), {
        isAxiosError: true,
        response: { status, data: { detail } },
        toJSON: () => ({}),
      });
    }

    it("422 password 에러 시 비밀번호 오류 toast 를 호출한다", async () => {
      mockedImportFile.mockRejectedValueOnce(
        makeAxiosError(422, "incorrect password provided"),
      );
      const { Wrapper } = makeWrapper();
      const { result } = renderHook(() => useImportFile(), { wrapper: Wrapper });

      act(() => {
        result.current.mutate({ source: "toss_investment", file: fakeFile, dryRun: false });
      });

      await waitFor(() => expect(result.current.isError).toBe(true));
      expect(mockedToast.error).toHaveBeenCalledWith("PDF 비밀번호가 올바르지 않습니다.");
    });

    it("422 일반 에러 시 detail 메시지 toast 를 호출한다", async () => {
      mockedImportFile.mockRejectedValueOnce(
        makeAxiosError(422, "unsupported source"),
      );
      const { Wrapper } = makeWrapper();
      const { result } = renderHook(() => useImportFile(), { wrapper: Wrapper });

      act(() => {
        result.current.mutate({ source: "toss_investment", file: fakeFile, dryRun: false });
      });

      await waitFor(() => expect(result.current.isError).toBe(true));
      expect(mockedToast.error).toHaveBeenCalledWith("unsupported source");
    });

    it("401 에러 시 로그인 필요 toast 를 호출한다", async () => {
      mockedImportFile.mockRejectedValueOnce(makeAxiosError(401, "Unauthorized"));
      const { Wrapper } = makeWrapper();
      const { result } = renderHook(() => useImportFile(), { wrapper: Wrapper });

      act(() => {
        result.current.mutate({ source: "toss_investment", file: fakeFile, dryRun: false });
      });

      await waitFor(() => expect(result.current.isError).toBe(true));
      expect(mockedToast.error).toHaveBeenCalledWith("로그인이 필요합니다.");
    });

    it("500 에러 시 detail toast 를 호출한다", async () => {
      mockedImportFile.mockRejectedValueOnce(makeAxiosError(500, "Internal Server Error"));
      const { Wrapper } = makeWrapper();
      const { result } = renderHook(() => useImportFile(), { wrapper: Wrapper });

      act(() => {
        result.current.mutate({ source: "toss_investment", file: fakeFile, dryRun: false });
      });

      await waitFor(() => expect(result.current.isError).toBe(true));
      expect(mockedToast.error).toHaveBeenCalledWith("Internal Server Error");
    });
  });
});
