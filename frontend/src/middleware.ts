import { NextRequest, NextResponse } from "next/server";

interface JwtPayload {
  sub?: string;
  exp?: number;
  role?: string;
}

const PUBLIC_PATHS = new Set([
  "/login",
  "/401",
  "/403",
  "/404",
  "/500",
  "/api/auth/login",
  "/api/auth/logout",
]);

function decodeJwtPayload(token: string): JwtPayload | null {
  try {
    const parts = token.split(".");
    if (parts.length !== 3) {
      return null;
    }

    const base64Url = parts[1];
    const base64 = base64Url.replace(/-/g, "+").replace(/_/g, "/");
    const padded = base64.padEnd(
      base64.length + ((4 - (base64.length % 4)) % 4),
      "="
    );
    const jsonPayload = atob(padded);
    return JSON.parse(jsonPayload) as JwtPayload;
  } catch {
    return null;
  }
}

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // Skip Next.js internals and static assets
  if (
    pathname.startsWith("/_next") ||
    pathname.startsWith("/favicon") ||
    pathname.includes(".")
  ) {
    return NextResponse.next();
  }

  const token = request.cookies.get("session_token")?.value;
  const payload = token ? decodeJwtPayload(token) : null;
  const nowSeconds = Math.floor(Date.now() / 1000);
  const isExpired =
    payload?.exp !== undefined && payload.exp < nowSeconds;
  const isAuthenticated = Boolean(token && payload && !isExpired);

  // If authenticated user visits /login, redirect to workspace (/)
  if (pathname === "/login" && isAuthenticated) {
    return NextResponse.redirect(new URL("/", request.url));
  }

  // Allow public routes
  if (PUBLIC_PATHS.has(pathname)) {
    return NextResponse.next();
  }

  // Block unauthenticated or expired sessions on all private routes
  if (!isAuthenticated) {
    const loginUrl = new URL("/login", request.url);
    if (pathname !== "/") {
      loginUrl.searchParams.set("from", pathname);
    }
    if (isExpired) {
      loginUrl.searchParams.set("expired", "1");
    }
    const response = NextResponse.redirect(loginUrl);
    if (token) {
      response.cookies.delete("session_token");
    }
    return response;
  }

  // Role-based access control: Partner-only calibration settings
  if (pathname.startsWith("/calibration") && payload?.role === "analyst") {
    return NextResponse.redirect(new URL("/403", request.url));
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};

