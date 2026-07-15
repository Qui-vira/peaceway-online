"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Package } from "lucide-react";
import { listOrders, type Order } from "@/lib/api/orders";
import { AppShell } from "@/components/app/app-shell";
import { EmptyState, GuestWall, SectionLabel, SkeletonCard } from "@/components/app/ui";

type State =
  | { kind: "loading" }
  | { kind: "guest" }
  | { kind: "ready"; orders: Order[] };

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
  source_from_network: "Sourcing from network",
  sourcing_requested: "Sourcing requested",
  partner_confirmed: "Partner confirmed",
  partner_rejected: "Partner unavailable",
  pack_ready: "Pack ready",
  dispatch_assigned: "Dispatch assigned",
  picked_up: "Picked up",
  delivered: "Delivered",
  failed: "Issue under review",
};

const STATUS_COLOR: Record<string, string> = {
  DELIVERED: "bg-emerald-500/15 text-emerald-400 border-emerald-500/25",
  PAYMENT_APPROVED: "bg-emerald-500/15 text-emerald-400 border-emerald-500/25",
  PROCESSING: "bg-emerald-500/15 text-emerald-400 border-emerald-500/25",
  DISPATCHED: "bg-emerald-500/15 text-emerald-400 border-emerald-500/25",
  AWAITING_PAYMENT: "bg-amber-500/15 text-amber-400 border-amber-500/25",
  PAYMENT_SUBMITTED: "bg-amber-500/15 text-amber-400 border-amber-500/25",
  CANCELLED: "bg-red-500/15 text-red-400 border-red-500/25",
  REJECTED: "bg-red-500/15 text-red-400 border-red-500/25",
  NEW: "bg-white/8 text-white/50 border-white/12",
};

export default function OrdersPage() {
  const router = useRouter();
  const [state, setState] = useState<State>({ kind: "loading" });

  useEffect(() => {
    listOrders()
      .then((orders) => setState({ kind: "ready", orders }))
      .catch(() => setState({ kind: "guest" }));
  }, []);

  return (
    <AppShell back={{ title: "My Orders", fallbackHref: "/app" }}>
      <div className="space-y-6 px-5 pt-6 pb-8">
        <h1 className="font-syne text-[22px] font-bold text-white">My Orders</h1>

        {state.kind === "loading" && (
          <div className="space-y-3">
            <SkeletonCard />
            <SkeletonCard />
          </div>
        )}

        {state.kind === "guest" && <GuestWall />}

        {state.kind === "ready" && state.orders.length === 0 && (
          <EmptyState
            icon={<Package className="h-6 w-6" />}
            title="No orders yet"
            message="Browse our catalog and place your first order."
            ctaHref="/shop"
            ctaLabel="Shop Now"
          />
        )}

        {state.kind === "ready" && state.orders.length > 0 && (
          <div className="space-y-3">
            <SectionLabel>{state.orders.length} order{state.orders.length !== 1 ? "s" : ""}</SectionLabel>
            {state.orders.map((order) => (
              <button
                key={order.id}
                onClick={() => router.push(`/orders/${order.id}`)}
                className="flex w-full items-center gap-3 rounded-2xl border border-white/8 bg-white/4 px-4 py-4 text-left transition hover:border-emerald-500/30 hover:bg-white/6"
              >
                <span className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl border border-emerald-500/20 bg-emerald-500/10 text-[11px] font-bold text-emerald-400">
                  #{order.code.split("-").pop()}
                </span>
                <div className="min-w-0 flex-1">
                  <p className="text-[13px] font-semibold text-white">{order.code}</p>
                  <p className="truncate text-[11px] text-[#b1bdb0]">
                    {order.items.map((i) => i.product_name).join(", ")}
                  </p>
                  {order.customer_facing_status && (
                    <p className="truncate text-[11px] text-emerald-300/80">
                      {order.customer_facing_status}
                    </p>
                  )}
                  <p className="mt-0.5 text-[11px] text-[#b1bdb0]">
                    {new Date(order.created_at).toLocaleDateString("en-NG", { day: "numeric", month: "short", year: "numeric" })}
                  </p>
                </div>
                <div className="shrink-0 text-right space-y-1">
                  <span className={`inline-flex items-center rounded-full border px-2 py-0.5 text-[10px] font-semibold ${STATUS_COLOR[order.status] ?? "bg-white/8 text-white/50 border-white/12"}`}>
                    {STATUS_LABEL[order.status] ?? order.status}
                  </span>
                  {order.fulfillment_status && (
                    <p className="text-[10px] text-[#b1bdb0]">
                      {FULFILLMENT_LABEL[order.fulfillment_status] ?? order.fulfillment_status}
                    </p>
                  )}
                  <p className="text-[12px] font-semibold text-emerald-400">
                    ₦{Number(order.total).toLocaleString()}
                  </p>
                </div>
              </button>
            ))}
          </div>
        )}
      </div>
    </AppShell>
  );
}
