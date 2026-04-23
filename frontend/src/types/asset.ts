export type AssetType = "crypto" | "kr_stock" | "us_stock";

export interface AssetSymbolResponse {
  id: number;
  assetType: AssetType;
  symbol: string;
  exchange: string;
  name: string;
  currency: string;
  createdAt: string;
  updatedAt: string;
}

export interface UserAssetResponse {
  id: number;
  userId: number;
  assetSymbol: AssetSymbolResponse;
  memo: string | null;
  createdAt: string;
}
