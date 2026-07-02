"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import { getRequest, type ProductRequestDetail } from "@/lib/api/requests";
import { AppShell } from "@/components/app/app-shell";
import { GuestWall, Spinner, StatusChip } from "@/components/app/ui";

function formatDateTime(iso: string): string {
  return new Date(iso).toLocaleString("en-NG", {
    day: "numeric",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function DetailRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-baseline justify-between gap-4 py-2.5">
      <span className="text-xs font-semibold uppercase tracking-widest text-white/35">
        {label}
      </span>
      <span className="text-right text-sm text-white/85">{value}</span>
    </div>
  );
}

export default function RequestDetailPage({
  params,
}: {
  params: { id: string };
}) {
  const [req, setReq] = useState<ProductRequestDetail | null>(null);
  const [error, setError] = useState<"guest" | "notfound" | null>(null);

  useEffect(() => {
    getRequest(params.id)
      .then(setReq)
      .catch((e) => setError(e?.status === 404 ? "notfound" : "guest"));
  }, [params.id]);

  return (
    <AppShell>
      <div className="px-5 pt-8 pb-4">
        <Link
          href="/requests"
          className="inline-flex items-center gap-2 text-xs font-semibold uppercase tracking-widest text-white/40 transition hover:text-white/70"
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          All requests
        </Link>
      </div>

      {!req && !error && <Spinner />}
      {error === "guest" && <GuestWall />}
      {error === "notfound" && (
        <p className="px-5 py-10 text-center text-sm text-white/50">
          This request could not be found.
        </p>
      )}

      {req && (
        <div className="space-y-6 px-5">
          <div className="space-y-3">
            <h1 className="text-2xl font-bold leading-tight text-white">
              {req.product_name}
            </h1>
            <StatusChip status={req.status} />
          </div>

          {req.customer_visible_message && (
            <div className="rounded-2xl border border-emerald-500/25 bg-emerald-500/8 px-5 py-4">
              <p className="mb-1 text-xs font-semibold uppercase tracking-widest text-emerald-400">
                From Peaceway
              </p>
              <p className="text-sm leading-relaxed text-white/85">
                {req.customer_visible_message}
              </p>
            </div>
          )}

          <div className="rounded-2xl border border-white/10 bg-white/4 px-5 py-2 divide-y divide-white/6">
            {req.strength && <DetailRow label="Strength" value={req.strength} />}
            {req.form && <DetailRow label="Form" value={req.form} />}
            {req.quantity && <DetailRow label="Quantity" value={req.quantity} />}
            {req.urgency && (
              <DetailRow label="Urgency" value={req.urgency.replaceAll("_", " ").toLowerCase()} />
            )}
            <DetailRow label="Submitted" value={formatDateTime(req.created_at)} />
          </div>

          {req.thread.length > 0 && (
            <div className="space-y-3">
              <p className="text-xs font-semibold uppercase tracking-widest text-white/35">
                Updates
              </p>
              {req.thread.map((m) => (
                <div
                  key={m.id}
                  className={[
                    "max-w-[85%] rounded-2xl px-4 py-3",
                    m.sender_type === "customer"
                      ? "ml-auto bg-emerald-500/12 border border-emerald-500/20"
                      : "bg-white/5 border border-white/10",
                  ].join(" ")}
                >
                  <p className="text-sm leading-relaxed text-white/85">{m.message_text}</p>
                  <p className="mt-1.5 text-[10px] text-white/30">
                    {m.sender_type === "customer" ? "You" : "Peaceway"} · {formatDateTime(m.created_at)}
                  </p>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </AppShell>
  );
}
