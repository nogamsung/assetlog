import { getTagBreakdown } from "@/lib/api/tag-breakdown";
import { apiClient } from "@/lib/api-client";
import type { TagBreakdownResponse } from "@/types/tag-breakdown";

jest.mock("@/lib/api-client", () => ({
  apiClient: {
    get: jest.fn(),
  },
}));

const mockedGet = jest.mocked(apiClient.get);

const rawResponse = {
  entries: [
    {
      tag: "DCA",
      transaction_count: 12,
      buy_count: 10,
      sell_count: 2,
      total_bought_value_by_currency: { USD: "1500.00", KRW: "5000000.00" },
      total_sold_value_by_currency: { USD: "100.00" },
    },
    {
      tag: null,
      transaction_count: 3,
      buy_count: 3,
      sell_count: 0,
      total_bought_value_by_currency: { KRW: "900000.00" },
      total_sold_value_by_currency: {},
    },
  ],
};

const expectedResponse: TagBreakdownResponse = {
  entries: [
    {
      tag: "DCA",
      transactionCount: 12,
      buyCount: 10,
      sellCount: 2,
      totalBoughtValueByCurrency: { USD: "1500.00", KRW: "5000000.00" },
      totalSoldValueByCurrency: { USD: "100.00" },
    },
    {
      tag: null,
      transactionCount: 3,
      buyCount: 3,
      sellCount: 0,
      totalBoughtValueByCurrency: { KRW: "900000.00" },
      totalSoldValueByCurrency: {},
    },
  ],
};

describe("getTagBreakdown", () => {
  beforeEach(() => jest.clearAllMocks());

  it("GET /api/portfolio/tags/breakdown 를 호출하고 camelCase 변환된 객체를 반환한다", async () => {
    mockedGet.mockResolvedValueOnce({ data: rawResponse });
    const result = await getTagBreakdown();
    expect(mockedGet).toHaveBeenCalledWith("/api/portfolio/tags/breakdown");
    expect(result).toEqual(expectedResponse);
  });

  it("snake_case 키를 camelCase 로 변환한다", async () => {
    mockedGet.mockResolvedValueOnce({ data: rawResponse });
    const result = await getTagBreakdown();
    const entry = result.entries[0];
    expect(entry.transactionCount).toBe(12);
    expect(entry.buyCount).toBe(10);
    expect(entry.sellCount).toBe(2);
    expect(entry.totalBoughtValueByCurrency).toEqual({ USD: "1500.00", KRW: "5000000.00" });
    expect(entry.totalSoldValueByCurrency).toEqual({ USD: "100.00" });
  });

  it("tag = null 인 entry 를 올바르게 처리한다", async () => {
    mockedGet.mockResolvedValueOnce({ data: rawResponse });
    const result = await getTagBreakdown();
    const untagged = result.entries[1];
    expect(untagged.tag).toBeNull();
    expect(untagged.transactionCount).toBe(3);
    expect(untagged.totalSoldValueByCurrency).toEqual({});
  });

  it("entries 빈 배열을 처리한다", async () => {
    mockedGet.mockResolvedValueOnce({ data: { entries: [] } });
    const result = await getTagBreakdown();
    expect(result.entries).toEqual([]);
  });

  it("API 에러 시 에러를 그대로 throw 한다", async () => {
    mockedGet.mockRejectedValueOnce(new Error("Network error"));
    await expect(getTagBreakdown()).rejects.toThrow("Network error");
  });
});
