import { apiClient } from "@/lib/api-client";
import { snakeToCamel } from "@/lib/case";
import type { LoginInput, SignupInput } from "@/lib/schemas/auth";

export interface UserResponse {
  id: number;
  email: string;
  createdAt: string;
}

interface RawUserResponse {
  id: number;
  email: string;
  created_at: string;
}

function toUserResponse(raw: RawUserResponse): UserResponse {
  const camelCased = snakeToCamel(raw) as unknown as UserResponse;
  return camelCased;
}

export async function signup(data: SignupInput): Promise<UserResponse> {
  const response = await apiClient.post<RawUserResponse>(
    "/api/auth/signup",
    data,
  );
  return toUserResponse(response.data);
}

export async function login(data: LoginInput): Promise<UserResponse> {
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
