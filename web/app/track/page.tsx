"use client";

import { Suspense, useState } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { Search, CheckCircle2 } from "lucide-react";
import { trackOrder } from "@/lib/api/orders";

type TrackResult = {
  code: string;
  status: string;
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

function TrackPageContent() {
  const searchParams = useSearchParams();
  const [code, setCode] = useState(searchParams?.get("code") ?? "");
  const [phone, setPhone] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<TrackResult | null>(null);
  const [error, setError] = useState("");

  async function handleTrack() {
    if (!code.trim() || !phone.trim()) return;
    setError("");
    setLoading(true);
    try {
      const data = await trackOrder(code.trim(), phone.trim());
      setResult(data);
    } catch {
      setError("Order not found. Check the code and phone number and try again.");
      setResult(null);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-[#0b0c09] px-5 py-12">
      {/* Brand */}
      <div className="mb-10 text-center">
        <Link href="/" className="inline-block">
          <span className="font-syne text-lg font-bold text-white">Peaceway Online</span>
        </Link>
        <p className="mt-1 text-[12px] text-white/30">Igando, Lagos</p>
      </div>

      <div className="mx-auto max-w-sm">
        <div className="mb-6 text-center">
          <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-full border border-white/10 bg-white/5">
            <Search className="h-6 w-6 text-white/50" />
          </div>
          <h1 className="font-syne text-[22px] font-bold text-white">Track Your Order</h1>
          <p className="mt-1.5 text-[13px] text-white/40">No account needed</p>
        </div>

        <div className="rounded-2xl border border-white/8 bg-white/4 p-5 space-y-4">
          <div className="space-y-1.5">
            <label className="block text-[11px] font-medium text-white/50">Order code</label>
            <input
              value={code}
              onChange={(e) => setCode(e.target.value)}
              placeholder="e.g. PW-2025-0042"
              className="w-full rounded-xl border border-white/10 bg-white/5 px-4 py-3 text-sm text-white placeholder-white/30 outline-none focus:border-emerald-500/50"
            />
          </div>
          <div className="space-y-1.5">
            <label className="block text-[11px] font-medium text-white/50">Phone number</label>
            <input
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              placeholder="08012345678"
              type="tel"
              className="w-full rounded-xl border border-white/10 bg-white/5 px-4 py-3 text-sm text-white placeholder-white/30 outline-none focus:border-emerald-500/50"
            />
          </div>

          {error && (
            <p className="text-[13px] text-red-400">{error}</p>
          )}

          <button
            onClick={handleTrack}
            disabled={loading || !code.trim() || !phone.trim()}
            className="w-full rounded-xl bg-emerald-500 py-3.5 text-sm font-semibold text-black transition hover:bg-emerald-400 disabled:opacity-50"
          >
            {loading ? "Searching…" : "Track Order"}
          </button>
        </div>

        {result && (
          <div className="mt-6 space-y-4">
            {/* Status */}
            <div className="rounded-2xl border border-emerald-500/25 bg-emerald-500/8 px-4 py-4">
              <p className="text-[11px] font-semibold uppercase tracking-wide text-emerald-400 mb-1">
                {result.code}
              </p>
              <p className="text-[18px] font-bold text-white">
                {STATUS_LABEL[result.status] ?? result.status}
              </p>
              <p className="text-[12px] text-white/40 mt-0.5">
                Placed {new Date(result.created_at).toLocaleDateString("en-NG", { day: "numeric", month: "long" })}
              </p>
            </div>

            {/* Items */}
            <div className="rounded-2xl border border-white/8 bg-white/4 px-4 py-4 space-y-2">
              <p className="text-[10px] font-semibold uppercase tracking-[0.14em] text-white/40 mb-3">Items</p>
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
                <p className="text-[10px] font-semibold uppercase tracking-[0.14em] text-white/40">Timeline</p>
                {result.history.map((h, i) => (
                  <div key={i} className="flex items-start gap-3">
                    <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-emerald-400" />
                    <div>
                      <p className="text-[13px] font-medium text-white">
                        {STATUS_LABEL[h.to_value] ?? h.to_value}
                      </p>
                      {h.note && <p className="text-[11px] text-white/50">{h.note}</p>}
                      <p className="text-[11px] text-white/30">
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

            <Link
              href="/start"
              className="block w-full rounded-xl border border-emerald-500/30 py-3 text-center text-sm font-semibold text-emerald-400 transition hover:bg-emerald-500/10"
            >
              Create account for real-time alerts
            </Link>
          </div>
        )}

        <p className="mt-8 text-center text-[12px] text-white/25">
          <Link href="/" className="hover:text-white/50">← Back to home</Link>
        </p>
      </div>
    </div>
  );
}

export default function TrackPage() {
  return (
    <Suspense fallback={<div className="min-h-screen bg-[#0b0c09]" />}>
      <TrackPageContent />
    </Suspense>
  );
}
