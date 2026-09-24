// name: lib/api/client.ts
// purpose: Small typed fetch wrapper for the CloudDesk backend REST API, with a single shared
//          error type/handling path (per Phase 9 dev rules: no ad-hoc try/catch scattered across
//          call sites). Base URL comes from NEXT_PUBLIC_API_BASE_URL (public env var, safe: it is
//          just a hostname, never a secret) with a documented local-dev default.
// author: CloudDesk Team
// date: 2026-09-24

export const API_BASE_URL: string =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8010/api/v1";

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
 * throwing a normalized `ApiError` for both network failures and non-2xx responses. */
export async function apiRequest<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const url = `${API_BASE_URL}${path}`;
  let response: Response;
  try {
    response = await fetch(url, {
      method: options.method ?? "GET",
      headers: options.body ? { "Content-Type": "application/json" } : undefined,
      body: options.body ? JSON.stringify(options.body) : undefined,
      cache: options.cache ?? "no-store",
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
