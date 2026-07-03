"use client";

export interface CartItem {
  product_id: string;
  product_name: string;
  selling_price: number;
  quantity: number;
}

const KEY = "pw_cart";

export function getCart(): CartItem[] {
  if (typeof window === "undefined") return [];
  try {
    return JSON.parse(localStorage.getItem(KEY) ?? "[]");
  } catch {
    return [];
  }
}

export function saveCart(items: CartItem[]): void {
  localStorage.setItem(KEY, JSON.stringify(items));
}

export function addToCart(item: Omit<CartItem, "quantity"> & { quantity?: number }): CartItem[] {
  const cart = getCart();
  const existing = cart.find((c) => c.product_id === item.product_id);
  if (existing) {
    existing.quantity += item.quantity ?? 1;
  } else {
    cart.push({ ...item, quantity: item.quantity ?? 1 });
  }
  saveCart(cart);
  return cart;
}

export function removeFromCart(product_id: string): CartItem[] {
  const cart = getCart().filter((c) => c.product_id !== product_id);
  saveCart(cart);
  return cart;
}

export function updateQty(product_id: string, quantity: number): CartItem[] {
  const cart = getCart().map((c) =>
    c.product_id === product_id ? { ...c, quantity } : c
  );
  saveCart(cart);
  return cart;
}

export function clearCart(): void {
  localStorage.removeItem(KEY);
}

export function cartTotal(cart: CartItem[]): number {
  return cart.reduce((s, c) => s + c.selling_price * c.quantity, 0);
}
