import {
  createTransaction,
  updateTransaction,
  listTransactions,
  deleteTransaction,
  getAssetSummary,
  importTransactionsCsv,
  listUserTags,
} from "@/lib/api/transaction";
import { apiClient } from "@/lib/api-client";
import type { TransactionResponse, UserAssetSummaryResponse } from "@/types/transaction";

jest.mock("@/lib/api-client", () => ({
  apiClient: {
    get: jest.fn(),
    post: jest.fn(),
    put: jest.fn(),
    delete: jest.fn(),
  },
}));

const mockedGet = jest.mocked(apiClient.get);
const mockedPost = jest.mocked(apiClient.post);
const mockedPut = jest.mocked(apiClient.put); // ADDED
const mockedDelete = jest.mocked(apiClient.delete);

const rawTransaction = {
  id: 1,
  user_asset_id: 10,
  type: "buy" as const,
  quantity: "1.5000000000",
  price: "50000.000000",
  traded_at: "2026-04-23T10:00:00+00:00",
  memo: "테스트 메모",
  tag: null,
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
  tag: null,
  createdAt: "2026-04-23T10:01:00Z",
};

const rawSummary = {
  user_asset_id: 10,
  total_bought_quantity: "3.0000000000",
  total_sold_quantity: "0.0000000000",
  remaining_quantity: "3.0000000000",
  avg_buy_price: "49000.000000",
  total_invested: "147000.000000",
  total_sold_value: "0.000000",
  realized_pnl: "0.000000",
  transaction_count: 2,
  currency: "KRW",
};

