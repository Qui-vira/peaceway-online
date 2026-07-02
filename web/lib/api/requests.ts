import { apiFetch } from "@/lib/api";

export type Urgency =
  | "TODAY"
  | "WITHIN_24H"
  | "THIS_WEEK"
  | "JUST_CHECKING";

export type ProductRequest = {
  id: string;
  product_name: string;
  strength: string | null;
  form: string | null;
  quantity: string | null;
  urgency: string | null;
  note: string | null;
  status: string;
  customer_visible_message: string | null;
  created_at: string;
};

export type Message = {
  id: string;
  sender_type: "customer" | "admin" | "system";
  message_text: string;
  created_at: string;
};

export type ProductRequestDetail = ProductRequest & { thread: Message[] };

export type CreateRequestPayload = {
  product_name: string;
  strength?: string;
  form?: string;
  quantity?: string;
  urgency?: Urgency;
  note?: string;
};

export async function createRequest(
  data: CreateRequestPayload
): Promise<ProductRequest> {
  return apiFetch<ProductRequest>("/requests", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function listRequests(): Promise<ProductRequest[]> {
  return apiFetch<ProductRequest[]>("/requests");
}

export async function getRequest(id: string): Promise<ProductRequestDetail> {
  return apiFetch<ProductRequestDetail>(`/requests/${id}`);
}
