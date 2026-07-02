"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ChevronRight, ClipboardList } from "lucide-react";
import { listRequests, type ProductRequest } from "@/lib/api/requests";
import { AppShell, AppHeader } from "@/components/app/app-shell";
import { EmptyState, GuestWall, Spinner, StatusChip } from "@/components/app/ui";

type State =
  | { kind: "loading" }
  | { kind: "guest" }
  | { kind: "ready"; requests: ProductRequest[] };

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("en-NG", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

export default function RequestsPage() {
  const [state, setState] = useState<State>({ kind: "loading" });

  useEffect(() => {
    listRequests()
      .then((requests) => setState({ kind: "ready", requests }))
      .catch(() => setState({ kind: "guest" }));
  }, []);

  return (
    <AppShell>
      <AppHeader
        title="My Requests"
        subtitle="Every availability request you've made, with live status."
      />

      {state.kind === "loading" && <Spinner />}
      {state.kind === "guest" && <GuestWall />}
      {state.kind === "ready" && state.requests.length === 0 && (
        <EmptyState
          icon={<ClipboardList className="h-6 w-6" />}
          title="No requests yet"
          message="When you ask us to check a medicine, it will show up here with its status."
          ctaHref="/request"
          ctaLabel="Check Availability"
        />
      )}
      {state.kind === "ready" && state.requests.length > 0 && (
        <div className="space-y-3 px-5">
          {state.requests.map((r) => (
            <Link
              key={r.id}
              href={`/requests/${r.id}`}
              className="flex items-center gap-4 rounded-2xl border border-white/10 bg-white/4 px-5 py-4 transition-colors hover:border-emerald-500/40 active:bg-white/8"
            >
              <span className="min-w-0 flex-1 space-y-1.5">
                <span className="block truncate text-sm font-semibold text-white">
                  {r.product_name}
                  {r.strength ? ` · ${r.strength}` : ""}
                </span>
                <span className="flex items-center gap-2">
                  <StatusChip status={r.status} />
                  <span className="text-xs text-white/35">{formatDate(r.created_at)}</span>
                </span>
              </span>
              <ChevronRight className="h-4 w-4 shrink-0 text-white/30" />
            </Link>
          ))}
        </div>
      )}
    </AppShell>
  );
}
