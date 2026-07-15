"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { ChevronRight } from "lucide-react";
import { isAuthError } from "@/lib/api";
import { listRequests, type ProductRequest } from "@/lib/api/requests";
import { AppShell } from "@/components/app/app-shell";
import { StaggerItem, StaggerList } from "@/components/app/motion";
import {
  EmptyState,
  GuestWall,
  LoadFailed,
  SectionLabel,
  SkeletonCard,
  StatusChip,
} from "@/components/app/ui";
import { GenericIcon } from "@/components/app/drug-icons";

type State =
  | { kind: "loading" }
  | { kind: "guest" }
  | { kind: "failed" }
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

  // A 401 means the backend looked and said "not you" - that is real.
  // Anything else (offline, timeout, 500) means nobody looked, so we must
  // not render a guest wall and tell a signed-in customer their account
  // is gone.
  const load = useCallback(() => {
    setState({ kind: "loading" });
    listRequests()
      .then((requests) => setState({ kind: "ready", requests }))
      .catch((e) =>
        setState(isAuthError(e) ? { kind: "guest" } : { kind: "failed" })
      );
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <AppShell>
      <div className="space-y-6 px-5 pt-10 pb-4">

        {/* Header */}
        <div className="flex items-center justify-between">
          <h1 className="font-syne text-[22px] font-bold text-white">My Requests</h1>
          {state.kind === "ready" && state.requests.length > 0 && (
            <span className="rounded-full border border-white/10 bg-white/6 px-2.5 py-0.5 text-xs font-semibold text-white/50">
              {state.requests.length}
            </span>
          )}
        </div>

        {state.kind === "loading" && (
          <div className="space-y-3">
            <SectionLabel>Loading your requests</SectionLabel>
            <SkeletonCard lines={2} />
            <SkeletonCard lines={2} />
            <SkeletonCard lines={2} />
          </div>
        )}

        {state.kind === "guest" && <GuestWall />}

        {state.kind === "failed" && <LoadFailed what="your requests" onRetry={load} />}

        {state.kind === "ready" && state.requests.length === 0 && (
          <EmptyState
            icon={<GenericIcon size={28} />}
            title="No requests yet"
            message="When you ask us to check a medicine, it will show up here with its status."
            ctaHref="/request"
            ctaLabel="Check Availability"
          />
        )}

        {state.kind === "ready" && state.requests.length > 0 && (
          <StaggerList className="space-y-3">
            {state.requests.map((r) => (
              <StaggerItem key={r.id}>
              <Link
                href={`/requests/${r.id}`}
                className="flex items-center gap-4 rounded-2xl border border-white/8 bg-white/4 px-4 py-4 transition-all hover:border-emerald-500/30 hover:bg-white/6 active:bg-white/8"
              >
                {/* Drug icon */}
                <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl border border-emerald-500/20 bg-emerald-500/10">
                  <GenericIcon size={26} />
                </span>

                {/* Content */}
                <span className="min-w-0 flex-1 space-y-1.5">
                  <span className="block truncate text-[15px] font-semibold text-white">
                    {r.product_name}
                    {r.strength && (
                      <span className="ml-1.5 font-normal text-[#b1bdb0]">· {r.strength}</span>
                    )}
                  </span>
                  <span className="flex items-center gap-2">
                    <StatusChip status={r.status} />
                    <span className="text-[11px] text-[#b1bdb0]">{formatDate(r.created_at)}</span>
                  </span>
                </span>

                <ChevronRight className="h-4 w-4 shrink-0 text-[#b1bdb0]" />
              </Link>
              </StaggerItem>
            ))}
          </StaggerList>
        )}
      </div>
    </AppShell>
  );
}
