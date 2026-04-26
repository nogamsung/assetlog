import { type NextRequest, NextResponse } from "next/server";

const PROTECTED_ROUTES = ["/", "/dashboard", "/assets", "/settings", "/profile"];
const PUBLIC_ROUTES = ["/login"]; // {/* MODIFIED */}

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

// {/* ADDED */}
function buildCsp(nonce: string): string {
  const apiBase = process.env.NEXT_PUBLIC_API_URL ?? "";
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

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // /signup 은 삭제됨 — /login 으로 영구 리다이렉트 {/* ADDED */}
  if (pathname === "/signup" || pathname.startsWith("/signup/")) { // {/* ADDED */}
    return NextResponse.redirect(new URL("/login", request.url), 308); // {/* ADDED */}
  } // {/* ADDED */}

  // 공개 라우트는 토큰 검사 없이 통과
  if (isPublicRoute(pathname)) {
    return NextResponse.next();
  }

  // 보호 라우트 확인
  if (isProtectedRoute(pathname)) {
    const token = request.cookies.get("access_token");

    if (!token) {
      const loginUrl = new URL("/login", request.url);
      loginUrl.searchParams.set("from", pathname);
      return NextResponse.redirect(loginUrl);
    }
  }

  // CSP nonce 생성 + 헤더 부착 {/* ADDED */}
  const nonce = Buffer.from(crypto.randomUUID()).toString("base64"); // {/* ADDED */}
  const csp = buildCsp(nonce); // {/* ADDED */}

  const requestHeaders = new Headers(request.headers); // {/* ADDED */}
  requestHeaders.set("x-nonce", nonce); // {/* ADDED */}

  const response = NextResponse.next({ // {/* ADDED */}
    request: { headers: requestHeaders }, // {/* ADDED */}
  }); // {/* ADDED */}
  response.headers.set("Content-Security-Policy", csp); // {/* ADDED */}
  response.headers.set("x-nonce", nonce); // {/* ADDED */}

  return response; // {/* ADDED */}
}

export const config = {
  matcher: [
    /*
     * _next/static, _next/image, favicon.ico, 정적 파일 제외
     */
    "/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp|ico|css|js)$).*)",
  ],
};
