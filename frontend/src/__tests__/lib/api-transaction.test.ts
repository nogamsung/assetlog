import {
  createTransaction,
  listTransactions,
  deleteTransaction,
  getAssetSummary,
} from "@/lib/api/transaction";
import { apiClient } from "@/lib/api-client";
import type { TransactionResponse, UserAssetSummaryResponse } from "@/types/transaction";

jest.mock("@/lib/api-client", () => ({
  apiClient: {
    get: jest.fn(),
    post: jest.fn(),
    delete: jest.fn(),
  },
}));

const mockedGet = jest.mocked(apiClient.get);
const mockedPost = jest.mocked(apiClient.post);
const mockedDelete = jest.mocked(apiClient.delete);

const rawTransaction = {
  id: 1,
  user_asset_id: 10,
  type: "buy" as const,
  quantity: "1.5000000000",
  price: "50000.000000",
  traded_at: "2026-04-23T10:00:00+00:00",
  memo: "테스트 메모",
  created_at: "2026-04-23T10:01:00Z",
};

const expectedTransaction: TransactionResponse = {
  id: 1,
  userAssetId: 10,
  type: "buy",
  quantity: "1.5000000000",
  price: "50000.000000",
  tradedAt: "2026-04-23T10:00:00+00:00",
  memo: "테스트 메모",
  createdAt: "2026-04-23T10:01:00Z",
};

const rawSummary = {
  user_asset_id: 10,
  total_quantity: "3.0000000000",
  avg_cost: "49000.000000",
  cost_basis: "147000.00",
  transaction_count: 2,
};

const expectedSummary: UserAssetSummaryResponse = {
  userAssetId: 10,
  totalQuantity: "3.0000000000",
  avgCost: "49000.000000",
  costBasis: "147000.00",
  transactionCount: 2,
};

describe("createTransaction", () => {
  beforeEach(() => jest.clearAllMocks());

  it("POST /api/user-assets/:id/transactions 를 호출하고 camelCase 변환된 객체를 반환한다", async () => {
    mockedPost.mockResolvedValueOnce({ data: rawTransaction });
    const tradedAt = new Date("2026-04-23T10:00:00Z");
    const result = await createTransaction(10, {
      type: "buy",
      quantity: "1.5",
      price: "50000",
      tradedAt,
      memo: "테스트 메모",
    });

    expect(mockedPost).toHaveBeenCalledWith(
      "/api/user-assets/10/transactions",
      expect.objectContaining({
        type: "buy",
        quantity: "1.5",
        price: "50000",
        traded_at: tradedAt.toISOString(),
        memo: "테스트 메모",
      }),
    );
    expect(result).toEqual(expectedTransaction);
  });

  it("memo 가 null 이면 null 로 전달된다", async () => {
    mockedPost.mockResolvedValueOnce({ data: { ...rawTransaction, memo: null } });
    await createTransaction(10, {
      type: "buy",
      quantity: "1.5",
      price: "50000",
      tradedAt: new Date(),
      memo: null,
    });

    expect(mockedPost).toHaveBeenCalledWith(
      "/api/user-assets/10/transactions",
      expect.objectContaining({ memo: null }),
    );
  });

  it("API 에러 시 에러를 그대로 throw 한다", async () => {
    mockedPost.mockRejectedValueOnce(new Error("Network error"));
    await expect(
      createTransaction(10, {
        type: "buy",
        quantity: "1.5",
        price: "50000",
        tradedAt: new Date(),
        memo: null,
      }),
    ).rejects.toThrow("Network error");
  });
});

describe("listTransactions", () => {
  beforeEach(() => jest.clearAllMocks());

  it("GET /api/user-assets/:id/transactions 를 호출하고 camelCase 배열을 반환한다", async () => {
    mockedGet.mockResolvedValueOnce({ data: [rawTransaction] });
    const result = await listTransactions(10, { limit: 100, offset: 0 });

    expect(mockedGet).toHaveBeenCalledWith(
      "/api/user-assets/10/transactions",
      { params: { limit: 100, offset: 0 } },
    );
    expect(result).toEqual([expectedTransaction]);
  });

  it("params 없이 호출 시 빈 params 로 GET 한다", async () => {
    mockedGet.mockResolvedValueOnce({ data: [] });
    await listTransactions(10);

    expect(mockedGet).toHaveBeenCalledWith(
      "/api/user-assets/10/transactions",
      { params: {} },
    );
  });

  it("빈 배열을 반환할 수 있다", async () => {
    mockedGet.mockResolvedValueOnce({ data: [] });
    const result = await listTransactions(10);
    expect(result).toEqual([]);
  });

  it("API 에러 시 에러를 그대로 throw 한다", async () => {
    mockedGet.mockRejectedValueOnce(new Error("Server error"));
    await expect(listTransactions(10)).rejects.toThrow("Server error");
  });
});

describe("deleteTransaction", () => {
  beforeEach(() => jest.clearAllMocks());

  it("DELETE /api/user-assets/:id/transactions/:txId 를 호출한다", async () => {
    mockedDelete.mockResolvedValueOnce({ data: undefined });
    await deleteTransaction(10, 1);

    expect(mockedDelete).toHaveBeenCalledWith(
      "/api/user-assets/10/transactions/1",
    );
  });

  it("API 에러 시 에러를 그대로 throw 한다", async () => {
    mockedDelete.mockRejectedValueOnce(new Error("Delete failed"));
    await expect(deleteTransaction(10, 1)).rejects.toThrow("Delete failed");
  });
});

describe("getAssetSummary", () => {
  beforeEach(() => jest.clearAllMocks());

  it("GET /api/user-assets/:id/summary 를 호출하고 camelCase 변환된 객체를 반환한다", async () => {
    mockedGet.mockResolvedValueOnce({ data: rawSummary });
    const result = await getAssetSummary(10);

    expect(mockedGet).toHaveBeenCalledWith("/api/user-assets/10/summary");
    expect(result).toEqual(expectedSummary);
  });

  it("API 에러 시 에러를 그대로 throw 한다", async () => {
    mockedGet.mockRejectedValueOnce(new Error("Network error"));
    await expect(getAssetSummary(10)).rejects.toThrow("Network error");
  });
});
