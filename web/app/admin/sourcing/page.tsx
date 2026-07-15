"use client";

import { useEffect, useState } from "react";
import { RefreshCcw, ShieldAlert } from "lucide-react";
import { AdminFetchError, adminFetch, getAdminToken } from "@/lib/admin-auth";
import { Button, FulfillmentBadge, PageHeader } from "@/components/app/ui";

type SourcingRow = {
  id: string;
  order_id: string;
  fulfillment_status: string;
  sourcing_required: boolean;
  partner_id: string | null;
  partner_type: string | null;
  sourcing_channel: string | null;
  customer_facing_status: string | null;
  requested_items: { product_name: string; requested_qty?: number; quantity?: number }[] | null;
  ready_for_pickup_at: string | null;
  pickup_code: string | null;
  last_error: string | null;
  updated_at: string;
};

type PartnerRow = {
  id: string;
  key: string;
  name: string;
  partner_type: string;
  channel_type: string;
  portal_contact: string | null;
  is_active: boolean;
};

type LoadState = "loading" | "ready" | "forbidden" | "error";

export default function AdminSourcingPage() {
  const [rows, setRows] = useState<SourcingRow[]>([]);
  const [partners, setPartners] = useState<PartnerRow[]>([]);
  const [state, setState] = useState<LoadState>("loading");
  const [error, setError] = useState("");

  async function load() {
    setState("loading");
    setError("");
    try {
      const [sourcing, networkPartners] = await Promise.all([
        adminFetch<SourcingRow[]>("/admin/sourcing"),
        adminFetch<PartnerRow[]>("/admin/network-partners"),
      ]);
      setRows(sourcing);
      setPartners(networkPartners);
      setState("ready");
    } catch (e) {
      if (e instanceof AdminFetchError && e.status === 403) {
        setState("forbidden");
      } else {
        setError(e instanceof Error ? e.message : "Could not load sourcing data.");
        setState("error");
      }
    }
  }

  useEffect(() => {
    if (!getAdminToken()) {
      window.location.href = "/admin";
      return;
    }
    load();
  }, []);

  return (
    <div className="min-h-screen bg-[#0b0c09] px-5 py-8 text-white">
      <div className="mx-auto max-w-6xl">
        <PageHeader
          title="Sourcing Control"
          fallbackHref="/admin"
          right={
            <Button variant="secondary" onClick={load} className="px-4 py-2">
              <RefreshCcw className="h-4 w-4" />
              Refresh
            </Button>
          }
        />

        <div className="space-y-6 pt-4">
          <p className="text-sm text-white/45">
            Out-of-stock orders routed through Peaceway&apos;s approved partner network.
          </p>

          {state === "forbidden" && (
            <div className="flex items-start gap-3 rounded-2xl border border-amber-500/20 bg-amber-500/8 px-4 py-4 text-sm text-amber-100/85">
              <ShieldAlert className="mt-0.5 h-5 w-5 shrink-0 text-amber-400" />
              <div>
                <p className="font-semibold">You don&apos;t have access to this view</p>
                <p className="mt-1 text-amber-100/70">
                  Sourcing control needs order or pricing permissions. Ask a System Owner to grant access.
                </p>
              </div>
            </div>
          )}

          {state === "error" && (
            <div className="rounded-2xl border border-red-500/20 bg-red-500/10 px-4 py-3 text-sm text-red-300">
              {error}
            </div>
          )}

          {(state === "ready" || state === "loading") && (
            <>
              <section className="rounded-3xl border border-white/8 bg-white/4 p-5">
                <div className="mb-4">
                  <p className="text-xs uppercase tracking-[0.18em] text-[#b1bdb0]">Network Partners</p>
                  <p className="mt-1 text-lg font-semibold">{partners.length} configured</p>
                </div>
                <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
                  {partners.map((partner) => (
                    <div key={partner.id} className="rounded-2xl border border-white/8 bg-black/20 p-4">
                      <p className="text-sm font-semibold">{partner.name}</p>
                      <p className="mt-1 text-xs text-white/45">
                        {partner.partner_type} · {partner.channel_type}
                      </p>
                      <p className="mt-3 text-xs text-[#b1bdb0]">{partner.portal_contact ?? partner.key}</p>
                    </div>
                  ))}
                  {state === "ready" && partners.length === 0 && (
                    <div className="rounded-2xl border border-dashed border-white/10 p-4 text-sm text-white/45">
                      No network partners yet. Add wholesalers or suppliers through the admin API first.
                    </div>
                  )}
                </div>
              </section>

              <section className="rounded-3xl border border-white/8 bg-white/4 p-5">
                <div className="mb-4">
                  <p className="text-xs uppercase tracking-[0.18em] text-[#b1bdb0]">Sourcing Requests</p>
                  <p className="mt-1 text-lg font-semibold">{rows.length} tracked orders</p>
                </div>
                <div className="space-y-3">
                  {rows.map((row) => (
                    <div key={row.id} className="rounded-2xl border border-white/8 bg-black/20 p-4">
                      <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
                        <div className="space-y-2">
                          <FulfillmentBadge status={row.fulfillment_status} />
                          <p className="text-xs text-white/45">Order {row.order_id}</p>
                          <p className="text-xs text-white/45">
                            {row.partner_type ?? "unassigned"} · {row.sourcing_channel ?? "pending"}
                          </p>
                          {row.requested_items && (
                            <p className="text-xs text-white/60">
                              {row.requested_items
                                .map((item) => `${item.product_name} ×${item.requested_qty ?? item.quantity ?? 1}`)
                                .join(", ")}
                            </p>
                          )}
                          {row.last_error && <p className="text-xs text-amber-300">{row.last_error}</p>}
                        </div>
                        <div className="space-y-1 text-xs text-white/45 md:text-right">
                          {row.ready_for_pickup_at && (
                            <p>Ready: {new Date(row.ready_for_pickup_at).toLocaleString("en-NG")}</p>
                          )}
                          {row.pickup_code && (
                            <p>
                              Pickup code: <span className="font-semibold text-white">{row.pickup_code}</span>
                            </p>
                          )}
                          <p>Updated {new Date(row.updated_at).toLocaleString("en-NG")}</p>
                        </div>
                      </div>
                    </div>
                  ))}
                  {state === "ready" && rows.length === 0 && (
                    <div className="rounded-2xl border border-dashed border-white/10 p-4 text-sm text-white/45">
                      No sourcing requests yet.
                    </div>
                  )}
                </div>
              </section>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
