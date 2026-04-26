/**
 * 미들웨어 로직을 직접 단위 테스트합니다.
 * Next.js middleware 는 edge runtime 에서 실행되므로,
 * 로직을 추출한 헬퍼 함수를 통해 테스트합니다.
 */

// 미들웨어 내부 헬퍼 로직을 재현합니다 (동일 로직 추출)
const PROTECTED_ROUTES = ["/", "/dashboard", "/assets", "/settings", "/profile"];
const PUBLIC_ROUTES = ["/login"]; // {/* MODIFIED */}

// {/* ADDED */}
function buildCsp(nonce: string, apiUrl?: string): string {
  const apiBase = apiUrl ?? "";
  const connectSrc = ["'self'"];
  if (apiBase && !apiBase.startsWith("/")) {
    try {
      const u = new URL(apiBase);
      connectSrc.push(u.origin);
    } catch {
      // 잘못된 URL 은 무시
    }
  }

  const directives = [
    "default-src 'self'",
    `script-src 'self' 'nonce-${nonce}' 'strict-dynamic'`,
    "style-src 'self' 'unsafe-inline'",
    "img-src 'self' data: blob:",
    "font-src 'self' data:",
    `connect-src ${connectSrc.join(" ")}`,
    "frame-ancestors 'none'",
    "form-action 'self'",
    "base-uri 'self'",
    "object-src 'none'",
    "upgrade-insecure-requests",
  ];
  return directives.join("; ");
}
// {/* ADDED */}

function isSignupRoute(pathname: string): boolean { // {/* ADDED */}
  return pathname === "/signup" || pathname.startsWith("/signup/"); // {/* ADDED */}
} // {/* ADDED */}

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

function shouldRedirectToSignup(pathname: string): boolean { // {/* ADDED */}
  return isSignupRoute(pathname); // {/* ADDED */}
} // {/* ADDED */}

function shouldRedirectToLogin(pathname: string, hasToken: boolean): boolean {
  if (isSignupRoute(pathname)) return false; // handled separately {/* ADDED */}
  if (isPublicRoute(pathname)) return false;
  if (isProtectedRoute(pathname) && !hasToken) return true;
  return false;
}

function shouldPass(pathname: string, hasToken: boolean): boolean {
  return !shouldRedirectToLogin(pathname, hasToken) && !shouldRedirectToSignup(pathname);
}

describe("미들웨어 라우트 로직", () => {
  describe("/signup 리다이렉트 — 단일 사용자 전환", () => { // {/* ADDED */}
    it("/signup 은 /login 으로 리다이렉트된다", () => {
      expect(shouldRedirectToSignup("/signup")).toBe(true);
    });

    it("/signup/confirm 도 /login 으로 리다이렉트된다", () => {
      expect(shouldRedirectToSignup("/signup/confirm")).toBe(true);
    });

    it("/login 은 리다이렉트되지 않는다", () => {
      expect(shouldRedirectToSignup("/login")).toBe(false);
    });
  });

  describe("공개 라우트", () => {
    it("/login 은 토큰 없이 통과한다", () => {
      expect(shouldPass("/login", false)).toBe(true);
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
      expect(shouldPass("/api/holdings", false)).toBe(true);
    });
  });

  describe("isPublicRoute 헬퍼", () => {
    it("/login 은 공개 라우트다", () => {
      expect(isPublicRoute("/login")).toBe(true);
    });

    it("/signup 은 공개 라우트가 아니다 (리다이렉트 대상)", () => { // {/* MODIFIED */}
      expect(isPublicRoute("/signup")).toBe(false);
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

// {/* ADDED */}
describe("CSP buildCsp", () => {
  describe("기본 디렉티브", () => {
    it("default-src 'self' 를 포함한다", () => {
      const csp = buildCsp("testnonce");
      expect(csp).toContain("default-src 'self'");
    });

    it("frame-ancestors 'none' 를 포함한다", () => {
      const csp = buildCsp("testnonce");
      expect(csp).toContain("frame-ancestors 'none'");
    });

    it("object-src 'none' 를 포함한다", () => {
      const csp = buildCsp("testnonce");
      expect(csp).toContain("object-src 'none'");
    });

    it("form-action 'self' 를 포함한다", () => {
      const csp = buildCsp("testnonce");
      expect(csp).toContain("form-action 'self'");
    });

    it("base-uri 'self' 를 포함한다", () => {
      const csp = buildCsp("testnonce");
      expect(csp).toContain("base-uri 'self'");
    });

    it("style-src 'unsafe-inline' 를 포함한다", () => {
      const csp = buildCsp("testnonce");
      expect(csp).toContain("style-src 'self' 'unsafe-inline'");
    });

    it("upgrade-insecure-requests 를 포함한다", () => {
      const csp = buildCsp("testnonce");
      expect(csp).toContain("upgrade-insecure-requests");
    });
  });

  describe("nonce 삽입", () => {
    it("script-src 에 전달된 nonce 가 포함된다", () => {
      const nonce = "abc123xyz";
      const csp = buildCsp(nonce);
      expect(csp).toContain(`'nonce-${nonce}'`);
    });

    it("script-src 에 'strict-dynamic' 이 포함된다", () => {
      const csp = buildCsp("anynonce");
      expect(csp).toContain("'strict-dynamic'");
    });

    it("nonce 가 다르면 CSP 문자열도 달라진다", () => {
      const csp1 = buildCsp("nonce-aaa");
      const csp2 = buildCsp("nonce-bbb");
      expect(csp1).not.toBe(csp2);
    });
  });

  describe("connect-src + NEXT_PUBLIC_API_URL", () => {
    it("API URL 미설정 시 connect-src 는 self 만 포함한다", () => {
      const csp = buildCsp("testnonce", "");
      expect(csp).toContain("connect-src 'self'");
      expect(csp).not.toContain("localhost");
    });

    it("외부 도메인 API URL 설정 시 origin 이 connect-src 에 추가된다", () => {
      const csp = buildCsp("testnonce", "http://localhost:8000");
      expect(csp).toContain("connect-src 'self' http://localhost:8000");
    });

    it("경로 포함 URL 에서도 origin 만 추출된다", () => {
      const csp = buildCsp("testnonce", "https://api.example.com/v1/path");
      expect(csp).toContain("connect-src 'self' https://api.example.com");
      expect(csp).not.toContain("/v1/path");
    });

    it("상대 경로(/api)는 connect-src 에 추가되지 않는다", () => {
      const csp = buildCsp("testnonce", "/api");
      const connectLine = csp.split("; ").find((d) => d.startsWith("connect-src"));
      expect(connectLine).toBe("connect-src 'self'");
    });

    it("잘못된 URL 문자열은 무시되고 self 만 남는다", () => {
      const csp = buildCsp("testnonce", "not-a-valid-url");
      const connectLine = csp.split("; ").find((d) => d.startsWith("connect-src"));
      expect(connectLine).toBe("connect-src 'self'");
    });
  });
});
// {/* ADDED */}
