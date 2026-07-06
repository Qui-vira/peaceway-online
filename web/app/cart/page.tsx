"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Trash2, ShoppingCart } from "lucide-react";
import { getCart, updateQty, removeFromCart, cartTotal, type CartItem } from "@/lib/cart";
import { AppShell } from "@/components/app/app-shell";
import { EmptyState } from "@/components/app/ui";
import { DrugIcon } from "@/components/app/drug-icons";

function fmt(n: number) {
  return `₦${n.toLocaleString("en-NG")}`;
}

const DELIVERY_FEE = 500;

export default function CartPage() {
  const router = useRouter();
  const [cart, setCart] = useState<CartItem[]>([]);

  useEffect(() => {
    setCart(getCart());
  }, []);

  function handleQty(id: string, qty: number) {
    if (qty < 1) return;
    setCart(updateQty(id, qty));
  }

  function handleRemove(id: string) {
    setCart(removeFromCart(id));
  }

  const subtotal = cartTotal(cart);
  const total = subtotal + DELIVERY_FEE;

  return (
    <AppShell back={{ title: "Your Cart", fallbackHref: "/shop" }}>
      <div className="space-y-6 px-5 pt-6 pb-8">
        <h1 className="font-syne text-[22px] font-bold text-white">Your Cart</h1>

        {cart.length === 0 && (
          <EmptyState
            icon={<ShoppingCart className="h-6 w-6" />}
            title="Cart is empty"
            message="Browse our catalog and add medicines to your cart."
            ctaHref="/shop"
            ctaLabel="Browse Medicines"
          />
        )}

        {cart.length > 0 && (
          <>
            <div className="space-y-3">
              {cart.map((item) => (
                <div
                  key={item.product_id}
                  className="rounded-2xl border border-white/8 bg-white/4 p-3.5"
                >
                  <div className="flex min-w-0 items-start gap-3">
                    <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl border border-emerald-500/20 bg-emerald-500/10">
                      <DrugIcon size={26} />
                    </span>
                    <div className="min-w-0 flex-1">
                      <p className="break-words text-[13px] font-semibold leading-snug text-white">
                        {item.product_name}
                      </p>
                      <p className="mt-0.5 text-[11px] text-white/40">
                        Unit price
                      </p>
                    </div>
                    <p className="shrink-0 text-right text-[12px] font-bold text-emerald-400">
                      {fmt(item.selling_price)}
                    </p>
                  </div>

                  <div className="mt-3 flex items-center justify-between border-t border-white/6 pt-3">
                    <button
                      onClick={() => handleRemove(item.product_id)}
                      className="inline-flex min-h-9 items-center gap-1.5 rounded-lg border border-red-500/20 px-3 text-[11px] font-semibold text-red-400/70 hover:text-red-400"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                      Remove
                    </button>
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => handleQty(item.product_id, item.quantity - 1)}
                        className="flex h-9 w-9 items-center justify-center rounded-lg border border-white/15 text-white/70 hover:border-white/30"
                        aria-label={`Reduce ${item.product_name} quantity`}
                      >
                        −
                      </button>
                      <span className="w-7 text-center text-[13px] font-semibold text-white">
                        {item.quantity}
                      </span>
                      <button
                        onClick={() => handleQty(item.product_id, item.quantity + 1)}
                        className="flex h-9 w-9 items-center justify-center rounded-lg bg-emerald-500 text-[13px] font-bold text-black"
                        aria-label={`Increase ${item.product_name} quantity`}
                      >
                        +
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>

            {/* Order summary */}
            <div className="rounded-2xl border border-white/8 bg-white/4 px-4 py-4 space-y-3">
              <div className="flex justify-between text-[13px]">
                <span className="text-white/50">Subtotal</span>
                <span className="text-white">{fmt(subtotal)}</span>
              </div>
              <div className="flex justify-between text-[13px]">
                <span className="text-white/50">Delivery</span>
                <span className="text-white">{fmt(DELIVERY_FEE)}</span>
              </div>
              <div className="h-px bg-white/8" />
              <div className="flex justify-between">
                <span className="text-[15px] font-semibold text-white">Total</span>
                <span className="text-[17px] font-bold text-emerald-400">{fmt(total)}</span>
              </div>
            </div>

            <Link
              href="/checkout"
              className="block w-full rounded-xl bg-emerald-500 py-3.5 text-center text-sm font-semibold text-black transition hover:bg-emerald-400"
            >
              Proceed to Checkout →
            </Link>
          </>
        )}
      </div>
    </AppShell>
  );
}
