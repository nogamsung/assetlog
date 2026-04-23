const BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api";

export type AssetType = "kr_stock" | "us_stock" | "crypto";

export interface Holding {
  id: number;
  asset_type: AssetType;
  symbol: string;
  quantity: number;
  avg_cost: number;
  purchased_at: string;
  created_at: string;
}

export interface HoldingCreate {
  asset_type: AssetType;
  symbol: string;
  quantity: number;
  avg_cost: number;
  purchased_at: string;
}

export interface Price {
  symbol: string;
  asset_type: string;
  price: number;
  currency: string;
  fetched_at: string;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
  });
  if (!res.ok) throw new Error(`API ${res.status}: ${await res.text()}`);
  if (res.status === 204) return undefined as T;
  return res.json();
}

export const api = {
  listHoldings: () => request<Holding[]>("/holdings"),
  createHolding: (payload: HoldingCreate) =>
    request<Holding>("/holdings", { method: "POST", body: JSON.stringify(payload) }),
  deleteHolding: (id: number) => request<void>(`/holdings/${id}`, { method: "DELETE" }),
  latestPrices: () => request<Price[]>("/prices/latest"),
  triggerRefresh: () => request<{ status: string }>("/prices/refresh", { method: "POST" }),
};
