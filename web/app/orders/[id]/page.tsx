"use client";

import { useEffect, useState } from "react";
import { useParams, useSearchParams } from "next/navigation";
import Link from "next/link";
import { ArrowLeft, CheckCircle2 } from "lucide-react";
import { isNotFound } from "@/lib/api";
import { getOrder, type Order } from "@/lib/api/orders";
import { AppShell } from "@/components/app/app-shell";
import { LoadFailed, Spinner } from "@/components/app/ui";
import { PageTitle } from "@/components/app/page-title";

const STATUS_LABEL: Record<string, string> = {
  NEW: "Received",
  AWAITING_PAYMENT: "Awaiting payment",
  PAYMENT_SUBMITTED: "Payment submitted",
  PAYMENT_APPROVED: "Payment approved",
  PROCESSING: "Processing",
  DISPATCHED: "Dispatched",
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
  pack_ready: "Packed and ready for pickup",
  dispatch_assigned: "Dispatch assigned",
  picked_up: "Picked up",
  delivered: "Delivered",
  failed: "Issue under review",
};

const PROGRESS_STEPS = [
  { key: "NEW", label: "Order received" },
  { key: "AWAITING_PAYMENT", label: "Awaiting payment" },
  { key: "PAYMENT_APPROVED", label: "Payment confirmed" },
  { key: "PROCESSING", label: "Being prepared" },
  { key: "DISPATCHED", label: "On the way" },
  { key: "DELIVERED", label: "Delivered" },
];

const ORDER_SEQ = ["NEW", "AWAITING_PAYMENT", "PAYMENT_SUBMITTED", "PAYMENT_APPROVED", "PROCESSING", "DISPATCHED", "DELIVERED"];

function stepIndex(status: string) {
  return ORDER_SEQ.indexOf(status);
}

export default function OrderDetailPage() {
  const params = useParams();
  const searchParams = useSearchParams();
  const id = params?.id as string;
  const justPlaced = searchParams?.get("placed") === "1";

  const [order, setOrder] = useState<Order | null>(null);
  const [loading, setLoading] = useState(true);
  // Distinct from `order === null`, which renders "order not found". A failed
  // request is not evidence that the order does not exist.
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    if (!id) return;
    getOrder(id)
      .then(setOrder)
      .catch((e) => {
        if (isNotFound(e)) setOrder(null);
        else setFailed(true);
      })
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) return <AppShell><Spinner /></AppShell>;

  if (failed) {
    return (
      <AppShell back={{ fallbackHref: "/orders" }}>
        <div className="px-5 pt-6">
          <LoadFailed what="this order" onRetry={() => window.location.reload()} />
        </div>
      </AppShell>
    );
  }

  if (!order) {
    return (
      <AppShell>
        <div className="flex flex-col items-center gap-4 px-5 py-20 text-center">
          <p className="text-white/60">Order not found.</p>
          <Link href="/orders" className="text-sm text-emerald-400 hover:underline">← My Orders</Link>
        </div>
      </AppShell>
    );
  }

  const currentStep = stepIndex(order.status);

  return (
    <AppShell>
      <PageTitle title={`Order ${order.code}`} />
      <div className="space-y-6 pb-8">
        {/* Header */}
        <div className="flex items-center gap-3 px-5 pt-8">
          <Link
            href="/orders"
            className="flex h-9 w-9 items-center justify-center rounded-full border border-white/10 bg-white/5"
          >
            <ArrowLeft className="h-4 w-4 text-white/70" />
          </Link>
          <p className="text-[13px] text-[#b1bdb0]">My Orders</p>
        </div>

        {/* Placed banner */}
        {justPlaced && (
          <div className="mx-5 flex items-center gap-3 rounded-2xl border border-emerald-500/25 bg-emerald-500/10 px-4 py-4">
            <CheckCircle2 className="h-5 w-5 shrink-0 text-emerald-400" />
            <div>
              <p className="text-[13px] font-semibold text-emerald-400">Order placed!</p>
              <p className="text-[11px] text-white/50">We&apos;ll send you a Telegram message with next steps.</p>
            </div>
          </div>
        )}

        {/* Code + status */}
        <div className="px-5">
          <p className="text-[11px] text-[#b1bdb0] mb-1">{order.code}</p>
          <h1 className="font-syne text-[22px] font-bold text-white">
            {STATUS_LABEL[order.status] ?? order.status}
          </h1>
          {order.customer_facing_status && (
            <p className="text-[12px] text-emerald-300/80 mt-1">{order.customer_facing_status}</p>
          )}
          <p className="text-[12px] text-[#b1bdb0] mt-0.5">
            Placed {new Date(order.created_at).toLocaleDateString("en-NG", { day: "numeric", month: "long", year: "numeric" })}
          </p>
        </div>

        {order.fulfillment_status && (
          <div className="mx-5 rounded-2xl border border-white/8 bg-white/4 px-4 py-4">
            <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-[#b1bdb0] mb-2">Fulfilment</p>
            <p className="text-[14px] font-semibold text-white">
              {FULFILLMENT_LABEL[order.fulfillment_status] ?? order.fulfillment_status}
            </p>
          </div>
        )}

        {/* Progress */}
        <div className="mx-5 rounded-2xl border border-white/8 bg-white/4 px-4 py-4 space-y-3">
          <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-[#b1bdb0]">Progress</p>
          <div className="space-y-3">
            {PROGRESS_STEPS.map((step, i) => {
              const done = i <= currentStep;
              const current = ORDER_SEQ[currentStep] === step.key || (step.key === "PAYMENT_APPROVED" && order.status === "PAYMENT_SUBMITTED");
              return (
                <div key={step.key} className="flex items-center gap-3">
                  <span
                    className={`flex h-2 w-2 shrink-0 rounded-full ${
                      done ? "bg-emerald-500" : "bg-white/15"
                    }`}
                  />
                  <span className={`text-[13px] ${done ? "font-medium text-white" : "text-[#b1bdb0]"}`}>
                    {step.label}
                  </span>
                </div>
              );
            })}
          </div>
        </div>

        {/* Items */}
        <div className="mx-5 rounded-2xl border border-white/8 bg-white/4 divide-y divide-white/6">
          {order.items.map((item, i) => (
            <div key={i} className="flex justify-between px-4 py-3">
              <div>
                <p className="text-[13px] font-medium text-white">{item.product_name}</p>
                <p className="text-[11px] text-[#b1bdb0]">Qty {item.quantity} × ₦{Number(item.unit_price).toLocaleString()}</p>
              </div>
              <p className="text-[13px] font-semibold text-white">₦{Number(item.line_total).toLocaleString()}</p>
            </div>
          ))}
          <div className="px-4 py-3 space-y-1.5">
            <div className="flex justify-between text-[13px]">
              <span className="text-[#b1bdb0]">Delivery</span>
              <span className="text-white">₦{Number(order.delivery_fee).toLocaleString()}</span>
            </div>
            <div className="flex justify-between font-semibold">
              <span className="text-white">Total</span>
              <span className="text-[15px] text-emerald-400">₦{Number(order.total).toLocaleString()}</span>
            </div>
          </div>
        </div>

        {/* Track publicly */}
        <div className="px-5">
          <Link
            href={`/track?code=${order.code}`}
            className="block w-full rounded-xl border border-white/10 py-3 text-center text-[13px] text-white/50 transition hover:border-white/20 hover:text-white/70"
          >
            Share tracking link
          </Link>
        </div>
      </div>
    </AppShell>
  );
}
