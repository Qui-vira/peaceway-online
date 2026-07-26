/**
 * Base API client for the Peaceway web frontend.
 *
 * Browser requests use the first-party Next.js /api/v1 proxy. That keeps
 * cookies same-origin and avoids CORS failures when the backend lives on
 * Railway and the site lives on Vercel.
 */

export function getApiBase(): string {
  if (typeof window !== "undefined") {
    const host = window.location.hostname;
    if (host === "localhost" || host === "127.0.0.1" || host === "::1") {
      return "http://localhost:8000/api/v1";
    }
    return "/api/v1";
  }
  return process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";
}

/**
 * Resolve an API-relative media path (e.g. "/api/v1/media/<uuid>") to something the
 * browser can actually load.
 *
 * The backend returns these paths relative to /api/v1 because in production the
 * Next.js rewrite proxies that prefix to Railway on the same origin. In local dev
 * there is no proxy — the backend is on :8000 — so the path has to be rebased onto
 * the same origin getApiBase() already picks for data requests.
 */
export function mediaSrc(path: string): string {
  const prefix = "/api/v1";
  return path.startsWith(`${prefix}/`) ? getApiBase() + path.slice(prefix.length) : path;
}

export type ApiError = {
  status: number;
  detail: string;
};

/**
 * `status: 0` means the request never reached the backend - DNS, offline, CORS,
 * timeout, a dead server. It is deliberately not a real HTTP status, so it can
 * never collide with one.
 *
 * This distinction is the whole point. `fetch` rejects with a bare TypeError on
 * a network failure, which is indistinguishable from any other thrown value at
 * the call site. Callers were therefore writing `.catch(() => setGuest(true))`
 * and turning "I could not reach the pharmacy" into "you are not signed in" -
 * or, worse, into "you have no medication today". A failure to reach the server
 * is not information about the user. Callers must be able to tell the two apart,
 * so the client has to hand them the difference.
 */
export const NETWORK_ERROR_STATUS = 0;

export function isApiError(e: unknown): e is ApiError {
  return typeof e === "object" && e !== null && "status" in e && "detail" in e;
}

/** The backend answered, and said "not you". This IS real information. */
export function isAuthError(e: unknown): boolean {
  return isApiError(e) && (e.status === 401 || e.status === 403);
}

/** The backend never answered. This is NOT information about the user. */
export function isNetworkError(e: unknown): boolean {
  return isApiError(e) && e.status === NETWORK_ERROR_STATUS;
}

export function isNotFound(e: unknown): boolean {
  return isApiError(e) && e.status === 404;
}

export async function apiFetch<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${getApiBase()}${path}`;

  let res: Response;
  try {
    res = await fetch(url, {
      ...options,
      credentials: "include",
      headers: {
        "Content-Type": "application/json",
        ...(options.headers ?? {}),
      },
    });
  } catch {
    // fetch only rejects when the request never completed. Normalise it into an
    // ApiError so every call site sees one shape and can classify it.
    const err: ApiError = {
      status: NETWORK_ERROR_STATUS,
      detail: "We couldn't reach the pharmacy. Check your connection.",
    };
    throw err;
  }

  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body?.detail ?? detail;
    } catch {
      // non-JSON error body - use statusText as-is
    }
    const err: ApiError = { status: res.status, detail };
    throw err;
  }

  // 204 No Content - return undefined cast to T
  if (res.status === 204) return undefined as unknown as T;

  return res.json() as Promise<T>;
}

/** Typed health check - confirms the Railway backend is reachable. */
export type HealthResponse = {
  status: string;
  service: string;
  version: string;
  environment: string;
};

export async function checkApiHealth(): Promise<HealthResponse> {
  return apiFetch<HealthResponse>("/health");
}
