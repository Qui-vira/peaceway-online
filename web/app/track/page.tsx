"use client";

import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { Search, CheckCircle2 } from "lucide-react";
import { trackOrder } from "@/lib/api/orders";
import { getMe } from "@/lib/api/customers";
import { TactileButton } from "@/components/app/tactile-button";
import { usePageTitle } from "@/components/app/page-title";

type TrackResult = {
  code: string;
  status: string;
  fulfillment_status?: string | null;
  customer_facing_status?: string | null;
  pickup_code?: string | null;
  delivery_status: string;
  items: { product_name: string; quantity: number; unit_price: string; line_total: string }[];
  history: { field: string; to_value: string; note: string | null; created_at: string }[];
  created_at: string;
};

const STATUS_LABEL: Record<string, string> = {
  NEW: "Received",
  AWAITING_PAYMENT: "Awaiting payment",
  PAYMENT_SUBMITTED: "Payment submitted",
  PAYMENT_APPROVED: "Payment confirmed",
  PROCESSING: "Being prepared",
  DISPATCHED: "On the way",
  DELIVERED: "Delivered",
  CANCELLED: "Cancelled",
  REJECTED: "Rejected",
};

const FULFILLMENT_LABEL: Record<string, string> = {
  in_stock: "In stock now",
  source_from_network: "Sourcing from approved network",
  sourcing_requested: "Approved partner request sent",
  partner_confirmed: "Partner confirmed",
  partner_rejected: "Partner unavailable",
  pack_ready: "Pack ready for pickup",
  dispatch_assigned: "Dispatch assigned",
  picked_up: "Picked up",
  delivered: "Delivered",
  failed: "Issue under review",
};

