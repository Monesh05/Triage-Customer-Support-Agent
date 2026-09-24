// name: app/api/auth/login/route.ts
// purpose: Next.js Route Handler that proxies customer login to the backend's
//          POST /api/v1/auth/login (Phase 10, spec section 27) and, on success, stores the
//          returned JWT in an httpOnly cookie — never exposed to client-side JS (basic frontend
//          security hygiene: avoid storing a JWT somewhere an XSS payload could read it, which
//          rules out localStorage/sessionStorage and a non-httpOnly cookie alike).
// author: CloudDesk Team
// date: 2026-09-24

import { NextResponse } from "next/server";

import { API_BASE_URL } from "@/lib/api/client";
import { AUTH_TOKEN_COOKIE } from "@/lib/constants";

const COOKIE_MAX_AGE_SECONDS: number = 60 * 30; // Mirrors the backend's 30-minute token expiry.

export async function POST(request: Request): Promise<NextResponse> {
  const body: unknown = await request.json().catch(() => null);

  const backendResponse = await fetch(`${API_BASE_URL}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  const responseBody: unknown = await backendResponse.json().catch(() => ({}));
  if (!backendResponse.ok) {
    return NextResponse.json(responseBody, { status: backendResponse.status });
  }

  const { access_token: accessToken, role } = responseBody as { access_token: string; role: string };
  const response = NextResponse.json({ role });
  response.cookies.set(AUTH_TOKEN_COOKIE, accessToken, {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax",
    path: "/",
    maxAge: COOKIE_MAX_AGE_SECONDS,
  });
  return response;
}
