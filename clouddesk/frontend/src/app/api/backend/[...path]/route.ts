// name: app/api/backend/[...path]/route.ts
// purpose: Same-origin proxy to the CloudDesk backend for BROWSER-side calls (Phase 10, spec
//          section 27). The auth JWT lives in an httpOnly cookie, invisible to client-side JS by
//          design, so a client component (e.g. the chat hook's polling, the Approval Queue's
//          decision buttons) cannot attach an Authorization header itself. It instead calls this
//          same-origin route with `credentials: "include"`; this handler (running server-side,
//          where the httpOnly cookie IS readable) attaches the real Authorization header and
//          forwards the request to the actual backend. Server Components/Server Actions do not
//          need this proxy — they call the backend directly via lib/api/client.ts, which reads
//          the cookie itself in that context.
// author: CloudDesk Team
// date: 2026-09-24

import { cookies } from "next/headers";
import { NextResponse } from "next/server";

import { API_BASE_URL } from "@/lib/api/client";
import { AUTH_TOKEN_COOKIE } from "@/lib/constants";

async function proxy(request: Request, path: string[]): Promise<NextResponse> {
  const cookieStore = await cookies();
  const token = cookieStore.get(AUTH_TOKEN_COOKIE)?.value;

  const targetUrl = new URL(`${API_BASE_URL}/${path.join("/")}`);
  const incomingUrl = new URL(request.url);
  targetUrl.search = incomingUrl.search;

  const hasBody = request.method !== "GET" && request.method !== "HEAD";
  const backendResponse = await fetch(targetUrl, {
    method: request.method,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: hasBody ? await request.text() : undefined,
    cache: "no-store",
  });

  const responseBody = await backendResponse.text();
  return new NextResponse(responseBody, {
    status: backendResponse.status,
    headers: { "Content-Type": backendResponse.headers.get("Content-Type") ?? "application/json" },
  });
}

interface RouteParams {
  params: Promise<{ path: string[] }>;
}

export async function GET(request: Request, { params }: RouteParams): Promise<NextResponse> {
  const { path } = await params;
  return proxy(request, path);
}

export async function POST(request: Request, { params }: RouteParams): Promise<NextResponse> {
  const { path } = await params;
  return proxy(request, path);
}

export async function PATCH(request: Request, { params }: RouteParams): Promise<NextResponse> {
  const { path } = await params;
  return proxy(request, path);
}

export async function DELETE(request: Request, { params }: RouteParams): Promise<NextResponse> {
  const { path } = await params;
  return proxy(request, path);
}
