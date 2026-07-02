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

export async function listZones(): Promise<Zone[]> {
  return apiFetch<Zone[]>("/zones");
}
