"use client";

import { useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { getMe, login, logout, signup } from "@/lib/api/auth";
import type { UserResponse } from "@/lib/api/auth";
import type { LoginInput, SignupInput } from "@/lib/schemas/auth";

const AUTH_QUERY_KEY = ["auth", "me"] as const;

export function useCurrentUser() {
  return useQuery<UserResponse | null>({
    queryKey: AUTH_QUERY_KEY,
    queryFn: async () => {
      try {
        return await getMe();
      } catch {
        return null;
      }
    },
    retry: false,
    staleTime: 60_000,
  });
}

export function useSignup() {
  const router = useRouter();
  const queryClient = useQueryClient();

  return useMutation<UserResponse, Error, SignupInput>({
    mutationFn: signup,
    onSuccess: (user) => {
      queryClient.setQueryData(AUTH_QUERY_KEY, user);
      router.push("/");
    },
  });
}

export function useLogin() {
  const router = useRouter();
  const queryClient = useQueryClient();

  return useMutation<
    UserResponse,
    Error,
    LoginInput & { redirectTo?: string }
  >({
    mutationFn: (variables) => {
      const loginData: LoginInput = {
        email: variables.email,
        password: variables.password,
      };
      return login(loginData);
    },
    onSuccess: (user, variables) => {
      queryClient.setQueryData(AUTH_QUERY_KEY, user);
      router.push(variables.redirectTo ?? "/");
    },
  });
}

export function useLogout() {
  const router = useRouter();
  const queryClient = useQueryClient();

  return useMutation<void, Error, void>({
    mutationFn: logout,
    onSuccess: () => {
      queryClient.setQueryData(AUTH_QUERY_KEY, null);
      router.push("/login");
    },
  });
}
