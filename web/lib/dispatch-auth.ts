/**
 * Dispatch (rider) portal auth helpers. A SEPARATE domain from staff, customers
 * and suppliers. Riders authenticate against dispatch_partners via email OTP and
 * get a session token stored under its own key, sent as X-Dispatch-Session.
 */
import { getApiBase } from "./api";

const TOKEN_KEY = "pw_dispatch_session_token";

export function getDispatchToken(): string | null {
  if (typeof window === "undefined") return null;
  return sessionStorage.getItem(TOKEN_KEY);
}

export function setDispatchToken(token: string): void {
  if (typeof window === "undefined") return;
  sessionStorage.setItem(TOKEN_KEY, token);
}

export function clearDispatchToken(): void {
  if (typeof window === "undefined") return;
  sessionStorage.removeItem(TOKEN_KEY);
}

export class DispatchFetchError extends Error {
  status: number;
  constructor(status: number, detail: string) {
    super(detail);
    this.status = status;
  }
}

export function dispatchFetch<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getDispatchToken();
  const API_BASE = getApiBase();
  return fetch(`${API_BASE}${path}`, {
    ...options,
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { "X-Dispatch-Session": token } : {}),
      ...(options.headers ?? {}),
    },
  }).then(async (res) => {
    if (res.status === 401) {
      clearDispatchToken();
      throw new DispatchFetchError(401, "Session expired.");
    }
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      throw new DispatchFetchError(res.status, (body as { detail?: string })?.detail ?? res.statusText);
    }
    if (res.status === 204) return undefined as unknown as T;
    return res.json() as Promise<T>;
  });
}
