import { getPortfolioHistory } from "@/lib/api/portfolio-history";
import { apiClient } from "@/lib/api-client";
import type { PortfolioHistoryResponse } from "@/types/portfolio-history";

jest.mock("@/lib/api-client", () => ({
  apiClient: {
    get: jest.fn(),
  },
}));

const mockedGet = jest.mocked(apiClient.get);

const rawResponse = {
  currency: "KRW",
  period: "1M",
  bucket: "DAY",
  points: [
    {
      timestamp: "2026-03-25T00:00:00Z",
      value: "1234567.000000",
      cost_basis: "1000000.000000",
    },
    {
      timestamp: "2026-03-26T00:00:00Z",
      value: "1300000.000000",
      cost_basis: "1000000.000000",
    },
  ],
};

describe("getPortfolioHistory", () => {
  beforeEach(() => jest.clearAllMocks());

  it("GET /api/portfolio/history 를 올바른 params 로 호출한다", async () => {
    mockedGet.mockResolvedValueOnce({ data: rawResponse });
    await getPortfolioHistory({ period: "1M", currency: "KRW" });

    expect(mockedGet).toHaveBeenCalledWith("/api/portfolio/history", {
      params: { period: "1M", currency: "KRW" },
    });
  });

  it("timestamp ISO string 을 Date 객체로 변환하여 반환한다", async () => {
    mockedGet.mockResolvedValueOnce({ data: rawResponse });
    const result = await getPortfolioHistory({ period: "1M", currency: "KRW" });

    expect(result.points[0].timestamp).toBeInstanceOf(Date);
    expect(result.points[0].timestamp.toISOString()).toBe(
      "2026-03-25T00:00:00.000Z",
    );
  });

  it("cost_basis 를 costBasis 로 변환하여 반환한다", async () => {
    mockedGet.mockResolvedValueOnce({ data: rawResponse });
    const result = await getPortfolioHistory({ period: "1M", currency: "KRW" });

    expect(result.points[0].costBasis).toBe("1000000.000000");
  });

  it("currency, period, bucket 을 그대로 반환한다", async () => {
    mockedGet.mockResolvedValueOnce({ data: rawResponse });
    const result = await getPortfolioHistory({ period: "1M", currency: "KRW" });

    expect(result.currency).toBe("KRW");
    expect(result.period).toBe("1M");
    expect(result.bucket).toBe("DAY");
  });

  it("빈 points 배열을 처리한다", async () => {
    mockedGet.mockResolvedValueOnce({
      data: { ...rawResponse, points: [] },
    });
    const result: PortfolioHistoryResponse = await getPortfolioHistory({
      period: "1D",
      currency: "USD",
    });
    expect(result.points).toEqual([]);
  });

  it("API 에러 시 에러를 그대로 throw 한다", async () => {
    mockedGet.mockRejectedValueOnce(new Error("Server error"));
    await expect(
      getPortfolioHistory({ period: "1M", currency: "KRW" }),
    ).rejects.toThrow("Server error");
  });
});
