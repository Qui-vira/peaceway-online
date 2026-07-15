"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  ArrowLeft,
  CheckCircle,
  ChevronRight,
  ClipboardList,
  Loader2,
  Package,
} from "lucide-react";
import {
  createRequest,
  type CreateRequestPayload,
  type ProductRequest,
  type Urgency,
} from "@/lib/api/requests";
import { getMe } from "@/lib/api/customers";
import type { ApiError } from "@/lib/api";
import { AppShell } from "@/components/app/app-shell";
import { GuestWall, StatusChip } from "@/components/app/ui";
import { TabletIcon } from "@/components/app/drug-icons";

type Field = "product_name" | "strength" | "form" | "quantity" | "urgency" | "note";
type Errors = Partial<Record<Field | "form_error", string>>;

const URGENCY_OPTIONS: { value: Urgency; label: string; sub: string }[] = [
  { value: "TODAY", label: "Today", sub: "Urgent, need it now" },
  { value: "WITHIN_24H", label: "Within 24 Hours", sub: "By tomorrow" },
  { value: "THIS_WEEK", label: "This Week", sub: "No rush" },
  { value: "JUST_CHECKING", label: "Just Checking", sub: "Availability only" },
];

function SectionCard({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div className="space-y-4 rounded-2xl border border-white/8 bg-white/[0.03] px-5 py-5">
      <p className="text-[10px] font-semibold uppercase tracking-widest text-[#b1bdb0]">
        {label}
      </p>
      {children}
    </div>
  );
}

