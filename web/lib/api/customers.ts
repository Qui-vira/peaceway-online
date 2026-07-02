import { apiFetch } from "@/lib/api";

export type Zone = {
  id: string;
  name: string;
  fee: number;
  eta_minutes: number | null;
};

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
  return apiFetch<Zone[]>("/zones");
}

export async function logout(): Promise<void> {
  await apiFetch<void>("/logout", { method: "POST" });
}
