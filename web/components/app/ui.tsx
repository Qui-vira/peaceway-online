"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { ArrowLeft, ChevronRight, UserPlus } from "lucide-react";
import { DrugIcon } from "@/components/app/drug-icons";
import { PeacewayLoader } from "@/components/app/peaceway-loader";
import type { MedicationReminder } from "@/lib/api/reminders";

export { PeacewayLoader };

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
      className="group flex items-center gap-4 rounded-2xl border border-white/10 bg-white/4 px-5 transition-all duration-300 hover:-translate-y-0.5 hover:border-emerald-500/40 hover:bg-white/6 hover:shadow-[0_10px_28px_rgba(0,0,0,0.35)] active:bg-white/8 motion-reduce:transform-none motion-reduce:transition-none"
      style={{ paddingTop: 18, paddingBottom: 18 }}
    >
      <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-emerald-500/12 text-emerald-400 transition-all duration-300 group-hover:bg-emerald-500/20 group-hover:shadow-[0_0_16px_rgba(16,185,129,0.35)]">
        {icon}
      </span>
      <span className="min-w-0 flex-1">
        <span className="block text-sm font-semibold text-white">{title}</span>
        <span className="block truncate text-xs text-white/45">{description}</span>
      </span>
      <ChevronRight className="h-4 w-4 shrink-0 text-white/30 transition-all duration-300 group-hover:translate-x-1 group-hover:text-emerald-400 motion-reduce:transform-none" />
    </Link>
  );
}

export function Spinner() {
  return <PeacewayLoader />;
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
      <Link
        href="/"
        className="text-[13px] text-white/35 hover:text-white/60 transition"
      >
        ← Back to Home
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

// ── New design-system additions ───────────────────────────────────────────────

export function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <p className="text-[10px] font-semibold uppercase tracking-[0.14em] text-white/40">
      {children}
    </p>
  );
}

export function FeatureCard({
  href,
  icon,
  title,
  subtitle,
}: {
  href: string;
  icon: React.ReactNode;
  title: string;
  subtitle: string;
}) {
  return (
    <Link
      href={href}
      className="group flex flex-col gap-3 rounded-2xl border border-white/8 bg-white/4 p-5 transition-all duration-200 hover:border-emerald-500/30 hover:bg-white/6 active:bg-white/8"
    >
      <span className="flex h-11 w-11 items-center justify-center rounded-xl bg-emerald-500/12 transition-all duration-200 group-hover:bg-emerald-500/20">
        {icon}
      </span>
      <span>
        <span className="block text-[15px] font-semibold leading-tight text-white">
          {title}
        </span>
        <span className="mt-0.5 block text-xs leading-snug text-white/45">
          {subtitle}
        </span>
      </span>
    </Link>
  );
}

export type TimeChipStatus = "upcoming" | "sent" | "missed";

