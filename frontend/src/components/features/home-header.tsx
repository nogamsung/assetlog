"use client";

import { useLogout } from "@/hooks/use-auth";
import { Button } from "@/components/ui/button";

export function HomeHeader() {
  const logoutMutation = useLogout();

  return (
    <header className="flex items-center justify-between border-b px-6 py-4">
      <h1 className="text-lg font-semibold">AssetLog</h1>
      <Button
        variant="outline"
        size="sm"
        onClick={() => logoutMutation.mutate()}
        disabled={logoutMutation.isPending}
        aria-busy={logoutMutation.isPending}
      >
        {logoutMutation.isPending ? "로그아웃 중..." : "로그아웃"}
      </Button>
    </header>
  );
}
