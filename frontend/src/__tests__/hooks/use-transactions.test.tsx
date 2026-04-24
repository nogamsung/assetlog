import { renderHook, waitFor, act } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";
import {
  useTransactions,
  useAssetSummary,
  useCreateTransaction,
  useUpdateTransaction,
  useDeleteTransaction,
} from "@/hooks/use-transactions";
import * as txApi from "@/lib/api/transaction";
import type { TransactionResponse, UserAssetSummaryResponse } from "@/types/transaction";

jest.mock("@/lib/api/transaction");
const mockedListTransactions = jest.mocked(txApi.listTransactions);
const mockedGetAssetSummary = jest.mocked(txApi.getAssetSummary);
const mockedCreateTransaction = jest.mocked(txApi.createTransaction);
const mockedUpdateTransaction = jest.mocked(txApi.updateTransaction); // ADDED
const mockedDeleteTransaction = jest.mocked(txApi.deleteTransaction);

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

const fakeTx: TransactionResponse = {
  id: 1,
  userAssetId: 10,
  type: "buy",
  quantity: "1.5000000000",
  price: "50000.000000",
  tradedAt: "2026-04-23T10:00:00Z",
  memo: null,
  createdAt: "2026-04-23T10:01:00Z",
};

const fakeSummary: UserAssetSummaryResponse = {
  userAssetId: 10,
  totalBoughtQuantity: "1.5000000000",
  totalSoldQuantity: "0.0000000000",
  remainingQuantity: "1.5000000000",
  avgBuyPrice: "50000.000000",
  totalInvested: "75000.000000",
  totalSoldValue: "0.000000",
  realizedPnl: "0.000000",
  transactionCount: 1,
  currency: "KRW",
};