export function TimeChip({
  time,
  status = "upcoming",
}: {
  time: string;
  status?: TimeChipStatus;
}) {
  const tone =
    status === "missed"
      ? "bg-red-500/15 text-red-400 border-red-500/25"
      : status === "sent"
      ? "bg-white/8 text-white/40 border-white/10"
      : "bg-emerald-500/15 text-emerald-400 border-emerald-500/25";
  return (
    <span
      className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-[11px] font-medium ${tone}`}
    >
      {time}
    </span>
  );
}

export function ReminderStatusBadge({ status }: { status: string }) {
  const cfg: Record<string, string> = {
    ACTIVE: "bg-emerald-500/15 text-emerald-400 border-emerald-500/25",
    PAUSED: "bg-amber-500/15 text-amber-400 border-amber-500/25",
    STOPPED: "bg-red-500/15 text-red-400 border-red-500/25",
    COMPLETED: "bg-white/8 text-white/40 border-white/10",
  };
  const labels: Record<string, string> = {
    ACTIVE: "Active",
    PAUSED: "Paused",
    STOPPED: "Stopped",
    COMPLETED: "Completed",
  };
  const tone = cfg[status] ?? "bg-white/8 text-white/40 border-white/10";
  return (
    <span
      className={`inline-flex items-center rounded-full border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide ${tone}`}
    >
      {labels[status] ?? status}
    </span>
  );
}

export function MedCard({
  reminder,
  onClick,
}: {
  reminder: MedicationReminder;
  onClick?: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className="flex w-full items-center gap-3 rounded-2xl border border-white/8 bg-white/4 px-4 py-4 text-left transition-colors hover:border-emerald-500/30 hover:bg-white/6 active:bg-white/8"
    >
      <span className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl border border-emerald-500/20 bg-emerald-500/12">
        <DrugIcon size={28} />
      </span>
      <span className="min-w-0 flex-1">
        <span className="block truncate text-[15px] font-semibold text-white">
          {reminder.medicine_name}
        </span>
        {reminder.instructions_text && (
          <span className="block truncate text-xs text-white/45">
            {reminder.instructions_text}
          </span>
        )}
        <span className="mt-1.5 flex flex-wrap gap-1">
          {reminder.times.slice(0, 3).map((t) => (
            <TimeChip key={t} time={t} />
          ))}
          {reminder.times.length > 3 && (
            <span className="text-xs text-white/30">
              +{reminder.times.length - 3} more
            </span>
          )}
        </span>
      </span>
      <span className="flex shrink-0 flex-col items-end gap-2">
        <ReminderStatusBadge status={reminder.status} />
        <ChevronRight className="h-4 w-4 text-white/25" />
      </span>
    </button>
  );
}

// ── Universal back navigation ──────────────────────────────────────────────────

/**
 * Sticky page header with a guaranteed "back" affordance.
 *
 * `back()` uses browser history when possible, but falls back to `fallbackHref`
 * when the page was deep-linked (history has no in-app entry) so the button
 * never dead-ends. Give every screen except the section homes a PageHeader.
 */
export function PageHeader({
  title,
  fallbackHref = "/app",
  right,
}: {
  title?: string;
  fallbackHref?: string;
  right?: React.ReactNode;
}) {
  const router = useRouter();

  function goBack() {
    if (typeof window !== "undefined" && window.history.length > 1) {
      router.back();
    } else {
      router.push(fallbackHref);
    }
  }

  return (
    <div className="sticky top-0 z-40 -mx-5 mb-2 flex items-center gap-3 border-b border-white/8 bg-[#0b0c09]/85 px-5 py-3 backdrop-blur-md">
      <button
        onClick={goBack}
        aria-label="Go back"
        className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full border border-white/10 bg-white/5 text-white/70 transition hover:border-white/20 hover:text-white active:bg-white/10"
      >
        <ArrowLeft className="h-4 w-4" />
      </button>
      {title && (
        <p className="min-w-0 flex-1 truncate text-[15px] font-semibold text-white">{title}</p>
      )}
      {right && <div className="ml-auto shrink-0">{right}</div>}
    </div>
  );
}

// ── Buttons ────────────────────────────────────────────────────────────────────

type ButtonVariant = "primary" | "secondary" | "ghost" | "danger";

const BUTTON_VARIANTS: Record<ButtonVariant, string> = {
  primary: "bg-emerald-500 text-black hover:bg-emerald-400 hover:shadow-[0_10px_30px_rgba(26,163,90,0.35)]",
  secondary: "border border-white/12 text-white/80 hover:border-white/25 hover:text-white",
  ghost: "text-white/60 hover:text-white",
  danger: "border border-red-500/30 text-red-300 hover:bg-red-500/10",
};

export function Button({
  variant = "primary",
  className = "",
  children,
  ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement> & { variant?: ButtonVariant }) {
  return (
    <button
      {...props}
      className={[
        "inline-flex items-center justify-center gap-2 rounded-xl px-5 py-3 text-sm font-semibold transition-all duration-200",
        "active:scale-[0.98] motion-reduce:transform-none",
        "disabled:cursor-not-allowed disabled:opacity-50 disabled:active:scale-100",
        BUTTON_VARIANTS[variant],
        className,
      ].join(" ")}
    >
      {children}
    </button>
  );
}

// ── Order / fulfilment status badges ────────────────────────────────────────────

const ORDER_STATUS: Record<string, { label: string; tone: string }> = {
  NEW: { label: "Received", tone: "bg-white/8 text-white/60 border-white/10" },
  AWAITING_PAYMENT: { label: "Awaiting payment", tone: "bg-amber-500/15 text-amber-400 border-amber-500/25" },
  PAYMENT_SUBMITTED: { label: "Payment submitted", tone: "bg-amber-500/15 text-amber-400 border-amber-500/25" },
  PAYMENT_APPROVED: { label: "Payment confirmed", tone: "bg-emerald-500/15 text-emerald-400 border-emerald-500/25" },
  PROCESSING: { label: "Being prepared", tone: "bg-emerald-500/15 text-emerald-400 border-emerald-500/25" },
  DISPATCHED: { label: "On the way", tone: "bg-sky-500/15 text-sky-300 border-sky-500/25" },
  DELIVERED: { label: "Delivered", tone: "bg-emerald-500/15 text-emerald-400 border-emerald-500/25" },
  CANCELLED: { label: "Cancelled", tone: "bg-red-500/15 text-red-400 border-red-500/25" },
  REJECTED: { label: "Rejected", tone: "bg-red-500/15 text-red-400 border-red-500/25" },
};

const FULFILLMENT_STATUS: Record<string, { label: string; tone: string }> = {
  in_stock: { label: "In stock", tone: "bg-emerald-500/15 text-emerald-400 border-emerald-500/25" },
  source_from_network: { label: "Sourcing from network", tone: "bg-white/8 text-white/60 border-white/10" },
  sourcing_requested: { label: "Partner request sent", tone: "bg-amber-500/15 text-amber-400 border-amber-500/25" },
  partner_confirmed: { label: "Partner confirmed", tone: "bg-emerald-500/15 text-emerald-400 border-emerald-500/25" },
  partner_rejected: { label: "Partner unavailable", tone: "bg-red-500/15 text-red-400 border-red-500/25" },
  pack_ready: { label: "Pack ready", tone: "bg-emerald-500/15 text-emerald-400 border-emerald-500/25" },
  dispatch_assigned: { label: "Dispatch assigned", tone: "bg-sky-500/15 text-sky-300 border-sky-500/25" },
  picked_up: { label: "Picked up", tone: "bg-sky-500/15 text-sky-300 border-sky-500/25" },
  delivered: { label: "Delivered", tone: "bg-emerald-500/15 text-emerald-400 border-emerald-500/25" },
  failed: { label: "Issue under review", tone: "bg-red-500/15 text-red-400 border-red-500/25" },
};

function Badge({ label, tone }: { label: string; tone: string }) {
  return (
    <span className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium ${tone}`}>
      {label}
    </span>
  );
}

