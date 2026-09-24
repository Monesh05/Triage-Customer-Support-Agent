// name: app/api/auth/logout/route.ts
// purpose: Clears the httpOnly auth cookie (Phase 10, spec section 27). Works for both the
//          customer portal and the Support Console since they share one cookie/token slot.
// author: CloudDesk Team
// date: 2026-09-24

import { NextResponse } from "next/server";

import { AUTH_TOKEN_COOKIE } from "@/lib/constants";

export async function POST(): Promise<NextResponse> {
  const response = NextResponse.json({ ok: true });
  response.cookies.delete(AUTH_TOKEN_COOKIE);
  return response;
}
