"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { ThemeToggle } from "@/components/theme-toggle";
import { Download } from "lucide-react";
import { useLogout } from "@/hooks/use-auth";
import { useExportData } from "@/hooks/use-export";

export default function SettingsPage() {
  const logoutMutation = useLogout();
  const exportMutation = useExportData();

  return (
    <div className="container mx-auto max-w-2xl px-4 py-8 space-y-6">
      <h1 className="text-2xl font-bold">설정</h1>

      {/* 계정 카드 */}
      <Card>
        <CardHeader>
          <CardTitle>계정</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-1">
            <p className="text-sm font-medium text-muted-foreground">계정 유형</p>
            <p className="text-sm">단일 사용자 계정</p>
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={() => logoutMutation.mutate()}
            disabled={logoutMutation.isPending}
            aria-busy={logoutMutation.isPending}
            aria-label="로그아웃"
          >
            {logoutMutation.isPending ? "로그아웃 중..." : "로그아웃"}
          </Button>
        </CardContent>
      </Card>

      {/* 테마 카드 */}
      <Card>
        <CardHeader>
          <CardTitle>테마</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <ThemeToggle />
          <p className="text-sm text-muted-foreground">
            System은 OS 설정을 따릅니다.
          </p>
        </CardContent>
      </Card>

      {/* 데이터 백업 카드 — ADDED */}
      <Card>
        <CardHeader>
          <CardTitle>데이터 백업</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-sm text-muted-foreground">
            보유 자산과 거래 내역을 파일로 내려받습니다. 정기적인 백업을 권장합니다.
          </p>
          <div className="flex flex-wrap gap-2">
            <Button
              variant="outline"
              onClick={() => exportMutation.mutate("json")}
              disabled={exportMutation.isPending}
              aria-label="데이터를 JSON 으로 내려받기"
            >
              <Download className="h-4 w-4 mr-1" /> JSON 다운로드
            </Button>
            <Button
              variant="outline"
              onClick={() => exportMutation.mutate("csv")}
              disabled={exportMutation.isPending}
              aria-label="데이터를 CSV(ZIP) 로 내려받기"
            >
              <Download className="h-4 w-4 mr-1" /> CSV (ZIP) 다운로드
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* 보안 카드 */}
      <Card>
        <CardHeader>
          <CardTitle>보안</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          <p className="text-sm text-muted-foreground">
            비밀번호는 서버 환경변수로 관리됩니다.
          </p>
          <p className="text-sm text-muted-foreground">
            비밀번호 변경은 서버 재배포가 필요합니다.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
