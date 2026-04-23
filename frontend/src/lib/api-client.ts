import axios, { type AxiosError } from "axios";

export interface ApiError {
  detail: string;
  status: number;
}

export const apiClient = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000",
  withCredentials: true,
  headers: {
    "Content-Type": "application/json",
  },
});

apiClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    if (error.response?.status === 401) {
      const url = error.config?.url ?? "";
      // /api/auth/me 는 훅에서 조용히 처리하므로 자동 리다이렉트 제외
      const isMeEndpoint = url.includes("/api/auth/me");
      if (!isMeEndpoint && typeof window !== "undefined") {
        window.location.href = "/login";
      }
    }
    return Promise.reject(error);
  },
);

// ──────────────────────────────────────────────
// Domain types (migrated from src/lib/api.ts)
// ──────────────────────────────────────────────

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

// ──────────────────────────────────────────────
// API helpers (migrated from src/lib/api.ts)
// ──────────────────────────────────────────────

export const holdingsApi = {
  list: (): Promise<Holding[]> =>
    apiClient.get<Holding[]>("/api/holdings").then((r) => r.data),
  create: (payload: HoldingCreate): Promise<Holding> =>
    apiClient.post<Holding>("/api/holdings", payload).then((r) => r.data),
  delete: (id: number): Promise<void> =>
    apiClient.delete(`/api/holdings/${id}`).then(() => undefined),
};

export const pricesApi = {
  latest: (): Promise<Price[]> =>
    apiClient.get<Price[]>("/api/prices/latest").then((r) => r.data),
  triggerRefresh: (): Promise<{ status: string }> =>
    apiClient
      .post<{ status: string }>("/api/prices/refresh")
      .then((r) => r.data),
};
