"use client";

import Link from "next/link";
import { ChevronRight, Loader2, UserPlus } from "lucide-react";

export const STATUS_LABELS: Record<string, string> = {
  NEW: "Received",
  CHECKING_AVAILABILITY: "Checking availability",
  NEEDS_MORE_INFO: "More info needed",
  AVAILABLE: "Available",
  NOT_AVAILABLE: "Not currently available",
  ORDERED_FROM_SUPPLIER: "Ordered from supplier",
  READY_TO_ORDER: "Ready to order",
  CUSTOMER_NOTIFIED: "You've been notified",
  CONVERTED_TO_ORDER: "Converted to order",
  FULFILLED: "Fulfilled",
  CLOSED: "Closed",
  REJECTED: "Rejected",
};

const POSITIVE = ["AVAILABLE", "READY_TO_ORDER", "CUSTOMER_NOTIFIED", "FULFILLED"];
const NEGATIVE = ["NOT_AVAILABLE", "REJECTED", "CLOSED"];

export function StatusChip({ status }: { status: string }) {
  const label = STATUS_LABELS[status] ?? status;
  const tone = POSITIVE.includes(status)
    ? "bg-emerald-500/15 text-emerald-400 border-emerald-500/25"
    : NEGATIVE.includes(status)
    ? "bg-red-500/15 text-red-400 border-red-500/25"
    : "bg-white/8 text-white/60 border-white/10";
  return (
    <span className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium ${tone}`}>
      {label}
    </span>
  );
}

export function ActionCard({
  href,
  icon,
  title,
  description,
}: {
  href: string;
  icon: React.ReactNode;
  title: string;
  description: string;
}) {
  return (
    <Link
      href={href}
      className="flex items-center gap-4 rounded-2xl border border-white/10 bg-white/4 px-5 py-4.5 transition-colors hover:border-emerald-500/40 hover:bg-white/6 active:bg-white/8"
      style={{ paddingTop: 18, paddingBottom: 18 }}
    >
      <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-emerald-500/12 text-emerald-400">
        {icon}
      </span>
      <span className="min-w-0 flex-1">
        <span className="block text-sm font-semibold text-white">{title}</span>
        <span className="block truncate text-xs text-white/45">{description}</span>
      </span>
      <ChevronRight className="h-4 w-4 shrink-0 text-white/30" />
    </Link>
  );
}

export function Spinner() {
  return (
    <div className="flex min-h-[50vh] items-center justify-center">
      <Loader2 className="h-6 w-6 animate-spin text-white/30" />
    </div>
  );
}

export function GuestWall({ message }: { message?: string }) {
  return (
    <div className="flex flex-col items-center gap-6 px-5 py-16 text-center">
      <span className="inline-flex h-16 w-16 items-center justify-center rounded-full border border-white/10 bg-white/5">
        <UserPlus className="h-8 w-8 text-white/40" />
      </span>
      <div className="space-y-2">
        <h2 className="text-xl font-bold text-white">Create your profile first</h2>
        <p className="max-w-xs text-sm leading-relaxed text-white/50">
          {message ??
            "We need your contact details so our pharmacists can reach you."}
        </p>
      </div>
      <Link
        href="/start"
        className="inline-flex items-center justify-center gap-2 rounded-xl bg-emerald-500 px-6 py-3.5 text-sm font-semibold text-black transition hover:bg-emerald-400"
      >
        Start Profile
        <ChevronRight className="h-4 w-4" />
      </Link>
    </div>
  );
}

export function EmptyState({
  icon,
  title,
  message,
  ctaHref,
  ctaLabel,
}: {
  icon: React.ReactNode;
  title: string;
  message: string;
  ctaHref?: string;
  ctaLabel?: string;
}) {
  return (
    <div className="flex flex-col items-center gap-5 px-5 py-14 text-center">
      <span className="inline-flex h-14 w-14 items-center justify-center rounded-full border border-white/10 bg-white/5 text-white/40">
        {icon}
      </span>
      <div className="space-y-1.5">
        <h3 className="text-base font-semibold text-white">{title}</h3>
        <p className="max-w-xs text-sm leading-relaxed text-white/45">{message}</p>
      </div>
      {ctaHref && ctaLabel && (
        <Link
          href={ctaHref}
          className="inline-flex items-center gap-2 rounded-xl bg-emerald-500 px-5 py-3 text-sm font-semibold text-black transition hover:bg-emerald-400"
        >
          {ctaLabel}
          <ChevronRight className="h-4 w-4" />
        </Link>
      )}
    </div>
  );
}
