import { apiFetch } from "@/lib/api";

export interface Product {
  id: string;
  name: string;
  generic_name: string;
  brand_name: string | null;
  dosage_form: string | null;
  strength: string | null;
  category: string | null;
  description: string | null;
  requires_prescription: boolean;
  selling_price: string | null;
  is_in_stock: boolean;
  /** Path to the staff-taken product photo, or null to fall back to the DrugIcon. */
  image_url: string | null;
}

export async function listCatalog(opts?: {
  q?: string;
  category?: string;
  in_stock_only?: boolean;
}): Promise<Product[]> {
  const params = new URLSearchParams();
  if (opts?.q) params.set("q", opts.q);
  if (opts?.category) params.set("category", opts.category);
  if (opts?.in_stock_only) params.set("in_stock_only", "true");
  const qs = params.toString();
  return apiFetch<Product[]>(`/catalog${qs ? `?${qs}` : ""}`);
}

export async function getProduct(id: string): Promise<Product> {
  return apiFetch<Product>(`/catalog/${id}`);
}

export async function listCategories(): Promise<string[]> {
  return apiFetch<string[]>("/catalog/categories");
}
