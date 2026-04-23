import {
  searchSymbols,
  createSymbol,
  listUserAssets,
  createUserAsset,
  deleteUserAsset,
} from "@/lib/api/asset";
import { apiClient } from "@/lib/api-client";
import type { AssetSymbolResponse, UserAssetResponse } from "@/types/asset";

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

const rawSymbol = {
  id: 1,
  asset_type: "crypto" as const,
  symbol: "BTC",
  exchange: "BINANCE",
  name: "Bitcoin",
  currency: "USDT",
  created_at: "2024-01-01T00:00:00Z",
  updated_at: "2024-01-01T00:00:00Z",
};

const expectedSymbol: AssetSymbolResponse = {
  id: 1,
  assetType: "crypto",
  symbol: "BTC",
  exchange: "BINANCE",
  name: "Bitcoin",
  currency: "USDT",
  createdAt: "2024-01-01T00:00:00Z",
  updatedAt: "2024-01-01T00:00:00Z",
};

const rawUserAsset = {
  id: 10,
  user_id: 1,
  asset_symbol: rawSymbol,
  memo: "장기보유",
  created_at: "2024-01-01T00:00:00Z",
};

const expectedUserAsset: UserAssetResponse = {
  id: 10,
  userId: 1,
  assetSymbol: expectedSymbol,
  memo: "장기보유",
  createdAt: "2024-01-01T00:00:00Z",
};

describe("searchSymbols", () => {
  beforeEach(() => jest.clearAllMocks());

  it("GET /api/symbols 를 호출하고 camelCase 변환된 배열을 반환한다", async () => {
    mockedGet.mockResolvedValueOnce({ data: [rawSymbol] });
    const result = await searchSymbols({ q: "BTC" });
    expect(mockedGet).toHaveBeenCalledWith("/api/symbols", {
      params: { q: "BTC" },
    });
    expect(result).toEqual([expectedSymbol]);
  });

  it("assetType 필터를 snake_case 로 변환하여 전달한다", async () => {
    mockedGet.mockResolvedValueOnce({ data: [] });
    await searchSymbols({ assetType: "kr_stock", limit: 10, offset: 0 });
    expect(mockedGet).toHaveBeenCalledWith("/api/symbols", {
      params: { asset_type: "kr_stock", limit: 10, offset: 0 },
    });
  });

  it("빈 결과를 반환할 수 있다", async () => {
    mockedGet.mockResolvedValueOnce({ data: [] });
    const result = await searchSymbols({ q: "UNKNOWN" });
    expect(result).toEqual([]);
  });
});

describe("createSymbol", () => {
  beforeEach(() => jest.clearAllMocks());

  it("POST /api/symbols 를 호출하고 AssetSymbolResponse 를 반환한다", async () => {
    mockedPost.mockResolvedValueOnce({ data: rawSymbol });
    const result = await createSymbol({
      assetType: "crypto",
      symbol: "BTC",
      exchange: "BINANCE",
      name: "Bitcoin",
      currency: "USDT",
    });
    expect(mockedPost).toHaveBeenCalledWith("/api/symbols", {
      asset_type: "crypto",
      symbol: "BTC",
      exchange: "BINANCE",
      name: "Bitcoin",
      currency: "USDT",
    });
    expect(result).toEqual(expectedSymbol);
  });

  it("409 에러 시 ApiError (status: 409) 를 throw 한다", async () => {
    const axiosErr = Object.assign(new Error("Conflict"), {
      response: { status: 409, data: { detail: "Duplicate" } },
    });
    mockedPost.mockRejectedValueOnce(axiosErr);
    await expect(
      createSymbol({
        assetType: "crypto",
        symbol: "BTC",
        exchange: "BINANCE",
        name: "Bitcoin",
        currency: "USDT",
      }),
    ).rejects.toMatchObject({ status: 409 });
  });

  it("비-409 에러는 그대로 re-throw 한다", async () => {
    const networkErr = new Error("Network error");
    mockedPost.mockRejectedValueOnce(networkErr);
    await expect(
      createSymbol({
        assetType: "crypto",
        symbol: "BTC",
        exchange: "BINANCE",
        name: "Bitcoin",
        currency: "USDT",
      }),
    ).rejects.toThrow("Network error");
  });
});

describe("listUserAssets", () => {
  beforeEach(() => jest.clearAllMocks());

  it("GET /api/user-assets 를 호출하고 UserAssetResponse[] 를 반환한다", async () => {
    mockedGet.mockResolvedValueOnce({ data: [rawUserAsset] });
    const result = await listUserAssets();
    expect(mockedGet).toHaveBeenCalledWith("/api/user-assets");
    expect(result).toEqual([expectedUserAsset]);
  });
});

describe("createUserAsset", () => {
  beforeEach(() => jest.clearAllMocks());

  it("POST /api/user-assets 를 호출하고 UserAssetResponse 를 반환한다", async () => {
    mockedPost.mockResolvedValueOnce({ data: rawUserAsset });
    const result = await createUserAsset({ assetSymbolId: 1, memo: "장기보유" });
    expect(mockedPost).toHaveBeenCalledWith("/api/user-assets", {
      asset_symbol_id: 1,
      memo: "장기보유",
    });
    expect(result).toEqual(expectedUserAsset);
  });

  it("memo 없을 때 null 로 전달한다", async () => {
    mockedPost.mockResolvedValueOnce({ data: { ...rawUserAsset, memo: null } });
    await createUserAsset({ assetSymbolId: 1 });
    expect(mockedPost).toHaveBeenCalledWith("/api/user-assets", {
      asset_symbol_id: 1,
      memo: null,
    });
  });
});

describe("deleteUserAsset", () => {
  beforeEach(() => jest.clearAllMocks());

  it("DELETE /api/user-assets/:id 를 호출한다", async () => {
    mockedDelete.mockResolvedValueOnce({ data: undefined });
    await deleteUserAsset(10);
    expect(mockedDelete).toHaveBeenCalledWith("/api/user-assets/10");
  });
});