describe("useTransactions", () => {
  beforeEach(() => jest.clearAllMocks());

  it("listTransactions(id, {limit:100, offset:0}) 호출 결과를 반환한다", async () => {
    mockedListTransactions.mockResolvedValueOnce([fakeTx]);
    const { Wrapper } = makeWrapper();
    const { result } = renderHook(() => useTransactions(10), { wrapper: Wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toEqual([fakeTx]);
    expect(mockedListTransactions).toHaveBeenCalledWith(10, { limit: 100, offset: 0 });
  });

  it("에러 시 isError 가 true 다", async () => {
    mockedListTransactions.mockRejectedValueOnce(new Error("Network error"));
    const { Wrapper } = makeWrapper();
    const { result } = renderHook(() => useTransactions(10), { wrapper: Wrapper });

    await waitFor(() => expect(result.current.isError).toBe(true));
  });
});

describe("useAssetSummary", () => {
  beforeEach(() => jest.clearAllMocks());

  it("getAssetSummary 호출 결과를 반환한다", async () => {
    mockedGetAssetSummary.mockResolvedValueOnce(fakeSummary);
    const { Wrapper } = makeWrapper();
    const { result } = renderHook(() => useAssetSummary(10), { wrapper: Wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toEqual(fakeSummary);
  });

  it("에러 시 isError 가 true 다", async () => {
    mockedGetAssetSummary.mockRejectedValueOnce(new Error("API error"));
    const { Wrapper } = makeWrapper();
    const { result } = renderHook(() => useAssetSummary(10), { wrapper: Wrapper });

    await waitFor(() => expect(result.current.isError).toBe(true));
  });
});

describe("useCreateTransaction", () => {
  beforeEach(() => jest.clearAllMocks());

  it("성공 시 isSuccess 가 true 다", async () => {
    mockedCreateTransaction.mockResolvedValueOnce(fakeTx);
    const { Wrapper } = makeWrapper();
    const { result } = renderHook(() => useCreateTransaction(), { wrapper: Wrapper });

    act(() => {
      result.current.mutate({
        userAssetId: 10,
        data: {
          type: "buy",
          quantity: "1.5",
          price: "50000",
          tradedAt: new Date("2026-04-23"),
          memo: null,
        },
      });
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(mockedCreateTransaction).toHaveBeenCalledWith(
      10,
      expect.objectContaining({ type: "buy", quantity: "1.5" }),
    );
  });

  it("에러 시 isError 가 true 다", async () => {
    mockedCreateTransaction.mockRejectedValueOnce(new Error("Failed"));
    const { Wrapper } = makeWrapper();
    const { result } = renderHook(() => useCreateTransaction(), { wrapper: Wrapper });

    act(() => {
      result.current.mutate({
        userAssetId: 10,
        data: {
          type: "buy",
          quantity: "1.5",
          price: "50000",
          tradedAt: new Date("2026-04-23"),
          memo: null,
        },
      });
    });

    await waitFor(() => expect(result.current.isError).toBe(true));
  });
});

describe("useUpdateTransaction", () => { // ADDED
  beforeEach(() => jest.clearAllMocks());

  it("성공 시 isSuccess 가 true 다", async () => {
    mockedUpdateTransaction.mockResolvedValueOnce(fakeTx);
    const { Wrapper, queryClient } = makeWrapper();
    const { result } = renderHook(() => useUpdateTransaction(), { wrapper: Wrapper });

    act(() => {
      result.current.mutate({
        userAssetId: 10,
        transactionId: 1,
        data: {
          type: "buy",
          quantity: "2.0",
          price: "50000",
          tradedAt: new Date("2026-04-23"),
          memo: null,
        },
      });
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(mockedUpdateTransaction).toHaveBeenCalledWith(
      10,
      1,
      expect.objectContaining({ type: "buy", quantity: "2.0" }),
    );
    void queryClient;
  });

  it("에러 시 isError 가 true 다", async () => {
    mockedUpdateTransaction.mockRejectedValueOnce(new Error("Update failed"));
    const { Wrapper } = makeWrapper();
    const { result } = renderHook(() => useUpdateTransaction(), { wrapper: Wrapper });

    act(() => {
      result.current.mutate({
        userAssetId: 10,
        transactionId: 1,
        data: {
          type: "buy",
          quantity: "2.0",
          price: "50000",
          tradedAt: new Date("2026-04-23"),
          memo: null,
        },
      });
    });

    await waitFor(() => expect(result.current.isError).toBe(true));
  });

  it("성공 시 transactions, assetSummary, portfolio 쿼리를 invalidate 한다", async () => {
    mockedUpdateTransaction.mockResolvedValueOnce(fakeTx);
    const { Wrapper, queryClient } = makeWrapper();
    const invalidateSpy = jest.spyOn(queryClient, "invalidateQueries");
    const { result } = renderHook(() => useUpdateTransaction(), { wrapper: Wrapper });

    act(() => {
      result.current.mutate({
        userAssetId: 10,
        transactionId: 1,
        data: {
          type: "buy",
          quantity: "2.0",
          price: "50000",
          tradedAt: new Date("2026-04-23"),
          memo: null,
        },
      });
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(invalidateSpy).toHaveBeenCalledWith(
      expect.objectContaining({ queryKey: ["transactions", 10] }),
    );
    expect(invalidateSpy).toHaveBeenCalledWith(
      expect.objectContaining({ queryKey: ["assetSummary", 10] }),
    );
  });
});

describe("useDeleteTransaction", () => {
  beforeEach(() => jest.clearAllMocks());

  it("성공 시 isSuccess 가 true 다", async () => {
    mockedDeleteTransaction.mockResolvedValueOnce(undefined);
    const { Wrapper } = makeWrapper();
    const { result } = renderHook(() => useDeleteTransaction(), { wrapper: Wrapper });

    act(() => {
      result.current.mutate({ userAssetId: 10, txId: 1 });
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(mockedDeleteTransaction).toHaveBeenCalledWith(10, 1);
  });

  it("에러 시 isError 가 true 다", async () => {
    mockedDeleteTransaction.mockRejectedValueOnce(new Error("Delete failed"));
    const { Wrapper } = makeWrapper();
    const { result } = renderHook(() => useDeleteTransaction(), { wrapper: Wrapper });

    act(() => {
      result.current.mutate({ userAssetId: 10, txId: 1 });
    });

    await waitFor(() => expect(result.current.isError).toBe(true));
  });
});
