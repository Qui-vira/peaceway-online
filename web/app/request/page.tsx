"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  CheckCircle,
  ChevronRight,
  Loader2,
  Package,
  ClipboardList,
} from "lucide-react";
import {
  createRequest,
  type CreateRequestPayload,
  type ProductRequest,
  type Urgency,
} from "@/lib/api/requests";
import { getMe } from "@/lib/api/customers";
import type { ApiError } from "@/lib/api";

type Field =
  | "product_name"
  | "strength"
  | "form"
  | "quantity"
  | "urgency"
  | "note";
type Errors = Partial<Record<Field | "form_error", string>>;

const URGENCY_OPTIONS: { value: Urgency; label: string }[] = [
  { value: "TODAY", label: "Today — urgent" },
  { value: "WITHIN_24H", label: "Within 24 hours" },
  { value: "THIS_WEEK", label: "This week" },
  { value: "JUST_CHECKING", label: "Just checking availability" },
];

const STATUS_LABELS: Record<string, string> = {
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

function Label({ children, optional }: { children: React.ReactNode; optional?: boolean }) {
  return (
    <label className="block text-xs font-semibold uppercase tracking-widest text-white/40 mb-2">
      {children}
      {optional && (
        <span className="ml-2 normal-case tracking-normal font-normal text-white/25">
          optional
        </span>
      )}
    </label>
  );
}

function InputRow({
  error,
  children,
}: {
  error?: string;
  children: React.ReactNode;
}) {
  return (
    <div className="space-y-1.5">
      <div
        className={[
          "flex items-center gap-3 rounded-xl border px-4 py-3.5 transition-colors",
          "bg-white/4 backdrop-blur-sm",
          error
            ? "border-red-500/50 focus-within:border-red-400"
            : "border-white/10 focus-within:border-emerald-500/60",
        ].join(" ")}
      >
        {children}
      </div>
      {error && <p className="text-xs text-red-400 pl-1">{error}</p>}
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const label = STATUS_LABELS[status] ?? status;
  const isPositive = ["AVAILABLE", "READY_TO_ORDER", "CUSTOMER_NOTIFIED", "FULFILLED"].includes(status);
  const isNegative = ["NOT_AVAILABLE", "REJECTED", "CLOSED"].includes(status);

  return (
    <span
      className={[
        "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium",
        isPositive
          ? "bg-emerald-500/15 text-emerald-400 border border-emerald-500/25"
          : isNegative
          ? "bg-red-500/15 text-red-400 border border-red-500/25"
          : "bg-white/8 text-white/60 border border-white/10",
      ].join(" ")}
    >
      {label}
    </span>
  );
}

export default function RequestPage() {
  const [authed, setAuthed] = useState<boolean | null>(null);
  const [form, setForm] = useState({
    product_name: "",
    strength: "",
    form_type: "",
    quantity: "",
    urgency: "" as Urgency | "",
    note: "",
  });
  const [errors, setErrors] = useState<Errors>({});
  const [loading, setLoading] = useState(false);
  const [submitted, setSubmitted] = useState<ProductRequest | null>(null);

  useEffect(() => {
    getMe()
      .then(() => setAuthed(true))
      .catch(() => setAuthed(false));
  }, []);

  function validate(): Errors {
    const e: Errors = {};
    if (!form.product_name.trim()) {
      e.product_name = "Please enter the product name.";
    }
    return e;
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const errs = validate();
    if (Object.keys(errs).length) {
      setErrors(errs);
      return;
    }
    setErrors({});
    setLoading(true);
    try {
      const payload: CreateRequestPayload = {
        product_name: form.product_name.trim(),
      };
      if (form.strength.trim()) payload.strength = form.strength.trim();
      if (form.form_type.trim()) payload.form = form.form_type.trim();
      if (form.quantity.trim()) payload.quantity = form.quantity.trim();
      if (form.urgency) payload.urgency = form.urgency as Urgency;
      if (form.note.trim()) payload.note = form.note.trim();

      const result = await createRequest(payload);
      setSubmitted(result);
    } catch (err) {
      const apiErr = err as ApiError;
      setErrors({ form_error: apiErr?.detail ?? "Something went wrong. Please try again." });
    } finally {
      setLoading(false);
    }
  }

  // Loading auth state
  if (authed === null) {
    return (
      <main className="min-h-screen flex items-center justify-center">
        <Loader2 className="h-6 w-6 animate-spin text-white/30" />
      </main>
    );
  }

  // Not authenticated
  if (!authed) {
    return (
      <main className="min-h-screen flex items-center justify-center px-5 py-20">
        <div className="w-full max-w-md text-center space-y-6">
          <span className="inline-flex h-16 w-16 items-center justify-center rounded-full bg-white/5 border border-white/10">
            <Package className="h-8 w-8 text-white/40" />
          </span>
          <div className="space-y-2">
            <h1 className="text-2xl font-bold text-white">Register first</h1>
            <p className="text-white/50 text-sm leading-relaxed">
              We need your contact details before you can submit a product request.
            </p>
          </div>
          <Link
            href="/start"
            className="inline-flex items-center justify-center gap-2 rounded-xl bg-emerald-500 px-6 py-3.5 text-sm font-semibold text-black transition hover:bg-emerald-400"
          >
            Get started
            <ChevronRight className="h-4 w-4" />
          </Link>
        </div>
      </main>
    );
  }

  // Success state
  if (submitted) {
    return (
      <main className="min-h-screen flex items-center justify-center px-5 py-20">
        <div className="w-full max-w-md text-center space-y-6">
          <span className="inline-flex h-16 w-16 items-center justify-center rounded-full bg-emerald-500/15 border border-emerald-500/30">
            <CheckCircle className="h-8 w-8 text-emerald-400" />
          </span>
          <div className="space-y-2">
            <h1 className="text-2xl font-bold text-white">Request received</h1>
            <p className="text-white/55 text-sm leading-relaxed">
              We&apos;re checking availability for{" "}
              <span className="text-white font-medium">{submitted.product_name}</span>.
              We&apos;ll reach out by phone or Telegram with an update.
            </p>
          </div>

          <div className="rounded-xl border border-white/8 bg-white/3 px-5 py-4 text-left space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs text-white/40 uppercase tracking-widest font-semibold">Status</span>
              <StatusBadge status={submitted.status} />
            </div>
            {submitted.customer_visible_message && (
              <p className="text-sm text-white/70">{submitted.customer_visible_message}</p>
            )}
          </div>

          <div className="flex flex-col gap-3">
            <button
              onClick={() => {
                setSubmitted(null);
                setForm({ product_name: "", strength: "", form_type: "", quantity: "", urgency: "", note: "" });
              }}
              className="inline-flex items-center justify-center gap-2 rounded-xl bg-emerald-500 px-6 py-3.5 text-sm font-semibold text-black transition hover:bg-emerald-400"
            >
              <ClipboardList className="h-4 w-4" />
              Submit another request
            </button>
            <Link
              href="/requests"
              className="inline-flex items-center justify-center gap-2 rounded-xl border border-white/10 px-6 py-3.5 text-sm font-semibold text-white/70 transition hover:border-white/20 hover:text-white"
            >
              Track My Requests
            </Link>
          </div>
        </div>
      </main>
    );
  }

  // Form
  return (
    <main className="min-h-screen flex items-start justify-center px-5 py-20">
      <div className="w-full max-w-md space-y-8">

        <div className="space-y-2">
          <p className="text-xs font-semibold uppercase tracking-widest text-emerald-400">
            Peaceway Online · Product Request
          </p>
          <h1 className="text-3xl font-bold text-white leading-tight">
            Can&apos;t find what you need?
          </h1>
          <p className="text-white/50 text-sm leading-relaxed">
            Tell us what you&apos;re looking for. Our pharmacists will check stock and call you back.
          </p>
        </div>

        <form onSubmit={handleSubmit} noValidate className="space-y-4">

          <div>
            <Label>Product / Medicine name *</Label>
            <InputRow error={errors.product_name}>
              <input
                type="text"
                placeholder="e.g. Amoxicillin, Vitamin C, Panadol"
                value={form.product_name}
                onChange={(e) => setForm((f) => ({ ...f, product_name: e.target.value }))}
                className="flex-1 bg-transparent text-sm text-white placeholder-white/25 outline-none"
                autoFocus
              />
            </InputRow>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label optional>Strength</Label>
              <InputRow error={errors.strength}>
                <input
                  type="text"
                  placeholder="e.g. 500mg"
                  value={form.strength}
                  onChange={(e) => setForm((f) => ({ ...f, strength: e.target.value }))}
                  className="flex-1 bg-transparent text-sm text-white placeholder-white/25 outline-none"
                />
              </InputRow>
            </div>
            <div>
              <Label optional>Form</Label>
              <InputRow error={errors.form}>
                <input
                  type="text"
                  placeholder="e.g. Tablet"
                  value={form.form_type}
                  onChange={(e) => setForm((f) => ({ ...f, form_type: e.target.value }))}
                  className="flex-1 bg-transparent text-sm text-white placeholder-white/25 outline-none"
                />
              </InputRow>
            </div>
          </div>

          <div>
            <Label optional>Quantity</Label>
            <InputRow error={errors.quantity}>
              <input
                type="text"
                placeholder="e.g. 2 packs, 1 bottle"
                value={form.quantity}
                onChange={(e) => setForm((f) => ({ ...f, quantity: e.target.value }))}
                className="flex-1 bg-transparent text-sm text-white placeholder-white/25 outline-none"
              />
            </InputRow>
          </div>

          <div>
            <Label optional>How soon do you need it?</Label>
            <InputRow error={errors.urgency}>
              <select
                value={form.urgency}
                onChange={(e) =>
                  setForm((f) => ({ ...f, urgency: e.target.value as Urgency | "" }))
                }
                className="flex-1 bg-transparent text-sm text-white outline-none appearance-none [&>option]:bg-[#0b0c09]"
              >
                <option value="">Select urgency…</option>
                {URGENCY_OPTIONS.map((o) => (
                  <option key={o.value} value={o.value}>
                    {o.label}
                  </option>
                ))}
              </select>
            </InputRow>
          </div>

          <div>
            <Label optional>Additional notes</Label>
            <div
              className={[
                "rounded-xl border px-4 py-3.5 transition-colors",
                "bg-white/4 backdrop-blur-sm",
                errors.note
                  ? "border-red-500/50 focus-within:border-red-400"
                  : "border-white/10 focus-within:border-emerald-500/60",
              ].join(" ")}
            >
              <textarea
                rows={3}
                placeholder="Brand preference, diagnosis, any other details…"
                value={form.note}
                onChange={(e) => setForm((f) => ({ ...f, note: e.target.value }))}
                className="w-full bg-transparent text-sm text-white placeholder-white/25 outline-none resize-none"
                maxLength={1000}
              />
            </div>
            {errors.note && <p className="text-xs text-red-400 pl-1 mt-1.5">{errors.note}</p>}
          </div>

          {errors.form_error && (
            <p className="rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400">
              {errors.form_error}
            </p>
          )}

          <button
            type="submit"
            disabled={loading}
            className="mt-2 w-full inline-flex items-center justify-center gap-2 rounded-xl bg-emerald-500 px-6 py-3.5 text-sm font-semibold text-black transition hover:bg-emerald-400 disabled:opacity-60 disabled:cursor-not-allowed"
          >
            {loading ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                Sending…
              </>
            ) : (
              <>
                Send Request
                <ChevronRight className="h-4 w-4" />
              </>
            )}
          </button>

          <p className="text-center text-xs text-white/30 leading-relaxed pt-1">
            A Peaceway pharmacist will review your request and contact you to confirm availability.
          </p>
        </form>

        <div className="text-center">
          <Link href="/" className="text-xs text-white/30 hover:text-white/60 transition">
            ← Back to home
          </Link>
        </div>
      </div>
    </main>
  );
}
