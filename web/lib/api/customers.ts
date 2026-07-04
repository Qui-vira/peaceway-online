import { apiFetch } from "@/lib/api";

// In-memory auth cache — survives SPA navigations, cleared on logout/error.
// TTL keeps the cache fresh without hammering Railway on every page mount.
const AUTH_TTL_MS = 30_000; // 30 seconds
let _meCache: { profile: CustomerProfile; expiresAt: number } | null = null;

export function invalidateMeCache() {
  _meCache = null;
}

export type Zone = {
  id: string;
  name: string;
  fee: number | null;
  eta_minutes: number | null;
};

export const FALLBACK_ZONES: Zone[] = [
  "Igando",
  "Agodo",
  "Ikotun",
  "Egbeda",
  "Isheri",
  "Idimu",
  "Iyana Ipaja",
  "Egbe",
  "Ejigbo",
  "Ijegun",
  "Other Lagos Mainland",
].map((name) => ({
  id: `fallback-${name.toLowerCase().replace(/[^a-z0-9]+/g, "-")}`,
  name,
  fee: null,
  eta_minutes: null,
}));

export function formatZoneOption(zone: Zone): string {
  const fee = typeof zone.fee === "number" && zone.fee > 0
    ? ` · ₦${zone.fee.toLocaleString()}`
    : "";
  const eta = zone.eta_minutes ? ` · ~${zone.eta_minutes}min` : "";
  return `${zone.name}${fee}${eta}`;
}

export type CustomerProfile = {
  id: string;
  full_name: string | null;
  phone: string | null;
  email: string | null;
  delivery_area: string | null;
  telegram_username?: string | null;
  telegram_linked?: boolean;
};

export type RegisterPayload = {
  full_name: string;
  phone: string;
  email?: string;
  delivery_area?: string;
};

export async function registerCustomer(
  data: RegisterPayload
): Promise<CustomerProfile> {
  return apiFetch<CustomerProfile>("/customers", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function getMe(): Promise<CustomerProfile> {
  const now = Date.now();
  if (_meCache && _meCache.expiresAt > now) {
    return _meCache.profile;
  }
  const profile = await apiFetch<CustomerProfile>("/me");
  _meCache = { profile, expiresAt: now + AUTH_TTL_MS };
  return profile;
}

export type UpdateProfilePayload = {
  full_name?: string;
  email?: string;
  delivery_area?: string;
};

export async function updateProfile(
  data: UpdateProfilePayload
): Promise<CustomerProfile> {
  return apiFetch<CustomerProfile>("/me", {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

/** Raw payload the Telegram Login Widget hands to the onauth callback. */
export type TelegramAuthPayload = {
  id: number;
  first_name?: string;
  last_name?: string;
  username?: string;
  photo_url?: string;
  auth_date: number;
  hash: string;
};

export async function linkTelegram(
  payload: TelegramAuthPayload
): Promise<CustomerProfile> {
  const profile = await apiFetch<CustomerProfile>("/me/telegram-link", {
    method: "POST",
    body: JSON.stringify(payload),
  });
  _meCache = { profile, expiresAt: Date.now() + AUTH_TTL_MS };
  return profile;
}

export async function listZones(): Promise<Zone[]> {
  try {
    const zones = await apiFetch<Zone[]>("/zones");
    return zones.length ? zones : FALLBACK_ZONES;
  } catch {
    return FALLBACK_ZONES;
  }
}

export async function logout(): Promise<void> {
  invalidateMeCache();
  await apiFetch<void>("/logout", { method: "POST" });
}
