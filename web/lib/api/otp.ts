import { apiFetch } from "@/lib/api";
import type { CustomerProfile } from "@/lib/api/customers";

export type SendOtpPayload = {
  phone: string;
  email?: string;
  full_name?: string;
  mode: "signup" | "login";
};

export type SendOtpResponse = {
  email_hint: string;
};

export async function sendOtp(data: SendOtpPayload): Promise<SendOtpResponse> {
  return apiFetch<SendOtpResponse>("/otp/send", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function verifyOtp(data: {
  phone: string;
  code: string;
}): Promise<CustomerProfile> {
  return apiFetch<CustomerProfile>("/otp/verify", {
    method: "POST",
    body: JSON.stringify(data),
  });
}
