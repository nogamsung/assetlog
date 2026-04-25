"use client";

import { Button } from "@/components/ui/button";

interface ErrorProps {
  error: Error & { digest?: string };
  reset: () => void;
}

export default function SettingsError({ error, reset }: ErrorProps) {
  return (
    <div className="container mx-auto max-w-2xl px-4 py-8 text-center">
      <h2 className="text-xl font-semibold mb-2">오류가 발생했습니다</h2>
      <p className="text-muted-foreground mb-6 text-sm">
        {error.message ?? "설정을 불러오는 중 문제가 생겼습니다."}
      </p>
      <Button onClick={reset}>다시 시도</Button>
    </div>
  );
}
