"use client";

import Link from "next/link";
import { Button } from "@/components/ui/button";

interface ErrorProps {
  error: Error & { digest?: string };
  reset: () => void;
}

export default function DashboardError({ error, reset }: ErrorProps) {
  return (
    <div className="container mx-auto max-w-5xl px-4 py-8 text-center">
      <h2 className="text-xl font-semibold mb-2">오류가 발생했습니다</h2>
      <p className="text-muted-foreground mb-6 text-sm">
        {error.message ?? "대시보드를 불러오는 중 문제가 생겼습니다."}
      </p>
      <div className="flex justify-center gap-3">
        <Button onClick={reset}>다시 시도</Button>
        <Link
          href="/"
          className="inline-flex items-center justify-center rounded-md border border-input bg-background px-4 py-2 text-sm font-medium shadow-sm hover:bg-accent hover:text-accent-foreground transition-colors"
        >
          홈으로
        </Link>
      </div>
    </div>
  );
}
