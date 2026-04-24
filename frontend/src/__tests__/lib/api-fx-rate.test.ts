import { getFxRates } from "@/lib/api/fx-rate";
import { apiClient } from "@/lib/api-client";
import type { FxRateEntry } from "@/types/fx-rate";

jest.mock("@/lib/api-client", () => ({
  apiClient: {
    get: jest.fn(),
  },
}));

const mockedGet = jest.mocked(apiClient.get);

const rawRatesResponse = {
  rates: [
    {
      base: "USD",
      quote: "KRW",
      rate: "1380.25000000",
      fetched_at: "2026-04-24T09:00:00Z",
    },
    {
      base: "USD",
      quote: "JPY",
      rate: "154.50000000",
      fetched_at: "2026-04-24T09:00:00Z",
    },
  ],
};

const expectedRates: FxRateEntry[] = [
  {
    base: "USD",
    quote: "KRW",
    rate: "1380.25000000",
    fetchedAt: "2026-04-24T09:00:00Z",
  },
  {
    base: "USD",
    quote: "JPY",
    rate: "154.50000000",
    fetchedAt: "2026-04-24T09:00:00Z",
  },
];

describe("getFxRates", () => {
  beforeEach(() => jest.clearAllMocks());

  it("GET /api/fx/rates 를 호출하고 camelCase 변환된 배열을 반환한다", async () => {
    mockedGet.mockResolvedValueOnce({ data: rawRatesResponse });
    const result = await getFxRates();
    expect(mockedGet).toHaveBeenCalledWith("/api/fx/rates");
    expect(result).toEqual(expectedRates);
  });

  it("fetched_at 을 fetchedAt 으로 변환한다", async () => {
    mockedGet.mockResolvedValueOnce({ data: rawRatesResponse });
    const result = await getFxRates();
    expect(result[0].fetchedAt).toBe("2026-04-24T09:00:00Z");
  });

  it("rates 배열이 비어 있으면 빈 배열을 반환한다", async () => {
    mockedGet.mockResolvedValueOnce({ data: { rates: [] } });
    const result = await getFxRates();
    expect(result).toEqual([]);
  });

  it("API 에러 시 에러를 그대로 throw 한다", async () => {
    mockedGet.mockRejectedValueOnce(new Error("503 Service Unavailable"));
    await expect(getFxRates()).rejects.toThrow("503 Service Unavailable");
  });
});
