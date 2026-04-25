"use client";

import Link from "next/link";
import { Settings } from "lucide-react";
import { useCurrentUser, useLogout } from "@/hooks/use-auth";
import { Button } from "@/components/ui/button";

function AppHeader() {
  const { data: user } = useCurrentUser();
  const logoutMutation = useLogout();

  return (
    <header className="flex items-center justify-between border-b px-6 py-4">
      <div className="flex items-center gap-6">
        <Link
          href="/"
          className="text-lg font-semibold hover:text-primary transition-colors"
        >
          AssetLog
        </Link>
        <nav className="flex items-center gap-4">
          <Link
            href="/dashboard"
            className="text-sm text-muted-foreground hover:text-foreground transition-colors"
          >
            대시보드
          </Link>
          <Link
            href="/assets"
            className="text-sm text-muted-foreground hover:text-foreground transition-colors"
          >
            보유 자산
          </Link>
        </nav>
      </div>
      <div className="flex items-center gap-4">
        {user && (
          <span className="text-sm text-muted-foreground">{user.email}님</span>
        )}
        <Link
          href="/settings"
          className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors"
          aria-label="설정 페이지로 이동"
        >
          <Settings className="h-4 w-4" aria-hidden="true" />
          설정
        </Link>
        <Button
          variant="outline"
          size="sm"
          onClick={() => logoutMutation.mutate()}
          disabled={logoutMutation.isPending}
          aria-busy={logoutMutation.isPending}
        >
          {logoutMutation.isPending ? "로그아웃 중..." : "로그아웃"}
        </Button>
      </div>
    </header>
  );
}

export default function AppLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="flex min-h-screen flex-col">
      <AppHeader />
      <main className="flex-1">{children}</main>
    </div>
  );
}
