"use client";

import Link from "next/link";
import { usePathname } from "next/navigation"; /* ADDED */
import { Settings } from "lucide-react";
import { useLogout } from "@/hooks/use-auth";
import { Button } from "@/components/ui/button";

/* MODIFIED: Toss-style sticky header with aria-current */
function AppHeader() {
  const logoutMutation = useLogout();
  const pathname = usePathname(); /* ADDED */

  function navLinkClass(href: string): string {
    const isActive = pathname === href || pathname.startsWith(`${href}/`);
    return isActive
      ? "text-sm font-bold text-toss-blue transition-colors" /* MODIFIED: toss blue for active */
      : "text-sm text-toss-textWeak hover:text-toss-text transition-colors"; /* MODIFIED */
  }

  return (
    /* MODIFIED: sticky Toss-style header */
    <header className="sticky top-0 z-40 flex h-14 items-center justify-between border-b border-toss-border bg-toss-bg/90 px-4 backdrop-blur supports-[backdrop-filter]:bg-toss-bg/60 sm:px-6">
      <div className="flex items-center gap-4 sm:gap-6">
        <Link
          href="/"
          className="text-base font-bold text-toss-textStrong hover:text-toss-blue transition-colors"
        >
          AssetLog
        </Link>
        <nav className="flex items-center gap-3 sm:gap-4" aria-label="주 메뉴">
          <Link
            href="/dashboard"
            className={navLinkClass("/dashboard")}
            aria-current={pathname === "/dashboard" || pathname.startsWith("/dashboard/") ? "page" : undefined} /* ADDED */
          >
            대시보드
          </Link>
          <Link
            href="/assets"
            className={navLinkClass("/assets")}
            aria-current={pathname === "/assets" || pathname.startsWith("/assets/") ? "page" : undefined} /* ADDED */
          >
            보유 자산
          </Link>
        </nav>
      </div>
      <div className="flex items-center gap-2 sm:gap-4">
        <Link
          href="/settings"
          className={`inline-flex items-center gap-1.5 ${navLinkClass("/settings")}`}
          aria-label="설정 페이지로 이동"
          aria-current={pathname === "/settings" ? "page" : undefined} /* ADDED */
        >
          <Settings className="h-4 w-4" aria-hidden="true" />
          <span className="hidden sm:inline">설정</span>
        </Link>
        <Button
          variant="outline"
          size="sm"
          onClick={() => logoutMutation.mutate()}
          disabled={logoutMutation.isPending}
          aria-busy={logoutMutation.isPending}
          className="text-xs sm:text-sm" /* MODIFIED */
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
