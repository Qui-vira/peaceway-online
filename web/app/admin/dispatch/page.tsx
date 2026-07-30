"use client";

import { useEffect, useMemo, useState } from "react";
import { RefreshCcw, ShieldAlert } from "lucide-react";
import { AdminFetchError, adminFetch, getAdminToken } from "@/lib/admin-auth";
import { Button, FulfillmentBadge, PageHeader } from "@/components/app/ui";

type SourcingRow = {
  id: string;
  order_id: string;
  fulfillment_status: string;
  customer_facing_status: string | null;
  ready_for_pickup_at: string | null;
  pickup_code: string | null;
  updated_at: string;
};

type LoadState = "loading" | "ready" | "forbidden" | "error";

export default function AdminDispatchPage() {
  const [rows, setRows] = useState<SourcingRow[]>([]);
  const [state, setState] = useState<LoadState>("loading");
  const [error, setError] = useState("");

  async function load() {
    setState("loading");
    setError("");
    try {
      const data = await adminFetch<SourcingRow[]>("/admin/sourcing");
      setRows(data);
      setState("ready");
    } catch (e) {
      if (e instanceof AdminFetchError && e.status === 403) {
        setState("forbidden");
      } else {
        setError(e instanceof Error ? e.message : "Could not load dispatch queue.");
        setState("error");
      }
    }
  }

  useEffect(() => {
    if (!getAdminToken()) {
      // Carry the destination, so signing in returns staff to the screen
      // they asked for instead of dropping them on the dashboard.
      window.location.href = "/admin?next=/admin/dispatch";
      return;
    }
    load();
  }, []);

  const dispatchRows = useMemo(
    () => rows.filter((row) => ["pack_ready", "dispatch_assigned", "picked_up"].includes(row.fulfillment_status)),
    [rows]
  );

  return (
    <div className="min-h-screen bg-[#0b0c09] px-5 py-8 text-white">
      <div className="mx-auto max-w-4xl">
        <PageHeader
          title="Dispatch Readiness"
          fallbackHref="/admin"
          right={
            <Button variant="secondary" onClick={load} className="px-4 py-2">
              <RefreshCcw className="h-4 w-4" />
              Refresh
            </Button>
          }
        />

        <div className="space-y-4 pt-4">
          <p className="text-sm text-white/45">
            Only orders with partner pack-ready confirmation appear here.
          </p>

          {state === "forbidden" && (
            <div className="flex items-start gap-3 rounded-2xl border border-amber-500/20 bg-amber-500/8 px-4 py-4 text-sm text-amber-100/85">
              <ShieldAlert className="mt-0.5 h-5 w-5 shrink-0 text-amber-400" />
              <div>
                <p className="font-semibold">You don&apos;t have access to this view</p>
                <p className="mt-1 text-amber-100/70">
                  The dispatch queue needs dispatch or order permissions. Ask a System Owner to grant access.
                </p>
              </div>
            </div>
          )}

          {state === "error" && (
            <div className="rounded-2xl border border-red-500/20 bg-red-500/10 px-4 py-3 text-sm text-red-300">
              {error}
            </div>
          )}

          {state === "ready" &&
            dispatchRows.map((row) => (
              <div key={row.id} className="rounded-2xl border border-white/8 bg-white/4 p-4">
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <FulfillmentBadge status={row.fulfillment_status} />
                    <p className="mt-2 text-sm font-semibold">{row.customer_facing_status ?? row.fulfillment_status}</p>
                    <p className="mt-1 text-xs text-white/45">Order {row.order_id}</p>
                  </div>
                  <div className="text-right text-xs text-white/45">
                    {row.ready_for_pickup_at && <p>Ready: {new Date(row.ready_for_pickup_at).toLocaleString("en-NG")}</p>}
                    {row.pickup_code && (
                      <p>
                        Pickup code: <span className="font-semibold text-white">{row.pickup_code}</span>
                      </p>
                    )}
                  </div>
                </div>
              </div>
            ))}

          {state === "ready" && dispatchRows.length === 0 && (
            <div className="rounded-2xl border border-dashed border-white/10 p-4 text-sm text-white/45">
              No pack-ready sourcing orders yet.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
