"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { ThemeToggle } from "@/components/theme-toggle";
import { useCurrentUser, useLogout } from "@/hooks/use-auth";

export default function SettingsPage() {
  const { data: user } = useCurrentUser();
  const logoutMutation = useLogout();

  const createdAt = user?.createdAt
    ? new Date(user.createdAt).toLocaleDateString("ko-KR", {
        year: "numeric",
        month: "long",
        day: "numeric",
      })
    : null;

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
          {user && (
            <>
              <div className="space-y-1">
                <p className="text-sm font-medium text-muted-foreground">이메일</p>
                <p className="text-sm">{user.email}</p>
              </div>
              <div className="space-y-1">
                <p className="text-sm font-medium text-muted-foreground">가입일</p>
                <p className="text-sm">{createdAt}</p>
              </div>
            </>
          )}
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
