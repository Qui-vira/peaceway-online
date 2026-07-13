/**
 * Partner portal auth helpers - a SEPARATE domain from staff (`admin-auth.ts`).
 *
 * Partners (wholesalers/suppliers) authenticate against `network_partners` via
 * email OTP and get a partner session token, stored under its own key and sent
 * as `X-Partner-Session`. This file intentionally shares nothing with the admin
 * auth client so the two sessions can never be confused.
 */
import { getApiBase } from "./api";

const TOKEN_KEY = "pw_partner_session_token";

export function getPartnerToken(): string | null {
  if (typeof window === "undefined") return null;
  return sessionStorage.getItem(TOKEN_KEY);
}

export function setPartnerToken(token: string): void {
  if (typeof window === "undefined") return;
  sessionStorage.setItem(TOKEN_KEY, token);
}

export function clearPartnerToken(): void {
  if (typeof window === "undefined") return;
  sessionStorage.removeItem(TOKEN_KEY);
}

export class PartnerFetchError extends Error {
  status: number;
  constructor(status: number, detail: string) {
    super(detail);
    this.status = status;
  }
}

let _reloading = false;

export function partnerFetch<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getPartnerToken();
  const API_BASE = getApiBase();
  return fetch(`${API_BASE}${path}`, {
    ...options,
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { "X-Partner-Session": token } : {}),
      ...(options.headers ?? {}),
    },
  }).then(async (res) => {
    if (res.status === 401) {
      if (!_reloading) {
        _reloading = true;
        clearPartnerToken();
        window.location.reload();
      }
      throw new PartnerFetchError(401, "Session expired.");
    }
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      throw new PartnerFetchError(res.status, (body as { detail?: string })?.detail ?? res.statusText);
    }
    if (res.status === 204) return undefined as unknown as T;
    return res.json() as Promise<T>;
  });
}
