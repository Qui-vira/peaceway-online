import { apiFetch } from "@/lib/api";

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
  return apiFetch<CustomerProfile>("/me");
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

export async function listZones(): Promise<Zone[]> {
  try {
    const zones = await apiFetch<Zone[]>("/zones");
    return zones.length ? zones : FALLBACK_ZONES;
  } catch {
    return FALLBACK_ZONES;
  }
}

export async function logout(): Promise<void> {
  await apiFetch<void>("/logout", { method: "POST" });
}
