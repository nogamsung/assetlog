"use client";

import { useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner"; // {/* ADDED */}
import { getMe, login, logout } from "@/lib/api/auth"; // {/* MODIFIED */}
import type { UserResponse } from "@/lib/api/auth";
import type { LoginInput } from "@/lib/schemas/auth"; // {/* MODIFIED */}
import type { AxiosError } from "axios"; // {/* ADDED */}

const AUTH_QUERY_KEY = ["auth", "me"] as const;

interface ApiErrorDetail { // {/* ADDED */}
  detail: string;
}

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

export function useLogin() { // {/* MODIFIED */}
  const router = useRouter();
  const queryClient = useQueryClient();

  return useMutation<
    UserResponse,
    AxiosError<ApiErrorDetail>,
    LoginInput & { redirectTo?: string }
  >({
    mutationFn: (variables) => {
      const loginData: LoginInput = { password: variables.password }; // {/* MODIFIED */}
      return login(loginData);
    },
    onSuccess: (user, variables) => {
      queryClient.setQueryData(AUTH_QUERY_KEY, user);
      router.push(variables.redirectTo ?? "/");
    },
    onError: (error) => { // {/* ADDED */}
      const status = error.response?.status;
      if (status === 429) {
        const retryAfter = error.response?.headers?.["retry-after"] as string | undefined;
        const seconds = retryAfter ? Number(retryAfter) : null;
        if (seconds !== null && !Number.isNaN(seconds)) {
          toast.error(`${seconds}초 후 다시 시도해주세요.`);
        } else {
          toast.error("잠시 후 다시 시도해주세요.");
        }
      } else if (status === 503) {
        toast.error("서버 비밀번호 미설정. 관리자에게 문의하세요.");
      } else if (status === 401) {
        toast.error("비밀번호가 올바르지 않습니다.");
      } else {
        toast.error(error.response?.data?.detail ?? "로그인에 실패했습니다.");
      }
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
