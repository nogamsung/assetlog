import { renderHook, waitFor, act } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";
import {
  useCashAccounts,
  useCreateCashAccount,
  useUpdateCashAccount,
  useDeleteCashAccount,
} from "@/hooks/use-cash-accounts";
import * as cashAccountApi from "@/lib/api/cash-account";
import type { CashAccount } from "@/types/cash-account";

jest.mock("@/lib/api/cash-account");
const mockedGetCashAccounts = jest.mocked(cashAccountApi.getCashAccounts);
const mockedCreateCashAccount = jest.mocked(cashAccountApi.createCashAccount);
const mockedUpdateCashAccount = jest.mocked(cashAccountApi.updateCashAccount);
const mockedDeleteCashAccount = jest.mocked(cashAccountApi.deleteCashAccount);

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

const fakeCashAccount: CashAccount = {
  id: 1,
  label: "토스뱅크 원화",
  currency: "KRW",
  balance: "1500000.0000",
  createdAt: "2026-04-01T00:00:00Z",
  updatedAt: "2026-04-01T00:00:00Z",
};

describe("useCashAccounts", () => {
  beforeEach(() => jest.clearAllMocks());

  it("getCashAccounts 호출 결과를 반환한다", async () => {
    mockedGetCashAccounts.mockResolvedValueOnce([fakeCashAccount]);
    const { Wrapper } = makeWrapper();
    const { result } = renderHook(() => useCashAccounts(), { wrapper: Wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toEqual([fakeCashAccount]);
  });

  it("에러 시 isError 가 true 다", async () => {
    mockedGetCashAccounts.mockRejectedValueOnce(new Error("Network error"));
    const { Wrapper } = makeWrapper();
    const { result } = renderHook(() => useCashAccounts(), { wrapper: Wrapper });

    await waitFor(() => expect(result.current.isError).toBe(true));
  });
});

describe("useCreateCashAccount", () => {
  beforeEach(() => jest.clearAllMocks());

  it("성공 시 cash-accounts 쿼리를 invalidate 한다", async () => {
    mockedGetCashAccounts.mockResolvedValue([fakeCashAccount]);
    mockedCreateCashAccount.mockResolvedValueOnce(fakeCashAccount);

    const { Wrapper, queryClient } = makeWrapper();
    const invalidateSpy = jest.spyOn(queryClient, "invalidateQueries");

    const { result } = renderHook(() => useCreateCashAccount(), {
      wrapper: Wrapper,
    });

    act(() => {
      result.current.mutate({
        label: "토스뱅크 원화",
        currency: "KRW",
        balance: "1500000",
      });
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(invalidateSpy).toHaveBeenCalledWith(
      expect.objectContaining({ queryKey: ["cash-accounts"] }),
    );
  });

  it("성공 시 portfolio-summary 쿼리도 invalidate 한다", async () => {
    mockedGetCashAccounts.mockResolvedValue([fakeCashAccount]);
    mockedCreateCashAccount.mockResolvedValueOnce(fakeCashAccount);

    const { Wrapper, queryClient } = makeWrapper();
    const invalidateSpy = jest.spyOn(queryClient, "invalidateQueries");

    const { result } = renderHook(() => useCreateCashAccount(), {
      wrapper: Wrapper,
    });

    act(() => {
      result.current.mutate({
        label: "토스뱅크 원화",
        currency: "KRW",
        balance: "1500000",
      });
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(invalidateSpy).toHaveBeenCalledWith(
      expect.objectContaining({ queryKey: expect.arrayContaining(["portfolio", "summary"]) }),
    );
  });

  it("에러 시 isError 가 true 다", async () => {
    mockedCreateCashAccount.mockRejectedValueOnce(new Error("Failed"));
    const { Wrapper } = makeWrapper();
    const { result } = renderHook(() => useCreateCashAccount(), {
      wrapper: Wrapper,
    });

    act(() => {
      result.current.mutate({
        label: "test",
        currency: "KRW",
        balance: "100",
      });
    });

    await waitFor(() => expect(result.current.isError).toBe(true));
  });
});

describe("useUpdateCashAccount", () => {
  beforeEach(() => jest.clearAllMocks());

  it("성공 시 cash-accounts 쿼리를 invalidate 한다", async () => {
    const updated = { ...fakeCashAccount, balance: "2000000.0000" };
    mockedUpdateCashAccount.mockResolvedValueOnce(updated);

    const { Wrapper, queryClient } = makeWrapper();
    const invalidateSpy = jest.spyOn(queryClient, "invalidateQueries");

    const { result } = renderHook(() => useUpdateCashAccount(), {
      wrapper: Wrapper,
    });

    act(() => {
      result.current.mutate({ id: 1, input: { balance: "2000000" } });
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(invalidateSpy).toHaveBeenCalledWith(
      expect.objectContaining({ queryKey: ["cash-accounts"] }),
    );
  });

  it("에러 시 isError 가 true 다", async () => {
    mockedUpdateCashAccount.mockRejectedValueOnce(new Error("Not found"));
    const { Wrapper } = makeWrapper();
    const { result } = renderHook(() => useUpdateCashAccount(), {
      wrapper: Wrapper,
    });

    act(() => {
      result.current.mutate({ id: 999, input: { label: "test" } });
    });

    await waitFor(() => expect(result.current.isError).toBe(true));
  });
});

describe("useDeleteCashAccount", () => {
  beforeEach(() => jest.clearAllMocks());

  it("성공 시 cash-accounts 쿼리를 invalidate 한다", async () => {
    mockedDeleteCashAccount.mockResolvedValueOnce(undefined);

    const { Wrapper, queryClient } = makeWrapper();
    const invalidateSpy = jest.spyOn(queryClient, "invalidateQueries");

    const { result } = renderHook(() => useDeleteCashAccount(), {
      wrapper: Wrapper,
    });

    act(() => {
      result.current.mutate(1);
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(invalidateSpy).toHaveBeenCalledWith(
      expect.objectContaining({ queryKey: ["cash-accounts"] }),
    );
  });

  it("에러 시 isError 가 true 다", async () => {
    mockedDeleteCashAccount.mockRejectedValueOnce(new Error("Not found"));
    const { Wrapper } = makeWrapper();
    const { result } = renderHook(() => useDeleteCashAccount(), {
      wrapper: Wrapper,
    });

    act(() => {
      result.current.mutate(999);
    });

    await waitFor(() => expect(result.current.isError).toBe(true));
  });
});
