import { seedSampleData } from "@/lib/api/sample";
import { apiClient } from "@/lib/api-client";
import type { SampleSeedResponse } from "@/types/sample";

jest.mock("@/lib/api-client", () => ({
  apiClient: {
    post: jest.fn(),
  },
}));

const mockedPost = jest.mocked(apiClient.post);

const rawSeeded = {
  seeded: true,
  reason: null,
  user_assets_created: 5,
  transactions_created: 17,
  symbols_created: 5,
  symbols_reused: 0,
};

const expectedSeeded: SampleSeedResponse = {
  seeded: true,
  reason: null,
  userAssetsCreated: 5,
  transactionsCreated: 17,
  symbolsCreated: 5,
  symbolsReused: 0,
};

const rawSkipped = {
  seeded: false,
  reason: "user_already_has_assets",
  user_assets_created: 0,
  transactions_created: 0,
  symbols_created: 0,
  symbols_reused: 0,
};

const expectedSkipped: SampleSeedResponse = {
  seeded: false,
  reason: "user_already_has_assets",
  userAssetsCreated: 0,
  transactionsCreated: 0,
  symbolsCreated: 0,
  symbolsReused: 0,
};

describe("seedSampleData", () => {
  beforeEach(() => jest.clearAllMocks());

  it("POST /api/sample/seed 를 body 없이 호출한다", async () => {
    mockedPost.mockResolvedValueOnce({ data: rawSeeded });
    await seedSampleData();
    expect(mockedPost).toHaveBeenCalledWith("/api/sample/seed");
  });

  it("seeded=true 응답을 camelCase 로 변환하여 반환한다", async () => {
    mockedPost.mockResolvedValueOnce({ data: rawSeeded });
    const result = await seedSampleData();
    expect(result).toEqual(expectedSeeded);
  });

  it("seeded=false 응답(이미 자산 있음)을 올바르게 변환한다", async () => {
    mockedPost.mockResolvedValueOnce({ data: rawSkipped });
    const result = await seedSampleData();
    expect(result).toEqual(expectedSkipped);
  });

  it("네트워크 에러를 그대로 throw 한다", async () => {
    mockedPost.mockRejectedValueOnce(new Error("Network error"));
    await expect(seedSampleData()).rejects.toThrow("Network error");
  });
});
