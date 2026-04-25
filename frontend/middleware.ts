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

  return NextResponse.next();
}

export const config = {
  matcher: [
    /*
     * _next/static, _next/image, favicon.ico, 정적 파일 제외
     */
    "/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp|ico|css|js)$).*)",
  ],
};
