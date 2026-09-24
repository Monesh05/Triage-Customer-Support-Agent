// name: lib/api/client.ts
// purpose: Small typed fetch wrapper for the CloudDesk backend REST API, with a single shared
//          error type/handling path (per Phase 9 dev rules: no ad-hoc try/catch scattered across
//          call sites). Base URL comes from NEXT_PUBLIC_API_BASE_URL (public env var, safe: it is
//          just a hostname, never a secret) with a documented local-dev default.
//
//          Phase 10 (spec section 27) authentication: every protected backend route now requires
//          `Authorization: Bearer <jwt>`, and the JWT lives in an httpOnly cookie (never readable
//          by client-side JS, to keep it out of XSS's reach). This module is imported from BOTH
//          Server Components (lib/api/customers.ts etc., called from page.tsx) and Client
//          Components (hooks/use-conversation.ts, components/console/approval-queue.tsx), so it
//          branches on `typeof window`:
//            - Server: call the backend directly, reading the cookie here (server-side code CAN
//              read an httpOnly cookie) and attaching the header ourselves.
//            - Browser: the cookie is invisible to this code, so route the request through this
//              app's own same-origin proxy (app/api/backend/[...path]/route.ts), which runs
//              server-side and attaches the real Authorization header before forwarding.
// author: CloudDesk Team
// date: 2026-09-24

export const API_BASE_URL: string =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8010/api/v1";

const BROWSER_PROXY_BASE_PATH: string = "/api/backend";

async function resolveServerAuthHeader(): Promise<Record<string, string>> {
  // Dynamically imported so this module stays importable from Client Components: `next/headers`
  // cannot be statically imported into a module that also ships in the client bundle.
  const { cookies } = await import("next/headers");
  const { AUTH_TOKEN_COOKIE } = await import("@/lib/constants");
  const cookieStore = await cookies();
  const token = cookieStore.get(AUTH_TOKEN_COOKIE)?.value;
  return token ? { Authorization: `Bearer ${token}` } : {};
}

/** A normalized API failure: either a network error or a non-2xx HTTP response. */
export class ApiError extends Error {
  readonly status: number | null;
  readonly detail: string;

  constructor(message: string, status: number | null, detail: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

interface ErrorBody {
  detail?: string;
}

function isErrorBody(value: unknown): value is ErrorBody {
  return typeof value === "object" && value !== null;
}

async function parseErrorDetail(response: Response): Promise<string> {
  try {
    const body: unknown = await response.json();
    if (isErrorBody(body) && typeof body.detail === "string") {
      return body.detail;
    }
  } catch {
    // Response body was not JSON; fall through to the generic message below.
  }
  return `Request failed with status ${response.status}`;
}

export interface RequestOptions {
  method?: "GET" | "POST" | "PATCH" | "DELETE";
  body?: unknown;
  cache?: RequestCache;
}

/** Perform one API call against the CloudDesk backend, returning parsed JSON of type T or
 * throwing a normalized `ApiError` for both network failures and non-2xx responses. Attaches the
 * authenticated caller's bearer token automatically (see module docstring for the server/browser
 * split); call sites never need to think about auth headers themselves. */
export async function apiRequest<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const isBrowser = typeof window !== "undefined";
  const url = isBrowser ? `${BROWSER_PROXY_BASE_PATH}${path}` : `${API_BASE_URL}${path}`;
  const authHeader = isBrowser ? {} : await resolveServerAuthHeader();

  let response: Response;
  try {
    response = await fetch(url, {
      method: options.method ?? "GET",
      headers: {
        ...(options.body ? { "Content-Type": "application/json" } : {}),
        ...authHeader,
      },
      body: options.body ? JSON.stringify(options.body) : undefined,
      cache: options.cache ?? "no-store",
      credentials: isBrowser ? "include" : undefined,
    });
  } catch (cause) {
    const reason = cause instanceof Error ? cause.message : "Unknown network error";
    throw new ApiError(`Could not reach the CloudDesk API (${reason})`, null, reason);
  }

  if (!response.ok) {
    const detail = await parseErrorDetail(response);
    throw new ApiError(detail, response.status, detail);
  }

  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
}