function TrackPageContent() {
  const searchParams = useSearchParams();
  const [code, setCode] = useState(searchParams?.get("code") ?? "");
  const [phone, setPhone] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<TrackResult | null>(null);
  const [error, setError] = useState("");
  // This page is reachable two ways: signed out with a code (the point of it),
  // and from Profile / an order detail by someone already signed in. It used to
  // treat everyone as a stranger - no nav, exits only to the marketing site,
  // and a "Create account" CTA shown to people who had one.
  const [signedIn, setSignedIn] = useState(false);

  useEffect(() => {
    getMe()
      .then(() => setSignedIn(true))
      .catch(() => setSignedIn(false));
  }, []);

  async function handleTrack() {
    if (!code.trim() || !phone.trim()) return;
    setError("");
    setLoading(true);
    try {
      const data = await trackOrder(code.trim(), phone.trim());
      setResult(data);
    } catch (err) {
      const status = (err as { status?: number })?.status;
      if (status === 404) {
        setError("Order not found. Check the code and phone number and try again.");
      } else {
        setError("We couldn't reach the pharmacy to look up your order. Please try again in a moment.");
      }
      setResult(null);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-[#0b0c09] px-5 py-12">
      {/* Brand */}
      <div className="mb-10 text-center">
        <Link href={signedIn ? "/app" : "/"} className="inline-block">
          <span className="font-syne text-lg font-bold text-white">Peaceway Online</span>
        </Link>
        <p className="mt-1 text-[12px] text-[#b1bdb0]">Igando, Lagos</p>
      </div>

      <div className="mx-auto max-w-sm">
        <div className="mb-6 text-center">
          <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-full border border-white/10 bg-white/5">
            <Search className="h-6 w-6 text-white/50" />
          </div>
          <h1 className="font-syne text-[22px] font-bold text-white">Track Your Order</h1>
          <p className="mt-1.5 text-[13px] text-[#b1bdb0]">No account needed</p>
        </div>

        <div className="rounded-2xl border border-white/8 bg-white/4 p-5 space-y-4">
          <div className="space-y-1.5">
            <label className="block text-[11px] font-medium text-white/50">Order code</label>
            <input
              value={code}
              onChange={(e) => setCode(e.target.value)}
              placeholder="e.g. PW-2025-0042"
              className="w-full rounded-xl border border-white/10 bg-white/5 px-4 py-3 text-base text-white placeholder-[#b1bdb0] outline-none focus:border-emerald-500/50"
            />
          </div>
          <div className="space-y-1.5">
            <label className="block text-[11px] font-medium text-white/50">Phone number</label>
            <input
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              placeholder="08012345678"
              type="tel"
              className="w-full rounded-xl border border-white/10 bg-white/5 px-4 py-3 text-base text-white placeholder-[#b1bdb0] outline-none focus:border-emerald-500/50"
            />
          </div>

          {error && (
            <p className="text-[13px] text-red-400">{error}</p>
          )}

          <TactileButton
            onClick={handleTrack}
            disabled={loading || !code.trim() || !phone.trim()}
            className="w-full disabled:opacity-50"
          >
            {loading ? "Searching…" : "Track Order"}
          </TactileButton>
        </div>

        {result && (
          <div className="mt-6 space-y-4">
            {/* Status */}
            <div className="rounded-2xl border border-emerald-500/25 bg-emerald-500/8 px-4 py-4">
              <p className="text-[11px] font-semibold uppercase tracking-wide text-emerald-400 mb-1">
                {result.code}
              </p>
              <p className="text-lg font-bold text-white">
                {STATUS_LABEL[result.status] ?? result.status}
              </p>
              {result.customer_facing_status && (
                <p className="mt-1 text-[12px] text-emerald-200/80">
                  {result.customer_facing_status}
                </p>
              )}
              <p className="text-[12px] text-[#b1bdb0] mt-0.5">
                Placed {new Date(result.created_at).toLocaleDateString("en-NG", { day: "numeric", month: "long" })}
              </p>
            </div>

            {result.fulfillment_status && (
              <div className="rounded-2xl border border-white/8 bg-white/4 px-4 py-4">
                <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-[#b1bdb0] mb-2">Fulfilment</p>
                <p className="text-[14px] font-semibold text-white">
                  {FULFILLMENT_LABEL[result.fulfillment_status] ?? result.fulfillment_status}
                </p>
                {result.pickup_code && (
                  <p className="mt-1 text-[12px] text-white/50">Pickup code: <span className="font-semibold text-white">{result.pickup_code}</span></p>
                )}
              </div>
            )}

            {/* Items */}
            <div className="rounded-2xl border border-white/8 bg-white/4 px-4 py-4 space-y-2">
              <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-[#b1bdb0] mb-3">Items</p>
              {result.items.map((item, i) => (
                <div key={i} className="flex justify-between text-[13px]">
                  <span className="text-white/70">{item.product_name} × {item.quantity}</span>
                  <span className="text-white">₦{Number(item.line_total).toLocaleString()}</span>
                </div>
              ))}
            </div>

            {/* Timeline */}
            {result.history.length > 0 && (
              <div className="rounded-2xl border border-white/8 bg-white/4 px-4 py-4 space-y-3">
                <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-[#b1bdb0]">Timeline</p>
                {result.history.map((h, i) => (
                  <div key={i} className="flex items-start gap-3">
                    <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-emerald-400" />
                    <div>
                      <p className="text-[13px] font-medium text-white">
                        {STATUS_LABEL[h.to_value] ?? h.to_value}
                      </p>
                      {h.note && <p className="text-[11px] text-white/50">{h.note}</p>}
                      <p className="text-[11px] text-[#b1bdb0]">
                        {new Date(h.created_at).toLocaleString("en-NG", {
                          day: "numeric",
                          month: "short",
                          hour: "2-digit",
                          minute: "2-digit",
                        })}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            )}

            {/* Offering "create an account" to someone who is signed in is the
                app forgetting who it is talking to. Signed in, the useful
                action is the order list they already have. */}
            <Link
              href={signedIn ? "/orders" : "/start"}
              className="block w-full rounded-xl border border-emerald-500/30 py-3 text-center text-sm font-semibold text-emerald-400 transition hover:bg-emerald-500/10"
            >
              {signedIn ? "See all my orders" : "Create account for real-time alerts"}
            </Link>
          </div>
        )}

        {/* Was `/` twice - the marketing homepage - so a signed-in customer who
            tapped "Track an Order" in their profile was tipped out of the app
            with no way back in but the landing page. hover made it dimmer, too:
            #b1bdb0 (~10:1) fading to white/50 (~5.3:1) on hover is backwards. */}
        <p className="mt-8 text-center text-[12px] text-[#b1bdb0]">
          <Link
            href={signedIn ? "/app" : "/"}
            className="-my-2 inline-flex min-h-[44px] items-center rounded px-2 py-2 transition hover:text-white"
          >
            ← {signedIn ? "Back to Peaceway" : "Back to home"}
          </Link>
        </p>
      </div>
    </div>
  );
}

export default function TrackPage() {
  usePageTitle("Track Your Order");
  return (
    <Suspense fallback={<div className="min-h-screen bg-[#0b0c09]" />}>
      <TrackPageContent />
    </Suspense>
  );
}