function FieldWrap({
  label,
  optional,
  error,
  children,
}: {
  label: string;
  optional?: boolean;
  error?: string;
  children: React.ReactNode;
}) {
  return (
    <div className="space-y-1.5">
      <label className="flex items-center gap-2 text-[10px] font-semibold uppercase tracking-widest text-[#b1bdb0]">
        {label}
        {optional && (
          <span className="rounded-full bg-white/8 px-1.5 py-px text-[9px] normal-case tracking-normal font-normal text-[#b1bdb0]">
            optional
          </span>
        )}
      </label>
      <div
        className={[
          "flex items-center gap-3 rounded-xl border px-4 py-3.5 transition-colors bg-white/4",
          error
            ? "border-red-500/50 focus-within:border-red-400"
            : "border-white/10 focus-within:border-emerald-500/50",
        ].join(" ")}
      >
        {children}
      </div>
      {error && <p className="pl-1 text-xs text-red-400">{error}</p>}
    </div>
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
      setErrors({
        form_error: apiErr?.detail ?? "Something went wrong. Please try again.",
      });
    } finally {
      setLoading(false);
    }
  }

  if (authed === null) {
    return (
      <AppShell>
        <div className="flex min-h-[60vh] items-center justify-center">
          <Loader2 className="h-6 w-6 animate-spin text-[#b1bdb0]" />
        </div>
      </AppShell>
    );
  }

  if (!authed) {
    return (
      <AppShell>
        <GuestWall message="Register first so we can contact you about your request." />
      </AppShell>
    );
  }

  if (submitted) {
    return (
      <AppShell>
        <div className="flex min-h-[70vh] items-center justify-center px-5 py-16">
          <div className="w-full max-w-md space-y-7 text-center">
            <span className="inline-flex h-[72px] w-[72px] items-center justify-center rounded-full border border-emerald-500/30 bg-emerald-500/12">
              <CheckCircle className="h-9 w-9 text-emerald-400" />
            </span>
            <div className="space-y-2">
              <h1 className="font-syne text-[22px] font-bold text-white">Request received</h1>
              <p className="text-sm leading-relaxed text-white/55">
                We&apos;re checking availability for{" "}
                <span className="font-medium text-white">{submitted.product_name}</span>.
                We&apos;ll reach out by phone or Telegram with an update.
              </p>
            </div>
            <div className="rounded-xl border border-white/8 bg-white/3 px-5 py-4 text-left space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-[10px] uppercase tracking-widest font-semibold text-[#b1bdb0]">
                  Status
                </span>
                <StatusChip status={submitted.status} />
              </div>
              {submitted.customer_visible_message && (
                <p className="text-sm text-white/70 pt-1">
                  {submitted.customer_visible_message}
                </p>
              )}
            </div>
            <div className="flex flex-col gap-3">
              <button
                onClick={() => {
                  setSubmitted(null);
                  setForm({
                    product_name: "",
                    strength: "",
                    form_type: "",
                    quantity: "",
                    urgency: "",
                    note: "",
                  });
                }}
                className="inline-flex items-center justify-center gap-2 rounded-xl bg-emerald-500 px-6 py-3.5 text-sm font-semibold text-black transition hover:bg-emerald-400"
              >
                <ClipboardList className="h-4 w-4" />
                Submit Another Request
              </button>
              <Link
                href="/requests"
                className="inline-flex items-center justify-center gap-2 rounded-xl border border-white/10 px-6 py-3.5 text-sm font-semibold text-white/70 transition hover:border-white/20 hover:text-white"
              >
                Track My Requests
              </Link>
            </div>
          </div>
        </div>
      </AppShell>
    );
  }

  return (
    <AppShell>
      <div className="space-y-6 px-5 pt-8 pb-6">

        {/* Header */}
        <div className="flex items-start gap-4">
          <Link
            href="/app"
            className="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-xl border border-white/10 bg-white/4 transition hover:border-white/20"
          >
            <ArrowLeft className="h-4 w-4 text-white/60" />
          </Link>
          <div>
            <div className="flex items-center gap-3 mb-1">
              <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-emerald-500/12 border border-emerald-500/20">
                <TabletIcon size={22} />
              </span>
              <h1 className="font-syne text-xl font-bold text-white">Find a Medicine</h1>
            </div>
            <p className="text-sm text-white/50">
              We&apos;ll check stock and contact you to confirm.
            </p>
          </div>
        </div>

        <form onSubmit={handleSubmit} noValidate className="space-y-4">

          {/* Card 1 - What are you looking for? */}
          <SectionCard label="What are you looking for?">
            <FieldWrap label="Product / Medicine Name" error={errors.product_name}>
              <Package className="h-4 w-4 shrink-0 text-[#b1bdb0]" />
              <input
                type="text"
                placeholder="e.g. Amoxicillin, Vitamin C, Panadol"
                value={form.product_name}
                onChange={(e) => setForm((f) => ({ ...f, product_name: e.target.value }))}
                className="flex-1 bg-transparent text-sm text-white placeholder-[#b1bdb0] outline-none"
                autoFocus
              />
            </FieldWrap>
            <div className="grid grid-cols-2 gap-3">
              <FieldWrap label="Strength" optional>
                <input
                  type="text"
                  placeholder="e.g. 500mg"
                  value={form.strength}
                  onChange={(e) => setForm((f) => ({ ...f, strength: e.target.value }))}
                  className="flex-1 bg-transparent text-sm text-white placeholder-[#b1bdb0] outline-none"
                />
              </FieldWrap>
              <FieldWrap label="Form" optional error={errors.form}>
                <input
                  type="text"
                  placeholder="e.g. Tablet"
                  value={form.form_type}
                  onChange={(e) => setForm((f) => ({ ...f, form_type: e.target.value }))}
                  className="flex-1 bg-transparent text-sm text-white placeholder-[#b1bdb0] outline-none"
                />
              </FieldWrap>
            </div>
            <FieldWrap label="Quantity" optional>
              <input
                type="text"
                placeholder="e.g. 2 packs, 1 bottle"
                value={form.quantity}
                onChange={(e) => setForm((f) => ({ ...f, quantity: e.target.value }))}
                className="flex-1 bg-transparent text-sm text-white placeholder-[#b1bdb0] outline-none"
              />
            </FieldWrap>
          </SectionCard>

          {/* Card 2 - Urgency chips */}
          <SectionCard label="How soon do you need it?">
            <div className="grid grid-cols-2 gap-2.5">
              {URGENCY_OPTIONS.map((opt) => (
                <button
                  key={opt.value}
                  type="button"
                  onClick={() =>
                    setForm((f) => ({
                      ...f,
                      urgency: f.urgency === opt.value ? "" : opt.value,
                    }))
                  }
                  className={[
                    "flex flex-col items-start rounded-xl border px-4 py-3 text-left transition-all",
                    form.urgency === opt.value
                      ? "border-emerald-500/50 bg-emerald-500/12"
                      : "border-white/10 bg-white/4 hover:border-white/20",
                  ].join(" ")}
                >
                  <span
                    className={[
                      "text-[13px] font-semibold",
                      form.urgency === opt.value ? "text-emerald-400" : "text-white/80",
                    ].join(" ")}
                  >
                    {opt.label}
                  </span>
                  <span className="mt-0.5 text-[11px] text-[#b1bdb0] leading-tight">
                    {opt.sub}
                  </span>
                </button>
              ))}
            </div>
          </SectionCard>

          {/* Card 3 - Notes */}
          <SectionCard label="Additional Details">
            <div className="rounded-xl border border-white/10 bg-white/4 px-4 py-3.5 transition-colors focus-within:border-emerald-500/50">
              <textarea
                rows={3}
                placeholder="Brand preference, diagnosis, any other details…"
                value={form.note}
                onChange={(e) => setForm((f) => ({ ...f, note: e.target.value }))}
                className="w-full resize-none bg-transparent text-sm text-white placeholder-[#b1bdb0] outline-none"
                maxLength={1000}
              />
            </div>
            <p className="text-[11px] text-[#b1bdb0]">
              Optional - helps us find the right product faster
            </p>
          </SectionCard>

          {errors.form_error && (
            <p className="rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400">
              {errors.form_error}
            </p>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full inline-flex items-center justify-center gap-2 rounded-xl bg-emerald-500 px-6 py-3.5 text-sm font-semibold text-black transition hover:bg-emerald-400 disabled:cursor-not-allowed disabled:opacity-60"
            style={{ minHeight: 52 }}
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

          <p className="text-center text-[11px] leading-relaxed text-[#b1bdb0]">
            A Peaceway pharmacist will review your request and contact you to confirm availability.
          </p>
        </form>
      </div>
    </AppShell>
  );
}
