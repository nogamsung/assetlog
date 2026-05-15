"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { useUpbitSync } from "@/hooks/use-upbit-sync";

export function ExchangeSyncSection() {
  const upbit = useUpbitSync();
  const result = upbit.data;

  return (
    <Card>
      <CardHeader>
        <CardTitle>거래소 동기화</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="rounded-md border border-toss-border bg-toss-card p-4 space-y-3">
          <div className="flex items-center justify-between gap-3">
            <div>
              <p className="text-sm font-medium">업비트 (Upbit)</p>
              <p className="text-xs text-muted-foreground">
                read-only API 로 매매 기록을 가져옵니다.
              </p>
            </div>
            <Button
              size="sm"
              onClick={() => upbit.mutate()}
              disabled={upbit.isPending}
              aria-busy={upbit.isPending}
              aria-label="업비트 동기화"
            >
              {upbit.isPending ? "동기화 중..." : "지금 동기화"}
            </Button>
          </div>

          {result && (
            <dl
              role="group"
              className="grid grid-cols-2 gap-x-4 gap-y-1 text-sm sm:grid-cols-4"
              aria-label="업비트 동기화 결과"
            >
              <div>
                <dt className="text-xs text-muted-foreground">조회</dt>
                <dd className="font-medium">{result.fetched}건</dd>
              </div>
              <div>
                <dt className="text-xs text-muted-foreground">신규 입력</dt>
                <dd className="font-medium text-toss-up">{result.inserted}건</dd>
              </div>
              <div>
                <dt className="text-xs text-muted-foreground">중복 스킵</dt>
                <dd className="font-medium">{result.skippedDuplicate}건</dd>
              </div>
              <div>
                <dt className="text-xs text-muted-foreground">심볼 미해석</dt>
                <dd className="font-medium">{result.skippedNoSymbol}건</dd>
              </div>
            </dl>
          )}
        </div>

        <p className="text-xs text-muted-foreground">
          서버 환경변수{" "}
          <code className="rounded bg-muted px-1 py-0.5 text-[11px]">UPBIT_ACCESS_KEY</code>
          {", "}
          <code className="rounded bg-muted px-1 py-0.5 text-[11px]">UPBIT_SECRET_KEY</code> 가
          설정돼 있어야 합니다. 동기화는 매일 1회 자동으로도 실행됩니다.
        </p>
      </CardContent>
    </Card>
  );
}
