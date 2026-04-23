"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useCurrentUser } from "@/hooks/use-auth";

interface AuthGuardProps {
  children: React.ReactNode;
}

export function AuthGuard({ children }: AuthGuardProps) {
  const router = useRouter();
  const { data: user, isSuccess } = useCurrentUser();

  useEffect(() => {
    if (isSuccess && user !== null) {
      router.replace("/");
    }
  }, [isSuccess, user, router]);

  // 이미 로그인된 경우 리다이렉트 중 — 빈 화면 표시
  if (isSuccess && user !== null) {
    return null;
  }

  return <>{children}</>;
}
