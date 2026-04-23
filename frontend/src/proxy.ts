import { NextResponse, type NextRequest } from "next/server";

/**
 * Next 16 proxy (renamed from middleware) — runs at the edge before render.
 * Redirects unauthenticated requests to /login; lets auth routes + assets pass.
 */
export function proxy(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const hasAccessToken = request.cookies.has("access_token");

  // Public paths that don't require auth
  const isPublic =
    pathname === "/login" ||
    pathname === "/callback" ||
    pathname.startsWith("/_next") ||
    pathname.startsWith("/favicon") ||
    pathname.startsWith("/icons/");

  if (isPublic) {
    // If already logged in, bounce /login → /
    if (hasAccessToken && pathname === "/login") {
      return NextResponse.redirect(new URL("/", request.url));
    }
    return NextResponse.next();
  }

  if (!hasAccessToken) {
    const loginUrl = new URL("/login", request.url);
    return NextResponse.redirect(loginUrl);
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
    // Match everything except Next internals and static files with extensions
    "/((?!_next/static|_next/image|favicon.ico|.*\\..*).*)",
  ],
};
