import { apiClient } from "@/lib/api-client";
import { snakeToCamel } from "@/lib/case";
import type { LoginInput } from "@/lib/schemas/auth"; // {/* MODIFIED */}

export interface UserResponse {
  id: number;
}

interface RawUserResponse {
  id: number;
}

function toUserResponse(raw: RawUserResponse): UserResponse {
  const camelCased = snakeToCamel(raw) as unknown as UserResponse;
  return camelCased;
}

export async function login(data: LoginInput): Promise<UserResponse> { // {/* MODIFIED */}
  const response = await apiClient.post<RawUserResponse>(
    "/api/auth/login",
    data,
  );
  return toUserResponse(response.data);
}

export async function logout(): Promise<void> {
  await apiClient.post("/api/auth/logout", {});
}

export async function getMe(): Promise<UserResponse> {
  const response = await apiClient.get<RawUserResponse>("/api/auth/me");
  return toUserResponse(response.data);
}
