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

/** Mirrors NETWORK_ERROR_STATUS in ./api: the request never reached the server. */
export const ADMIN_NETWORK_ERROR = 0;

/** The backend answered and rejected the session. Real information. */
export function isAdminAuthError(e: unknown): boolean {
  return e instanceof AdminFetchError && (e.status === 401 || e.status === 403);
}

/** Nobody answered. Says nothing about whether the session is valid. */
export function isAdminNetworkError(e: unknown): boolean {
  return e instanceof AdminFetchError && e.status === ADMIN_NETWORK_ERROR;
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
  }).catch((e) => {
    // A rejected fetch never reached the backend. Normalise it so callers can
    // tell it apart from a 401 - otherwise a dropped packet looks identical to
    // an invalid session, and the caller clears a perfectly good token.
    if (e instanceof AdminFetchError) throw e;
    throw new AdminFetchError(
      ADMIN_NETWORK_ERROR,
      "We couldn't reach the server. Check your connection."
    );
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