export function OrderStatusBadge({ status }: { status: string }) {
  const cfg = ORDER_STATUS[status] ?? { label: status, tone: "bg-white/8 text-white/60 border-white/10" };
  return <Badge label={cfg.label} tone={cfg.tone} />;
}

export function FulfillmentBadge({ status }: { status: string }) {
  const cfg = FULFILLMENT_STATUS[status] ?? { label: status, tone: "bg-white/8 text-white/60 border-white/10" };
  return <Badge label={cfg.label} tone={cfg.tone} />;
}

export function SkeletonCard({ lines = 2 }: { lines?: 2 | 3 }) {
  return (
    <div className="flex items-center gap-3 rounded-2xl border border-white/6 bg-white/3 px-4 py-4">
      <div className="h-12 w-12 shrink-0 animate-pulse rounded-xl bg-white/8" />
      <div className="flex-1 space-y-2">
        <div className="h-3.5 w-2/3 animate-pulse rounded-full bg-white/8" />
        {lines >= 2 && (
          <div className="h-3 w-1/2 animate-pulse rounded-full bg-white/6" />
        )}
        {lines >= 3 && (
          <div className="flex gap-1.5 pt-0.5">
            <div className="h-5 w-14 animate-pulse rounded-full bg-white/6" />
            <div className="h-5 w-14 animate-pulse rounded-full bg-white/6" />
          </div>
        )}
      </div>
    </div>
  );
}
