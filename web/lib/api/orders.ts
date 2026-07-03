import { apiFetch } from "@/lib/api";

export interface OrderItem {
  product_id: string;
  product_name: string;
  quantity: number;
  unit_price: string;
  line_total: string;
}

export interface Order {
  id: string;
  code: string;
  status: string;
  delivery_status: string;
  subtotal: string;
  delivery_fee: string;
  total: string;
  items: OrderItem[];
  created_at: string;
}

export interface CartItem {
  product_id: string;
  product_name: string;
  selling_price: string;
  quantity: number;
}

export async function createOrder(body: {
  items: { product_id: string; quantity: number }[];
  delivery_address?: string;
  delivery_area?: string;
  delivery_note?: string;
  payment_method?: string;
}): Promise<Order> {
  return apiFetch<Order>("/orders", { method: "POST", body: JSON.stringify(body) });
}

export async function listOrders(): Promise<Order[]> {
  return apiFetch<Order[]>("/orders");
}

export async function getOrder(id: string): Promise<Order> {
  return apiFetch<Order>(`/orders/${id}`);
}

export async function trackOrder(code: string, phone: string): Promise<{
  code: string;
  status: string;
  delivery_status: string;
  items: { product_name: string; quantity: number; unit_price: string; line_total: string }[];
  history: { field: string; to_value: string; note: string | null; created_at: string }[];
  created_at: string;
}> {
  const params = new URLSearchParams({ code, phone });
  return apiFetch(`/track?${params}`);
}

export async function submitPrescription(body: {
  description: string;
  file_b64?: string;
  file_type?: string;
}): Promise<{ id: string; review_status: string; created_at: string }> {
  return apiFetch("/prescriptions", { method: "POST", body: JSON.stringify(body) });
}
