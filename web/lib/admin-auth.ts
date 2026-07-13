/**
 * Web admin auth helpers.
 *
 * Session token is stored in sessionStorage (cleared when tab closes).
 * Every admin API call goes through adminFetch - it injects the session
 * header and redirects to login on 401.
 */
import { getApiBase } from "./api";

const TOKEN_KEY = "pw_admin_session_token";

export function getAdminToken(): string | null {
  if (typeof window === "undefined") return null;
  return sessionStorage.getItem(TOKEN_KEY);
}

export function setAdminToken(token: string): void {
  if (typeof window === "undefined") return;
  sessionStorage.setItem(TOKEN_KEY, token);
}

export function clearAdminToken(): void {
  if (typeof window === "undefined") return;
  sessionStorage.removeItem(TOKEN_KEY);
}

export class AdminFetchError extends Error {
  status: number;
  constructor(status: number, detail: string) {
    super(detail);
    this.status = status;
  }
}

let _reloading = false;

export function adminFetch<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getAdminToken();
  const API_BASE = getApiBase();
  return fetch(`${API_BASE}${path}`, {
    ...options,
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { "X-Admin-Session": token } : {}),
      ...(options.headers ?? {}),
    },
  }).then(async (res) => {
    if (res.status === 401) {
      if (!_reloading) {
        _reloading = true;
        clearAdminToken();
        window.location.reload();
      }
      throw new AdminFetchError(401, "Session expired.");
    }
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      throw new AdminFetchError(res.status, (body as { detail?: string })?.detail ?? res.statusText);
    }
    if (res.status === 204) return undefined as unknown as T;
    return res.json() as Promise<T>;
  });
}

/** True if the admin has the given permission (or holds the wildcard). */
export function hasPermission(permissions: string[], key: string): boolean {
  return permissions.includes("*") || permissions.includes(key);
}

/** True if the admin has ANY of the given permissions. */
export function anyPermission(permissions: string[], keys: string[]): boolean {
  return keys.some((k) => hasPermission(permissions, k));
}
