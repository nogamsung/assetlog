import {
  getCashAccounts,
  createCashAccount,
  updateCashAccount,
  deleteCashAccount,
} from "@/lib/api/cash-account";
import { apiClient } from "@/lib/api-client";
import type { CashAccount } from "@/types/cash-account";

jest.mock("@/lib/api-client", () => ({
  apiClient: {
    get: jest.fn(),
    post: jest.fn(),
    patch: jest.fn(),
    delete: jest.fn(),
  },
}));

const mockedGet = jest.mocked(apiClient.get);
const mockedPost = jest.mocked(apiClient.post);
const mockedPatch = jest.mocked(apiClient.patch);
const mockedDelete = jest.mocked(apiClient.delete);

const rawCashAccount = {
  id: 1,
  label: "토스뱅크 원화",
  currency: "KRW",
  balance: "1500000.0000",
  created_at: "2026-04-01T00:00:00Z",
  updated_at: "2026-04-01T00:00:00Z",
};

const expectedCashAccount: CashAccount = {
  id: 1,
  label: "토스뱅크 원화",
  currency: "KRW",
  balance: "1500000.0000",
  createdAt: "2026-04-01T00:00:00Z",
  updatedAt: "2026-04-01T00:00:00Z",
};

describe("getCashAccounts", () => {
  beforeEach(() => jest.clearAllMocks());

  it("GET /api/cash-accounts 를 호출하고 camelCase 변환된 배열을 반환한다", async () => {
    mockedGet.mockResolvedValueOnce({ data: [rawCashAccount] });
    const result = await getCashAccounts();
    expect(mockedGet).toHaveBeenCalledWith("/api/cash-accounts");
    expect(result).toEqual([expectedCashAccount]);
  });

  it("빈 배열을 반환할 수 있다", async () => {
    mockedGet.mockResolvedValueOnce({ data: [] });
    const result = await getCashAccounts();
    expect(result).toEqual([]);
  });

  it("snake_case → camelCase 변환 (created_at → createdAt)", async () => {
    mockedGet.mockResolvedValueOnce({ data: [rawCashAccount] });
    const result = await getCashAccounts();
    expect(result[0].createdAt).toBe("2026-04-01T00:00:00Z");
    expect(result[0].updatedAt).toBe("2026-04-01T00:00:00Z");
  });

  it("API 에러 시 에러를 그대로 throw 한다", async () => {
    mockedGet.mockRejectedValueOnce(new Error("Network error"));
    await expect(getCashAccounts()).rejects.toThrow("Network error");
  });
});

describe("createCashAccount", () => {
  beforeEach(() => jest.clearAllMocks());

  it("POST /api/cash-accounts 를 호출하고 변환된 계좌를 반환한다", async () => {
    mockedPost.mockResolvedValueOnce({ data: rawCashAccount });
    const input = { label: "토스뱅크 원화", currency: "KRW", balance: "1500000" };
    const result = await createCashAccount(input);
    expect(mockedPost).toHaveBeenCalledWith("/api/cash-accounts", input);
    expect(result).toEqual(expectedCashAccount);
  });

  it("API 에러 시 에러를 그대로 throw 한다", async () => {
    mockedPost.mockRejectedValueOnce(new Error("Validation error"));
    await expect(
      createCashAccount({ label: "test", currency: "KRW", balance: "100" }),
    ).rejects.toThrow("Validation error");
  });
});

describe("updateCashAccount", () => {
  beforeEach(() => jest.clearAllMocks());

  it("PATCH /api/cash-accounts/:id 를 호출하고 변환된 계좌를 반환한다", async () => {
    const updatedRaw = { ...rawCashAccount, balance: "2000000.0000" };
    mockedPatch.mockResolvedValueOnce({ data: updatedRaw });
    const input = { balance: "2000000" };
    const result = await updateCashAccount(1, input);
    expect(mockedPatch).toHaveBeenCalledWith("/api/cash-accounts/1", input);
    expect(result.balance).toBe("2000000.0000");
  });

  it("label 수정도 정상 처리한다", async () => {
    const updatedRaw = { ...rawCashAccount, label: "새 라벨" };
    mockedPatch.mockResolvedValueOnce({ data: updatedRaw });
    const result = await updateCashAccount(1, { label: "새 라벨" });
    expect(result.label).toBe("새 라벨");
  });

  it("API 에러 시 에러를 그대로 throw 한다", async () => {
    mockedPatch.mockRejectedValueOnce(new Error("Not found"));
    await expect(updateCashAccount(999, { label: "test" })).rejects.toThrow(
      "Not found",
    );
  });
});

describe("deleteCashAccount", () => {
  beforeEach(() => jest.clearAllMocks());

  it("DELETE /api/cash-accounts/:id 를 호출한다", async () => {
    mockedDelete.mockResolvedValueOnce({ data: undefined });
    await deleteCashAccount(1);
    expect(mockedDelete).toHaveBeenCalledWith("/api/cash-accounts/1");
  });

  it("void 를 반환한다", async () => {
    mockedDelete.mockResolvedValueOnce({ data: undefined });
    const result = await deleteCashAccount(1);
    expect(result).toBeUndefined();
  });

  it("API 에러 시 에러를 그대로 throw 한다", async () => {
    mockedDelete.mockRejectedValueOnce(new Error("Not found"));
    await expect(deleteCashAccount(999)).rejects.toThrow("Not found");
  });
});
