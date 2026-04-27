import { renderHook, waitFor, act } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";
import { useBulkImportTransactions } from "@/hooks/use-bulk-import-transactions";
import { apiClient } from "@/lib/api-client";
import type { BulkTransactionResponse } from "@/types/bulk-transaction";

jest.mock("@/lib/api-client", () => ({
  apiClient: {
    post: jest.fn(),
  },
}));

jest.mock("sonner", () => ({
  toast: { success: jest.fn(), error: jest.fn() },
}));

const mockedPost = jest.mocked(apiClient.post);

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
    return (
      React.createElement(QueryClientProvider, { client: queryClient }, children)
    );
  }
  return { Wrapper, queryClient };
}

const fakeResponse: BulkTransactionResponse = {
  imported_count: 2,
  preview: [],
};

const fakeRows = [
  {
    symbol: "BTC",
    exchange: "UPBIT",
    type: "buy" as const,
    quantity: "0.5",
    price: "85000000",
    traded_at: "2026-04-20T10:00:00+09:00",
    memo: "DCA",
    tag: "DCA",
  },
];

describe("useBulkImportTransactions", () => {
  beforeEach(() => jest.clearAllMocks());

  describe("JSON 모드", () => {
    it("200 응답 시 imported_count 와 preview 를 반환한다", async () => {
      mockedPost.mockResolvedValueOnce({ data: fakeResponse });
      const { Wrapper } = makeWrapper();
      const { result } = renderHook(() => useBulkImportTransactions(), {
        wrapper: Wrapper,
      });

      act(() => {
        result.current.mutate({ mode: "json", rows: fakeRows });
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(result.current.data?.imported_count).toBe(2);
      expect(result.current.data?.preview).toEqual([]);
    });

    it("JSON 모드 — application/json 헤더로 POST 호출한다", async () => {
      mockedPost.mockResolvedValueOnce({ data: fakeResponse });
      const { Wrapper } = makeWrapper();
      const { result } = renderHook(() => useBulkImportTransactions(), {
        wrapper: Wrapper,
      });

      act(() => {
        result.current.mutate({ mode: "json", rows: fakeRows });
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(mockedPost).toHaveBeenCalledWith(
        "/api/transactions/bulk",
        { rows: fakeRows },
        { headers: { "Content-Type": "application/json" } },
      );
    });

    it("성공 시 success toast 를 호출한다", async () => {
      mockedPost.mockResolvedValueOnce({ data: fakeResponse });
      const { Wrapper } = makeWrapper();
      const { result } = renderHook(() => useBulkImportTransactions(), {
        wrapper: Wrapper,
      });

      act(() => {
        result.current.mutate({ mode: "json", rows: fakeRows });
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(mockedToast.success).toHaveBeenCalledWith(
        "2건의 거래가 일괄 등록되었습니다.",
      );
    });

    it("422 응답 시 errors[] 를 담은 에러가 throw 된다", async () => {
      const axiosErr = Object.assign(new Error("Unprocessable"), {
        isAxiosError: true,
        response: {
          status: 422,
          data: {
            detail: "Bulk validation failed",
            errors: [
              { row: 1, field: "symbol", message: "Unknown symbol" },
            ],
          },
        },
        toJSON: () => ({}),
      });
      mockedPost.mockRejectedValueOnce(axiosErr);
      const { Wrapper } = makeWrapper();
      const { result } = renderHook(() => useBulkImportTransactions(), {
        wrapper: Wrapper,
      });

      act(() => {
        result.current.mutate({ mode: "json", rows: fakeRows });
      });

      await waitFor(() => expect(result.current.isError).toBe(true));
      // 422 일 때 toast.error 를 호출하지 않는다
      expect(mockedToast.error).not.toHaveBeenCalled();
    });
  });

  describe("CSV 모드", () => {
    it("CSV 모드 — FormData 로 POST 호출한다", async () => {
      mockedPost.mockResolvedValueOnce({ data: fakeResponse });
      const { Wrapper } = makeWrapper();
      const { result } = renderHook(() => useBulkImportTransactions(), {
        wrapper: Wrapper,
      });

      const fakeFile = new File(["content"], "test.csv", { type: "text/csv" });

      act(() => {
        result.current.mutate({ mode: "csv", file: fakeFile });
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(mockedPost).toHaveBeenCalledWith(
        "/api/transactions/bulk",
        expect.any(FormData),
      );
    });

    it("CSV 모드 — 200 응답 시 imported_count 가 정상 반환된다", async () => {
      mockedPost.mockResolvedValueOnce({ data: { imported_count: 5, preview: [] } });
      const { Wrapper } = makeWrapper();
      const { result } = renderHook(() => useBulkImportTransactions(), {
        wrapper: Wrapper,
      });

      const fakeFile = new File(["content"], "test.csv", { type: "text/csv" });

      act(() => {
        result.current.mutate({ mode: "csv", file: fakeFile });
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(result.current.data?.imported_count).toBe(5);
    });

    it("CSV 모드 422 응답 시 toast 를 호출하지 않는다", async () => {
      const axiosErr = Object.assign(new Error("Unprocessable"), {
        isAxiosError: true,
        response: {
          status: 422,
          data: {
            detail: "Bulk validation failed",
            errors: [{ row: 1, field: "type", message: "invalid value" }],
          },
        },
        toJSON: () => ({}),
      });
      mockedPost.mockRejectedValueOnce(axiosErr);
      const { Wrapper } = makeWrapper();
      const { result } = renderHook(() => useBulkImportTransactions(), {
        wrapper: Wrapper,
      });

      const fakeFile = new File(["content"], "test.csv", { type: "text/csv" });

      act(() => {
        result.current.mutate({ mode: "csv", file: fakeFile });
      });

      await waitFor(() => expect(result.current.isError).toBe(true));
      expect(mockedToast.error).not.toHaveBeenCalled();
    });
  });

  describe("query invalidation", () => {
    it("성공 시 transactions 쿼리를 invalidate 한다", async () => {
      mockedPost.mockResolvedValueOnce({ data: fakeResponse });
      const { Wrapper, queryClient } = makeWrapper();
      const invalidateSpy = jest.spyOn(queryClient, "invalidateQueries");
      const { result } = renderHook(() => useBulkImportTransactions(), {
        wrapper: Wrapper,
      });

      act(() => {
        result.current.mutate({ mode: "json", rows: fakeRows });
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(invalidateSpy).toHaveBeenCalledWith(
        expect.objectContaining({ queryKey: ["transactions"] }),
      );
    });
  });

  describe("일반 서버 에러", () => {
    it("500 에러 시 error toast 를 호출한다", async () => {
      const axiosErr = Object.assign(new Error("Server error"), {
        isAxiosError: true,
        response: { status: 500, data: { detail: "Internal error" } },
        toJSON: () => ({}),
      });
      mockedPost.mockRejectedValueOnce(axiosErr);
      const { Wrapper } = makeWrapper();
      const { result } = renderHook(() => useBulkImportTransactions(), {
        wrapper: Wrapper,
      });

      act(() => {
        result.current.mutate({ mode: "json", rows: fakeRows });
      });

      await waitFor(() => expect(result.current.isError).toBe(true));
      expect(mockedToast.error).toHaveBeenCalledWith("Internal error");
    });
  });
});
