// name: app/api/auth/staff-login/route.ts
// purpose: Next.js Route Handler that proxies Support Console staff login to the backend's
//          POST /api/v1/auth/staff/login (Phase 10, spec section 27). Mirrors
//          app/api/auth/login/route.ts's cookie handling exactly; the only difference is which
//          backend endpoint it calls.
// author: CloudDesk Team
// date: 2026-09-24

import { NextResponse } from "next/server";

import { API_BASE_URL } from "@/lib/api/client";
import { AUTH_TOKEN_COOKIE } from "@/lib/constants";

const COOKIE_MAX_AGE_SECONDS: number = 60 * 30;

export async function POST(request: Request): Promise<NextResponse> {
  const body: unknown = await request.json().catch(() => null);

  const backendResponse = await fetch(`${API_BASE_URL}/auth/staff/login`, {
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
