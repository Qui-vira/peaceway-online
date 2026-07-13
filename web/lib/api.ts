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

export type ApiError = {
  status: number;
  detail: string;
};

export async function apiFetch<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${getApiBase()}${path}`;

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
