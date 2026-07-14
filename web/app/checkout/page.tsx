"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { getCart, cartTotal, clearCart, type CartItem } from "@/lib/cart";
import { createOrder } from "@/lib/api/orders";
import type { ApiError } from "@/lib/api";
import { getMe } from "@/lib/api/customers";
import { AppShell } from "@/components/app/app-shell";
import { Spinner } from "@/components/app/ui";

const FOCUS =
  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-400/70 focus-visible:ring-offset-2 focus-visible:ring-offset-[#0b0c09]";

const DELIVERY_FEE = 500;

type PayMethod = "BANK_TRANSFER" | "FLUTTERWAVE";

const PAY_OPTIONS: { value: PayMethod; label: string; sub: string }[] = [
  { value: "BANK_TRANSFER", label: "Bank transfer / USSD", sub: "We'll send account details after placing" },
  { value: "FLUTTERWAVE", label: "Pay online (card / transfer)", sub: "Powered by Flutterwave" },
];

export default function CheckoutPage() {
  const router = useRouter();
  const [cart, setCart] = useState<CartItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [payMethod, setPayMethod] = useState<PayMethod>("BANK_TRANSFER");
  const [address, setAddress] = useState("");
  const [note, setNote] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    const c = getCart();
    if (c.length === 0) {
      router.replace("/shop");
      return;
    }
    setCart(c);
    getMe()
      .catch(() => router.replace("/start"))
      .finally(() => setLoading(false));
  }, [router]);

  async function handleSubmit() {
    setError("");
    setSubmitting(true);
    try {
      const order = await createOrder({
        items: cart.map((c) => ({ product_id: c.product_id, quantity: c.quantity })),
        delivery_address: address || undefined,
        delivery_note: note || undefined,
        payment_method: payMethod,
      });
      clearCart();
      router.push(`/orders/${order.id}?placed=1`);
    } catch (e: unknown) {
      const apiErr =
        typeof e === "object" && e !== null && "status" in e && "detail" in e ? (e as ApiError) : null;
      if (apiErr?.status === 401) {
        setSubmitting(false);
        router.push("/start");
        return;
      }
      setError(apiErr?.detail ?? "Something went wrong.");
      setSubmitting(false);
    }
  }

  if (loading)
    return (
      <AppShell back={{ fallbackHref: "/cart" }}>
        <Spinner />
      </AppShell>
    );

  const subtotal = cartTotal(cart);
  const total = subtotal + DELIVERY_FEE;
  const inputCls = `w-full rounded-xl border border-white/10 bg-white/5 px-4 py-3 text-base text-white outline-none transition placeholder-white/30 focus:border-emerald-500/50 md:text-sm ${FOCUS}`;

  return (
    <AppShell back={{ title: "Checkout", fallbackHref: "/cart" }}>
      <div className="mx-auto w-full max-w-5xl px-5 pb-10 pt-4 md:px-8">
        <div className="grid gap-6 md:grid-cols-[minmax(0,1fr)_340px] md:items-start">
          {/* Left: delivery + payment */}
          <div className="space-y-5">
            {/* Delivery address */}
            <section className="space-y-3 rounded-2xl border border-white/8 bg-white/[0.04] px-4 py-4">
              <h2 className="text-[10px] font-semibold uppercase tracking-[0.14em] text-white/40">
                Delivery Address
              </h2>
              <textarea
                value={address}
                onChange={(e) => setAddress(e.target.value)}
                placeholder="Your street address, area, Lagos..."
                aria-label="Delivery address"
                rows={2}
                className={`resize-none ${inputCls}`}
              />
              <input
                value={note}
                onChange={(e) => setNote(e.target.value)}
                placeholder="Delivery note (optional)"
                aria-label="Delivery note"
                className={inputCls}
              />
            </section>

            {/* Payment method */}
            <section className="space-y-3 rounded-2xl border border-white/8 bg-white/[0.04] px-4 py-4">
              <h2 className="text-[10px] font-semibold uppercase tracking-[0.14em] text-white/40">
                Payment Method
              </h2>
              <div role="radiogroup" aria-label="Payment method" className="space-y-3">
                {PAY_OPTIONS.map((opt) => {
                  const selected = payMethod === opt.value;
                  return (
                    <button
                      key={opt.value}
                      role="radio"
                      aria-checked={selected}
                      onClick={() => setPayMethod(opt.value)}
                      className={`flex w-full items-start gap-3 rounded-xl border p-3.5 text-left transition-all duration-200 active:scale-[0.99] motion-reduce:transform-none ${
                        selected
                          ? "border-emerald-500/40 bg-emerald-500/[0.08] shadow-[0_0_24px_-8px_rgba(26,163,90,0.5)]"
                          : "border-white/10 hover:border-white/20"
                      } ${FOCUS}`}
                    >
                      <span
                        className={`mt-0.5 flex h-4 w-4 shrink-0 items-center justify-center rounded-full border ${
                          selected ? "border-emerald-500 bg-emerald-500" : "border-white/30"
                        }`}
                      >
                        {selected && <span className="h-2 w-2 rounded-full bg-black" />}
                      </span>
                      <span>
                        <span className="block text-[13px] font-semibold text-white">{opt.label}</span>
                        <span className="block text-[11px] text-white/40">{opt.sub}</span>
                      </span>
                    </button>
                  );
                })}
              </div>
            </section>
          </div>

          {/* Right: summary + place order (sticky on desktop) */}
          <div className="space-y-4 md:sticky md:top-24">
            <section className="space-y-2.5 rounded-2xl border border-white/8 bg-white/[0.04] px-4 py-4">
              <h2 className="mb-1 text-[10px] font-semibold uppercase tracking-[0.14em] text-white/40">
                Order Summary
              </h2>
              {cart.map((item) => (
                <div key={item.product_id} className="flex justify-between gap-2 text-[13px]">
                  <span className="truncate text-white/60">
                    {item.product_name} × {item.quantity}
                  </span>
                  <span className="shrink-0 text-white">
                    ₦{(item.selling_price * item.quantity).toLocaleString()}
                  </span>
                </div>
              ))}
              <div className="mt-1 h-px bg-white/8" />
              <div className="flex justify-between text-[13px]">
                <span className="text-white/50">Delivery</span>
                <span className="text-white">₦{DELIVERY_FEE.toLocaleString()}</span>
              </div>
              <div className="flex justify-between font-semibold">
                <span className="text-white">Total</span>
                <span className="text-[15px] text-emerald-400">₦{total.toLocaleString()}</span>
              </div>
            </section>

            {error && (
              <p
                role="alert"
                className="rounded-xl border border-red-500/25 bg-red-500/[0.08] px-4 py-3 text-[13px] text-red-400"
              >
                {error}
              </p>
            )}

            <button disabled={submitting} onClick={handleSubmit} className="pw-btn w-full">
              {submitting ? "Placing order…" : `Place Order · ₦${total.toLocaleString()}`}
            </button>
            <p className="text-center text-[11px] text-white/25">
              By placing this order you agree to our terms of service.
            </p>
          </div>
        </div>
      </div>
    </AppShell>
  );
}
