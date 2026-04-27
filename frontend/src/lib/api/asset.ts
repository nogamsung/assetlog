import { type AxiosError } from "axios";
import { apiClient } from "@/lib/api-client";
import { snakeToCamel } from "@/lib/case";
import type { AssetSymbolResponse, AssetType, UserAssetResponse } from "@/types/asset";
import type { SymbolCreateInput, UserAssetCreateInput } from "@/lib/schemas/asset";

// ── Raw shapes (snake_case from backend) ──────────────────────────────────────

interface RawAssetSymbolResponse {
  id: number;
  asset_type: AssetType;
  symbol: string;
  exchange: string;
  name: string;
  currency: string;
  created_at: string;
  updated_at: string;
}

interface RawUserAssetResponse {
  id: number;
  asset_symbol: RawAssetSymbolResponse;
  memo: string | null;
  created_at: string;
}

// ── Converters ─────────────────────────────────────────────────────────────────

function toAssetSymbol(raw: RawAssetSymbolResponse): AssetSymbolResponse {
  return snakeToCamel(raw) as unknown as AssetSymbolResponse;
}

function toUserAsset(raw: RawUserAssetResponse): UserAssetResponse {
  return snakeToCamel(raw) as unknown as UserAssetResponse;
}

// ── Public API helpers ─────────────────────────────────────────────────────────

export interface SearchSymbolsParams {
  q?: string;
  assetType?: AssetType;
  exchange?: string;
  limit?: number;
  offset?: number;
}

export async function searchSymbols(
  params: SearchSymbolsParams,
): Promise<AssetSymbolResponse[]> {
  const query: Record<string, string | number> = {};
  if (params.q !== undefined) query["q"] = params.q;
  if (params.assetType !== undefined) query["asset_type"] = params.assetType;
  if (params.exchange !== undefined) query["exchange"] = params.exchange;
  if (params.limit !== undefined) query["limit"] = params.limit;
  if (params.offset !== undefined) query["offset"] = params.offset;

  const response = await apiClient.get<RawAssetSymbolResponse[]>(
    "/api/symbols",
    { params: query },
  );
  return response.data.map(toAssetSymbol);
}

export async function createSymbol(
  data: SymbolCreateInput,
): Promise<AssetSymbolResponse> {
  try {
    const payload = {
      asset_type: data.assetType,
      symbol: data.symbol,
      exchange: data.exchange,
      name: data.name,
      currency: data.currency,
    };
    const response = await apiClient.post<RawAssetSymbolResponse>(
      "/api/symbols",
      payload,
    );
    return toAssetSymbol(response.data);
  } catch (err) {
    const axiosErr = err as AxiosError;
    if (axiosErr.response?.status === 409) {
      const apiError: import("@/lib/api-client").ApiError = {
        detail: "이미 등록된 심볼입니다.",
        status: 409,
      };
      throw apiError;
    }
    throw err;
  }
}

export async function listUserAssets(): Promise<UserAssetResponse[]> {
  const response = await apiClient.get<RawUserAssetResponse[]>("/api/user-assets");
  return response.data.map(toUserAsset);
}

export async function createUserAsset(
  data: UserAssetCreateInput,
): Promise<UserAssetResponse> {
  const payload = {
    asset_symbol_id: data.assetSymbolId,
    memo: data.memo ?? null,
  };
  const response = await apiClient.post<RawUserAssetResponse>(
    "/api/user-assets",
    payload,
  );
  return toUserAsset(response.data);
}

export async function deleteUserAsset(id: number): Promise<void> {
  await apiClient.delete(`/api/user-assets/${id}`);
}
