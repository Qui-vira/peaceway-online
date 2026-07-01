/**
 * Base API client for the Peaceway web frontend.
 *
 * All requests go to the Railway backend via NEXT_PUBLIC_API_URL.
 * credentials: "include" is set on every request so that cookie-based
 * customer sessions (Phase 1+) work across the Vercel → Railway boundary.
 */

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

export type ApiError = {
  status: number;
  detail: string;
};

export async function apiFetch<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${API_BASE}${path}`;

  const res = await fetch(url, {
    ...options,
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...(options.headers ?? {}),
    },
  });

  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body?.detail ?? detail;
    } catch {
      // non-JSON error body — use statusText as-is
    }
    const err: ApiError = { status: res.status, detail };
    throw err;
  }

  // 204 No Content — return undefined cast to T
  if (res.status === 204) return undefined as unknown as T;

  return res.json() as Promise<T>;
}

/** Typed health check — confirms the Railway backend is reachable. */
export type HealthResponse = {
  status: string;
  service: string;
  version: string;
  environment: string;
};

export async function checkApiHealth(): Promise<HealthResponse> {
  return apiFetch<HealthResponse>("/health");
}