const expectedSummary: UserAssetSummaryResponse = {
  userAssetId: 10,
  totalBoughtQuantity: "3.0000000000",
  totalSoldQuantity: "0.0000000000",
  remainingQuantity: "3.0000000000",
  avgBuyPrice: "49000.000000",
  totalInvested: "147000.000000",
  totalSoldValue: "0.000000",
  realizedPnl: "0.000000",
  transactionCount: 2,
  currency: "KRW",
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

describe("updateTransaction", () => { // ADDED
  beforeEach(() => jest.clearAllMocks());

  it("PUT /api/user-assets/:id/transactions/:txId 를 호출하고 camelCase 변환된 객체를 반환한다", async () => {
    mockedPut.mockResolvedValueOnce({ data: rawTransaction });
    const tradedAt = new Date("2026-04-23T10:00:00Z");
    const result = await updateTransaction(10, 1, {
      type: "buy",
      quantity: "1.5",
      price: "50000",
      tradedAt,
      memo: "테스트 메모",
    });

    expect(mockedPut).toHaveBeenCalledWith(
      "/api/user-assets/10/transactions/1",
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
    mockedPut.mockResolvedValueOnce({ data: { ...rawTransaction, memo: null } });
    await updateTransaction(10, 1, {
      type: "buy",
      quantity: "1.5",
      price: "50000",
      tradedAt: new Date(),
      memo: null,
    });

    expect(mockedPut).toHaveBeenCalledWith(
      "/api/user-assets/10/transactions/1",
      expect.objectContaining({ memo: null }),
    );
  });

  it("API 에러 시 에러를 그대로 throw 한다", async () => {
    mockedPut.mockRejectedValueOnce(new Error("Network error"));
    await expect(
      updateTransaction(10, 1, {
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

describe("importTransactionsCsv", () => {
  beforeEach(() => jest.clearAllMocks());

  it("POST /api/user-assets/:id/transactions/import 를 FormData 로 호출한다", async () => {
    const rawImportResponse = {
      imported_count: 2,
      preview: [rawTransaction],
    };
    mockedPost.mockResolvedValueOnce({ data: rawImportResponse });

    const file = new File(["type,quantity\nbuy,1"], "test.csv", { type: "text/csv" });
    const result = await importTransactionsCsv(10, file);

    expect(mockedPost).toHaveBeenCalledWith(
      "/api/user-assets/10/transactions/import",
      expect.any(FormData),
      expect.objectContaining({
        headers: { "Content-Type": "multipart/form-data" },
      }),
    );
    expect(result.importedCount).toBe(2);
    expect(result.preview).toEqual([expectedTransaction]);
  });

  it("FormData 에 file 필드가 포함된다", async () => {
    const rawImportResponse = { imported_count: 1, preview: [rawTransaction] };
    mockedPost.mockResolvedValueOnce({ data: rawImportResponse });

    const file = new File(["content"], "upload.csv", { type: "text/csv" });
    await importTransactionsCsv(10, file);

    const [, formData] = mockedPost.mock.calls[0] as [string, FormData, unknown];
    expect(formData.get("file")).toBe(file);
  });

  it("preview 배열을 camelCase 로 변환한다", async () => {
    mockedPost.mockResolvedValueOnce({
      data: { imported_count: 1, preview: [rawTransaction] },
    });
    const file = new File([""], "a.csv");
    const result = await importTransactionsCsv(10, file);

    expect(result.preview[0]).toEqual(expectedTransaction);
  });

  it("422 에러를 그대로 throw 한다", async () => {
    const err422 = Object.assign(new Error("Unprocessable"), {
      isAxiosError: true,
      response: {
        status: 422,
        data: {
          detail: "1 rows have errors",
          errors: [{ row: 2, field: "type", message: "invalid value" }],
        },
      },
    });
    mockedPost.mockRejectedValueOnce(err422);
    const file = new File([""], "b.csv");
    await expect(importTransactionsCsv(10, file)).rejects.toThrow("Unprocessable");
  });

  it("API 에러 시 에러를 그대로 throw 한다", async () => {
    mockedPost.mockRejectedValueOnce(new Error("Network error"));
    const file = new File([""], "c.csv");
    await expect(importTransactionsCsv(10, file)).rejects.toThrow("Network error");
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

describe("listTransactions — tag query", () => {
  beforeEach(() => jest.clearAllMocks());

  it("tag 파라미터를 query string 으로 전달한다", async () => {
    mockedGet.mockResolvedValueOnce({ data: [] });
    await listTransactions(10, { limit: 100, offset: 0, tag: "DCA" });
    expect(mockedGet).toHaveBeenCalledWith(
      "/api/user-assets/10/transactions",
      { params: { limit: 100, offset: 0, tag: "DCA" } },
    );
  });

  it("tag 가 없으면 query 에 포함되지 않는다", async () => {
    mockedGet.mockResolvedValueOnce({ data: [] });
    await listTransactions(10, { limit: 100, offset: 0 });
    expect(mockedGet).toHaveBeenCalledWith(
      "/api/user-assets/10/transactions",
      { params: { limit: 100, offset: 0 } },
    );
  });
});

describe("createTransaction / updateTransaction — tag payload", () => {
  beforeEach(() => jest.clearAllMocks());

  it("createTransaction 가 tag 를 trim 후 전송한다", async () => {
    mockedPost.mockResolvedValueOnce({ data: rawTransaction });
    await createTransaction(10, {
      type: "buy",
      quantity: "1.5",
      price: "50000",
      tradedAt: new Date("2026-04-23T10:00:00Z"),
      memo: null,
      tag: "  DCA  ",
    });
    expect(mockedPost).toHaveBeenCalledWith(
      "/api/user-assets/10/transactions",
      expect.objectContaining({ tag: "DCA" }),
    );
  });

  it("createTransaction 가 빈 tag 를 null 로 변환해 전송한다", async () => {
    mockedPost.mockResolvedValueOnce({ data: rawTransaction });
    await createTransaction(10, {
      type: "buy",
      quantity: "1.5",
      price: "50000",
      tradedAt: new Date("2026-04-23T10:00:00Z"),
      memo: null,
      tag: "   ",
    });
    expect(mockedPost).toHaveBeenCalledWith(
      "/api/user-assets/10/transactions",
      expect.objectContaining({ tag: null }),
    );
  });

  it("updateTransaction 가 tag 를 PUT body 에 포함한다", async () => {
    mockedPut.mockResolvedValueOnce({ data: rawTransaction });
    await updateTransaction(10, 1, {
      type: "buy",
      quantity: "1.5",
      price: "50000",
      tradedAt: new Date("2026-04-23T10:00:00Z"),
      memo: null,
      tag: "장기보유",
    });
    expect(mockedPut).toHaveBeenCalledWith(
      "/api/user-assets/10/transactions/1",
      expect.objectContaining({ tag: "장기보유" }),
    );
  });
});

describe("listUserTags", () => {
  beforeEach(() => jest.clearAllMocks());

  it("GET /api/user-assets/transactions/tags 를 호출하고 string 배열을 반환한다", async () => {
    mockedGet.mockResolvedValueOnce({ data: ["DCA", "스윙", "장기보유"] });
    const result = await listUserTags();
    expect(mockedGet).toHaveBeenCalledWith(
      "/api/user-assets/transactions/tags",
    );
    expect(result).toEqual(["DCA", "스윙", "장기보유"]);
  });

  it("빈 배열도 처리한다", async () => {
    mockedGet.mockResolvedValueOnce({ data: [] });
    const result = await listUserTags();
    expect(result).toEqual([]);
  });
});
