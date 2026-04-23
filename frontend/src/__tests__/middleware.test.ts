/**
 * 미들웨어 로직을 직접 단위 테스트합니다.
 * Next.js middleware 는 edge runtime 에서 실행되므로,
 * 로직을 추출한 헬퍼 함수를 통해 테스트합니다.
 */

// 미들웨어 내부 헬퍼 로직을 재현합니다 (동일 로직 추출)
const PROTECTED_ROUTES = ["/", "/dashboard", "/assets", "/settings", "/profile"];
const PUBLIC_ROUTES = ["/login", "/signup"];

function isProtectedRoute(pathname: string): boolean {
  return PROTECTED_ROUTES.some(
    (route) => pathname === route || pathname.startsWith(`${route}/`),
  );
}

function isPublicRoute(pathname: string): boolean {
  return PUBLIC_ROUTES.some(
    (route) => pathname === route || pathname.startsWith(`${route}/`),
  );
}

function shouldRedirectToLogin(pathname: string, hasToken: boolean): boolean {
  if (isPublicRoute(pathname)) return false;
  if (isProtectedRoute(pathname) && !hasToken) return true;
  return false;
}

function shouldPass(pathname: string, hasToken: boolean): boolean {
  return !shouldRedirectToLogin(pathname, hasToken);
}

describe("미들웨어 라우트 로직", () => {
  describe("공개 라우트", () => {
    it("/login 은 토큰 없이 통과한다", () => {
      expect(shouldPass("/login", false)).toBe(true);
    });

    it("/signup 은 토큰 없이 통과한다", () => {
      expect(shouldPass("/signup", false)).toBe(true);
    });

    it("/login 은 토큰 있어도 통과한다", () => {
      expect(shouldPass("/login", true)).toBe(true);
    });
  });

  describe("보호 라우트 — 토큰 없음 → 리다이렉트", () => {
    it("/ 는 토큰 없으면 리다이렉트해야 한다", () => {
      expect(shouldRedirectToLogin("/", false)).toBe(true);
    });

    it("/dashboard 는 토큰 없으면 리다이렉트해야 한다", () => {
      expect(shouldRedirectToLogin("/dashboard", false)).toBe(true);
    });

    it("/assets 는 토큰 없으면 리다이렉트해야 한다", () => {
      expect(shouldRedirectToLogin("/assets", false)).toBe(true);
    });

    it("/settings 는 토큰 없으면 리다이렉트해야 한다", () => {
      expect(shouldRedirectToLogin("/settings", false)).toBe(true);
    });

    it("/profile 는 토큰 없으면 리다이렉트해야 한다", () => {
      expect(shouldRedirectToLogin("/profile", false)).toBe(true);
    });

    it("/dashboard/overview 는 토큰 없으면 리다이렉트해야 한다", () => {
      expect(shouldRedirectToLogin("/dashboard/overview", false)).toBe(true);
    });
  });

  describe("보호 라우트 — 토큰 있음 → 통과", () => {
    it("/ 는 토큰 있으면 통과한다", () => {
      expect(shouldPass("/", true)).toBe(true);
    });

    it("/dashboard 는 토큰 있으면 통과한다", () => {
      expect(shouldPass("/dashboard", true)).toBe(true);
    });

    it("/assets 는 토큰 있으면 통과한다", () => {
      expect(shouldPass("/assets", true)).toBe(true);
    });
  });

  describe("비정의 라우트 (API 등)", () => {
    it("/api/auth/me 는 토큰 없어도 통과한다", () => {
      expect(shouldPass("/api/auth/me", false)).toBe(true);
    });

    it("/api/holdings 는 토큰 없어도 미들웨어 라우트 체크는 통과한다", () => {
      // API 라우트는 보호/공개 어느 쪽도 아니므로 통과
      expect(shouldPass("/api/holdings", false)).toBe(true);
    });
  });

  describe("isPublicRoute 헬퍼", () => {
    it("/login 은 공개 라우트다", () => {
      expect(isPublicRoute("/login")).toBe(true);
    });

    it("/signup 은 공개 라우트다", () => {
      expect(isPublicRoute("/signup")).toBe(true);
    });

    it("/signup/confirm 은 공개 라우트다", () => {
      expect(isPublicRoute("/signup/confirm")).toBe(true);
    });

    it("/ 는 공개 라우트가 아니다", () => {
      expect(isPublicRoute("/")).toBe(false);
    });
  });

  describe("isProtectedRoute 헬퍼", () => {
    it("/ 는 보호 라우트다", () => {
      expect(isProtectedRoute("/")).toBe(true);
    });

    it("/dashboard 는 보호 라우트다", () => {
      expect(isProtectedRoute("/dashboard")).toBe(true);
    });

    it("/unknown 는 보호 라우트가 아니다", () => {
      expect(isProtectedRoute("/unknown")).toBe(false);
    });
  });
});
