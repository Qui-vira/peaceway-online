"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import { getCart, cartTotal, clearCart, type CartItem } from "@/lib/cart";
import { createOrder } from "@/lib/api/orders";
import { AppShell } from "@/components/app/app-shell";
import { Spinner } from "@/components/app/ui";

const DELIVERY_FEE = 500;

type PayMethod = "BANK_TRANSFER" | "FLUTTERWAVE";

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
    setLoading(false);
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
      const msg = e instanceof Error ? e.message : "Something went wrong.";
      setError(msg);
      setSubmitting(false);
    }
  }

  if (loading) return <AppShell><Spinner /></AppShell>;

  const subtotal = cartTotal(cart);
  const total = subtotal + DELIVERY_FEE;

  return (
    <AppShell>
      <div className="space-y-5 px-5 pt-10 pb-8">
        {/* Header */}
        <div className="flex items-center gap-3">
          <Link
            href="/cart"
            className="flex h-9 w-9 items-center justify-center rounded-full border border-white/10 bg-white/5"
          >
            <ArrowLeft className="h-4 w-4 text-white/70" />
          </Link>
          <h1 className="font-syne text-[20px] font-bold text-white">Checkout</h1>
        </div>

        {/* Order summary */}
        <div className="rounded-2xl border border-white/8 bg-white/4 px-4 py-4 space-y-2.5">
          <p className="text-[10px] font-semibold uppercase tracking-[0.14em] text-white/40 mb-3">
            Order Summary
          </p>
          {cart.map((item) => (
            <div key={item.product_id} className="flex justify-between text-[13px]">
              <span className="text-white/60 truncate mr-2">{item.product_name} × {item.quantity}</span>
              <span className="shrink-0 text-white">₦{(item.selling_price * item.quantity).toLocaleString()}</span>
            </div>
          ))}
          <div className="h-px bg-white/8 mt-1" />
          <div className="flex justify-between text-[13px]">
            <span className="text-white/50">Delivery</span>
            <span className="text-white">₦{DELIVERY_FEE.toLocaleString()}</span>
          </div>
          <div className="flex justify-between font-semibold">
            <span className="text-white">Total</span>
            <span className="text-emerald-400 text-[15px]">₦{total.toLocaleString()}</span>
          </div>
        </div>

        {/* Delivery address */}
        <div className="rounded-2xl border border-white/8 bg-white/4 px-4 py-4 space-y-3">
          <p className="text-[10px] font-semibold uppercase tracking-[0.14em] text-white/40">
            Delivery Address
          </p>
          <textarea
            value={address}
            onChange={(e) => setAddress(e.target.value)}
            placeholder="Your street address, area, Lagos..."
            rows={2}
            className="w-full resize-none rounded-xl border border-white/10 bg-white/5 px-4 py-3 text-sm text-white placeholder-white/30 outline-none focus:border-emerald-500/50"
          />
          <input
            value={note}
            onChange={(e) => setNote(e.target.value)}
            placeholder="Delivery note (optional)"
            className="w-full rounded-xl border border-white/10 bg-white/5 px-4 py-3 text-sm text-white placeholder-white/30 outline-none focus:border-emerald-500/50"
          />
        </div>

        {/* Payment method */}
        <div className="rounded-2xl border border-white/8 bg-white/4 px-4 py-4 space-y-3">
          <p className="text-[10px] font-semibold uppercase tracking-[0.14em] text-white/40">
            Payment Method
          </p>
          {(
            [
              { value: "BANK_TRANSFER", label: "Bank transfer / USSD", sub: "We'll send account details after placing" },
              { value: "FLUTTERWAVE", label: "Pay online (card / transfer)", sub: "Powered by Flutterwave" },
            ] as { value: PayMethod; label: string; sub: string }[]
          ).map((opt) => (
            <button
              key={opt.value}
              onClick={() => setPayMethod(opt.value)}
              className={`flex w-full items-start gap-3 rounded-xl border p-3.5 text-left transition ${
                payMethod === opt.value
                  ? "border-emerald-500/40 bg-emerald-500/8"
                  : "border-white/10 bg-transparent hover:border-white/20"
              }`}
            >
              <span
                className={`mt-0.5 flex h-4 w-4 shrink-0 items-center justify-center rounded-full border ${
                  payMethod === opt.value ? "border-emerald-500 bg-emerald-500" : "border-white/30"
                }`}
              >
                {payMethod === opt.value && (
                  <span className="h-2 w-2 rounded-full bg-black" />
                )}
              </span>
              <div>
                <p className="text-[13px] font-semibold text-white">{opt.label}</p>
                <p className="text-[11px] text-white/40">{opt.sub}</p>
              </div>
            </button>
          ))}
        </div>

        {error && (
          <p className="rounded-xl border border-red-500/25 bg-red-500/8 px-4 py-3 text-[13px] text-red-400">
            {error}
          </p>
        )}

        <button
          disabled={submitting}
          onClick={handleSubmit}
          className="w-full rounded-xl bg-emerald-500 py-3.5 text-sm font-semibold text-black transition hover:bg-emerald-400 disabled:opacity-60"
        >
          {submitting ? "Placing order…" : `Place Order · ₦${total.toLocaleString()}`}
        </button>
        <p className="text-center text-[11px] text-white/25">
          By placing this order you agree to our terms of service.
        </p>
      </div>
    </AppShell>
  );
}
