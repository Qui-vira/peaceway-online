"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { getCart, cartTotal, clearCart, type CartItem } from "@/lib/cart";
import { createOrder } from "@/lib/api/orders";
import { isAuthError, type ApiError } from "@/lib/api";
import { getMe, listZones, type Zone } from "@/lib/api/customers";
import { AppShell } from "@/components/app/app-shell";
import { LoadFailed, Spinner } from "@/components/app/ui";
import { TactileButton } from "@/components/app/tactile-button";
import { siteConfig } from "@/lib/constants";
import { feeForArea } from "@/lib/delivery";
import { PageTitle } from "@/components/app/page-title";

const FOCUS =
  "focus-visible:outline-none focus-visible:ring-[3px] focus-visible:ring-[rgba(52,217,138,0.5)] focus-visible:ring-offset-2 focus-visible:ring-offset-[#0b0c09]";

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
  const [addressTouched, setAddressTouched] = useState(false);
  const [note, setNote] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  // Auth could not be confirmed - not the same as "signed out".
  const [authFailed, setAuthFailed] = useState(false);
  // Delivery is priced per area, so the area is part of the order, not a
  // profile nicety. Empty until the customer picks or their profile supplies it.
  const [area, setArea] = useState("");
  const [zones, setZones] = useState<Zone[]>([]);

  // Every order here is a delivery, so an address is required, not optional.
  // This used to submit `address || undefined`, which let an order through with
  // nowhere to send it: a refund, a phone call, and a customer who concludes the
  // pharmacy isn't real.
  const addressValid = address.trim().length > 0;
  const showAddressError = addressTouched && !addressValid;
  const areaValid = area.trim().length > 0;
  const canSubmit = addressValid && areaValid && !submitting;

  useEffect(() => {
    const c = getCart();
    if (c.length === 0) {
      router.replace("/shop");
      return;
    }
    setCart(c);
    void listZones().then(setZones);
    getMe()
      .then((me) => {
        // Preselect from the profile so a returning customer does not re-pick
        // their own area every order.
        if (me.delivery_area) setArea(me.delivery_area);
      })
      // Only bounce to sign-up when the backend actually says "not you". This
      // used to redirect on ANY failure, so a stutter mid-purchase threw a
      // signed-in customer out of checkout and onto a registration form - with
      // their cart intact but their identity apparently gone.
      //
      // `next` carries the destination through the sign-in round trip: without
      // it, signing in landed on /app and the customer had to find their way
      // back to a cart they had already filled.
      .catch((e) => {
        if (isAuthError(e)) router.replace("/start?next=/checkout");
        else setAuthFailed(true);
      })
      .finally(() => setLoading(false));
  }, [router]);

  async function handleSubmit() {
    if (!addressValid) {
      setAddressTouched(true);
      document.getElementById("delivery-address")?.focus();
      return;
    }
    if (!areaValid) {
      document.getElementById("delivery-area")?.focus();
      return;
    }
    setError("");
    setSubmitting(true);
    try {
      const order = await createOrder({
        items: cart.map((c) => ({ product_id: c.product_id, quantity: c.quantity })),
        delivery_address: address.trim(),
        // Send the area we priced. The server resolves the same zone table, so
        // letting it re-derive the area from the profile could quote the
        // customer one fee and charge another.
        delivery_area: area.trim(),
        delivery_note: note.trim() || undefined,
        payment_method: payMethod,
      });
      clearCart();
      router.push(`/orders/${order.id}?placed=1`);
    } catch (e: unknown) {
      const apiErr =
        typeof e === "object" && e !== null && "status" in e && "detail" in e ? (e as ApiError) : null;
      if (apiErr?.status === 401) {
        setSubmitting(false);
        router.push("/start?next=/checkout");
        return;
      }
      // "Something went wrong" said nothing about whether money had moved or an
      // order existed. Name the operation so the answer to "did it go through"
      // is on screen.
      setError(apiErr?.detail ?? "We couldn't place your order. Nothing was charged — please try again.");
      setSubmitting(false);
    }
  }

  if (loading)
    return (
      <AppShell back={{ fallbackHref: "/cart" }}>
        <PageTitle title="Checkout" />
        <Spinner />
      </AppShell>
    );

  if (authFailed)
    return (
      <AppShell back={{ title: "Checkout", fallbackHref: "/cart" }}>
        <div className="px-5 pt-6">
          <LoadFailed
            what="your account"
            detail="We couldn't reach the pharmacy to confirm your details. Your cart is safe - try again."
            onRetry={() => window.location.reload()}
          />
        </div>
      </AppShell>
    );

  const subtotal = cartTotal(cart);
  const deliveryFee = feeForArea(zones, area);
  const total = subtotal + deliveryFee;
  // No `md:text-sm` here: dropping to 14px on desktop is harmless, but the same
  // class ships to phones in other files and trips iOS auto-zoom. 16px is the
  // documented floor, and placeholders need the same 4.5:1 as body text.
  const inputCls = `w-full rounded-xl border border-white/10 bg-white/5 px-4 py-3 text-base text-white outline-none transition placeholder-[#b1bdb0] focus:border-emerald-500/50 ${FOCUS}`;

  return (
    <AppShell back={{ fallbackHref: "/cart" }}>
      <div className="mx-auto w-full max-w-5xl px-5 pb-10 pt-4 md:px-8">
        {/* The page went straight to <h2> with no <h1> above it - a heading
            level skip on the one screen where money changes hands. */}
        <h1 className="mb-4 font-syne text-[22px] font-bold text-white">Checkout</h1>
        <div className="grid gap-6 md:grid-cols-[minmax(0,1fr)_340px] md:items-start">
          {/* Left: delivery + payment */}
          <div className="space-y-5">
            {/* Delivery address */}
            <section className="space-y-3 rounded-2xl border border-white/8 bg-white/[0.04] px-4 py-4">
              <h2 className="text-[11px] font-semibold uppercase tracking-[0.14em] text-[#b1bdb0]">
                Delivery Address
              </h2>
              <textarea
                id="delivery-address"
                value={address}
                onChange={(e) => setAddress(e.target.value)}
                onBlur={() => setAddressTouched(true)}
                placeholder="Your street address, area, Lagos..."
                aria-label="Delivery address"
                aria-required="true"
                aria-invalid={showAddressError}
                aria-describedby={showAddressError ? "delivery-address-error" : undefined}
                rows={2}
                className={`resize-none ${inputCls} ${
                  showAddressError ? "border-red-500/50" : ""
                }`}
              />
              {showAddressError && (
                <p
                  id="delivery-address-error"
                  role="alert"
                  className="text-[13px] text-red-400"
                >
                  We need an address to deliver to. Street and area is enough.
                </p>
              )}
              {/* Delivery is priced per area and always has been - the zone
                  table drives it, and /profile has shown these prices all
                  along. Checkout quoted a flat ₦500 that matched no zone the
                  pharmacy serves, so the area has to be asked here, not
                  inferred. Preselected from the profile when we have one. */}
              <div className="space-y-1.5">
                <label
                  htmlFor="delivery-area"
                  className="block text-[13px] font-medium text-[#dcdddb]"
                >
                  Delivery area
                </label>
                <select
                  id="delivery-area"
                  value={area}
                  onChange={(e) => setArea(e.target.value)}
                  aria-required="true"
                  className={inputCls}
                >
                  <option value="">Select your area…</option>
                  {zones.map((z) => (
                    <option key={z.id} value={z.name}>
                      {z.name}
                      {z.fee !== null ? ` · ₦${z.fee.toLocaleString("en-NG")}` : ""}
                    </option>
                  ))}
                </select>
              </div>
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
              <h2 className="text-[11px] font-semibold uppercase tracking-[0.14em] text-[#b1bdb0]">
                Payment Method
              </h2>
              {/* Native radios, not buttons wearing role="radio". The hand-rolled
                  version announced "radio" to a screen reader but had no roving
                  tabIndex and no arrow-key handler, so the keys that a radio group
                  promises did nothing. The input is visually hidden; the tile is
                  the label, so it looks identical and behaves correctly. */}
              <fieldset className="space-y-3">
                <legend className="sr-only">Payment method</legend>
                {PAY_OPTIONS.map((opt) => {
                  const selected = payMethod === opt.value;
                  return (
                    <label
                      key={opt.value}
                      className={`pw-tile pw-tile-press flex w-full items-start gap-3 p-3.5 text-left has-[:focus-visible]:shadow-[0_4px_0_0_rgba(255,255,255,0.06),0_0_0_3px_rgba(52,217,138,0.5)] ${
                        selected ? "is-active" : ""
                      }`}
                    >
                      <input
                        type="radio"
                        name="payment-method"
                        value={opt.value}
                        checked={selected}
                        onChange={() => setPayMethod(opt.value)}
                        className="sr-only"
                      />
                      <span
                        aria-hidden
                        className={`mt-0.5 flex h-4 w-4 shrink-0 items-center justify-center rounded-full border ${
                          selected ? "border-emerald-500 bg-emerald-500" : "border-white/30"
                        }`}
                      >
                        {selected && <span className="h-2 w-2 rounded-full bg-black" />}
                      </span>
                      <span>
                        <span className="block text-[14px] font-semibold text-white">{opt.label}</span>
                        <span className="block text-[11px] text-[#b1bdb0]">{opt.sub}</span>
                      </span>
                    </label>
                  );
                })}
              </fieldset>
            </section>
          </div>

          {/* Right: summary + place order (sticky on desktop) */}
          <div className="space-y-4 md:sticky md:top-24">
            <section className="space-y-2.5 rounded-2xl border border-white/8 bg-white/[0.04] px-4 py-4">
              <h2 className="mb-1 text-[11px] font-semibold uppercase tracking-[0.14em] text-[#b1bdb0]">
                Order Summary
              </h2>
              {cart.map((item) => (
                <div key={item.product_id} className="flex justify-between gap-2 text-[13px]">
                  <span className="truncate text-[#b1bdb0]">
                    {item.product_name} × {item.quantity}
                  </span>
                  <span className="shrink-0 text-white">
                    ₦{(item.selling_price * item.quantity).toLocaleString()}
                  </span>
                </div>
              ))}
              <div className="mt-1 h-px bg-white/8" />
              <div className="flex justify-between text-[13px]">
                <span className="text-[#b1bdb0]">
                  Delivery{area ? ` · ${area}` : ""}
                </span>
                <span className="text-white">₦{deliveryFee.toLocaleString()}</span>
              </div>
              {!areaValid && (
                <p className="text-[11px] leading-relaxed text-[#b1bdb0]">
                  Estimated at our furthest area until you choose yours.
                </p>
              )}
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

            {/* Trust evidence, at the one moment it is actually needed. This was a
                terms-of-service line at 11px / white-25 (~2.2:1) - fine print,
                rendered invisible, at the exact point a customer commits money to
                medicine they cannot inspect. Every claim below is a fact already in
                the codebase; nothing here is decoration. */}
            <section
              aria-label="About this order"
              className="space-y-2 rounded-2xl border border-emerald-500/20 bg-emerald-500/[0.06] px-4 py-3.5"
            >
              <p className="text-[14px] font-semibold text-white">
                Dispensed by a licensed pharmacy
              </p>
              <p className="text-[13px] leading-relaxed text-[#b1bdb0]">
                {siteConfig.address}. We verify stock and check your order before
                confirming it — if anything is unavailable, a pharmacist contacts you
                first.
              </p>
              {payMethod === "BANK_TRANSFER" && (
                <p className="text-[13px] leading-relaxed text-[#b1bdb0]">
                  Nothing is charged now. We send account details after you place the
                  order.
                </p>
              )}
            </section>

            {/* The button used to be `disabled` with no other signal: full brand
                green, cursor:pointer, no aria-disabled, and the address error
                only appeared after the textarea had been focused and blurred.
                Tapping it did nothing and said nothing - on the one control in
                the product that takes money. It now says why it is waiting. */}
            <TactileButton
              disabled={!canSubmit}
              aria-disabled={!canSubmit}
              onClick={handleSubmit}
              className="w-full disabled:cursor-not-allowed"
            >
              {submitting ? "Placing order…" : `Place Order · ₦${total.toLocaleString()}`}
            </TactileButton>
            {!submitting && !canSubmit && (
              <p className="text-center text-[13px] text-[#b1bdb0]">
                {!addressValid
                  ? "Add a delivery address to place your order."
                  : "Choose your delivery area to place your order."}
              </p>
            )}
          </div>
        </div>
      </div>
    </AppShell>
  );
}
