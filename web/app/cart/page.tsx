"use client";

import { useEffect, useState } from "react";
import { Trash2, ShoppingCart, Minus, Plus } from "lucide-react";
import { getCart, updateQty, removeFromCart, cartTotal, type CartItem } from "@/lib/cart";
import { AppShell } from "@/components/app/app-shell";
import { EmptyState } from "@/components/app/ui";
import { DrugIcon } from "@/components/app/drug-icons";
import { TactileLink } from "@/components/app/tactile-button";

const FOCUS =
  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-400/70 focus-visible:ring-offset-2 focus-visible:ring-offset-[#0b0c09]";

const DELIVERY_FEE = 500;

function fmt(n: number) {
  return `₦${n.toLocaleString("en-NG")}`;
}

export default function CartPage() {
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
      <div className="mx-auto w-full max-w-5xl px-5 pb-10 pt-4 md:px-8">
        {cart.length === 0 ? (
          <EmptyState
            icon={<ShoppingCart className="h-6 w-6" />}
            title="Cart is empty"
            message="Browse our catalog and add medicines to your cart."
            ctaHref="/shop"
            ctaLabel="Browse Medicines"
          />
        ) : (
          <div className="grid gap-6 md:grid-cols-[minmax(0,1fr)_320px] md:items-start">
            {/* Items */}
            <ul className="space-y-3">
              {cart.map((item) => {
                const line = item.selling_price * item.quantity;
                return (
                  <li key={item.product_id} className="pw-tile p-3.5">
                    <div className="flex min-w-0 items-start gap-3">
                      <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl border border-emerald-500/20 bg-emerald-500/10">
                        <DrugIcon size={26} />
                      </span>
                      <div className="min-w-0 flex-1">
                        <p className="break-words text-[13px] font-semibold leading-snug text-white">
                          {item.product_name}
                        </p>
                        <p className="mt-0.5 text-[11px] text-white/40">{fmt(item.selling_price)} each</p>
                      </div>
                      <p className="shrink-0 text-right text-[13px] font-bold text-emerald-400">
                        {fmt(line)}
                      </p>
                    </div>

                    <div className="mt-3 flex items-center justify-between border-t border-white/6 pt-3">
                      <button
                        onClick={() => handleRemove(item.product_id)}
                        className={`inline-flex min-h-[44px] items-center gap-1.5 rounded-lg border border-red-500/20 px-3 text-[12px] font-semibold text-red-400/80 transition hover:border-red-500/40 hover:text-red-400 ${FOCUS}`}
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                        Remove
                      </button>
                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => handleQty(item.product_id, item.quantity - 1)}
                          disabled={item.quantity <= 1}
                          className={`flex h-11 w-11 items-center justify-center rounded-lg border border-white/15 text-white/70 transition-all duration-150 hover:border-white/30 active:scale-90 disabled:opacity-40 disabled:active:scale-100 motion-reduce:transform-none ${FOCUS}`}
                          aria-label={`Reduce ${item.product_name} quantity`}
                        >
                          <Minus className="h-4 w-4" />
                        </button>
                        <span className="w-7 text-center text-[14px] font-semibold tabular-nums text-white">
                          {item.quantity}
                        </span>
                        <button
                          onClick={() => handleQty(item.product_id, item.quantity + 1)}
                          className={`flex h-11 w-11 items-center justify-center rounded-lg bg-emerald-500 text-black transition-all duration-150 hover:bg-emerald-400 active:scale-90 motion-reduce:transform-none ${FOCUS}`}
                          aria-label={`Increase ${item.product_name} quantity`}
                        >
                          <Plus className="h-4 w-4" />
                        </button>
                      </div>
                    </div>
                  </li>
                );
              })}
            </ul>

            {/* Summary + CTA (sticky on desktop) */}
            <div className="space-y-4 md:sticky md:top-24">
              <div className="pw-tile space-y-3 px-4 py-4">
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

              <TactileLink href="/checkout" className="w-full">
                Proceed to Checkout →
              </TactileLink>
            </div>
          </div>
        )}
      </div>
    </AppShell>
  );
}
