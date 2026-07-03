"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import {
  CheckCircle,
  ChevronRight,
  Loader2,
  Mail,
  MapPin,
  Phone,
  User,
} from "lucide-react";
import { getMe, listZones, registerCustomer, type Zone } from "@/lib/api/customers";
import type { ApiError } from "@/lib/api";

type Field = "full_name" | "phone" | "email" | "delivery_area";
type Errors = Partial<Record<Field | "form", string>>;

function PeacewayMark() {
  return (
    <svg width="40" height="40" viewBox="0 0 40 40" fill="none" xmlns="http://www.w3.org/2000/svg">
      <circle cx="20" cy="20" r="18" fill="rgba(16,185,129,0.15)" stroke="#10b981" strokeWidth="1.8"/>
      <line x1="20" y1="8" x2="20" y2="32" stroke="#10b981" strokeWidth="2.2" strokeLinecap="round"/>
      <line x1="8" y1="20" x2="32" y2="20" stroke="#10b981" strokeWidth="2.2" strokeLinecap="round"/>
    </svg>
  );
}

function FieldGroup({
  label,
  optional,
  error,
  icon,
  children,
}: {
  label: string;
  optional?: boolean;
  error?: string;
  icon: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <div className="space-y-1.5">
      <label className="flex items-center gap-2 text-[10px] font-semibold uppercase tracking-widest text-white/40">
        {label}
        {optional && (
          <span className="rounded-full bg-white/8 px-1.5 py-px text-[9px] normal-case tracking-normal font-normal text-white/25">
            optional
          </span>
        )}
      </label>
      <div
        className={[
          "flex items-center gap-3 rounded-xl border px-4 py-3.5 transition-colors",
          "bg-white/4 backdrop-blur-sm",
          error
            ? "border-red-500/50 focus-within:border-red-400"
            : "border-white/10 focus-within:border-emerald-500/50",
        ].join(" ")}
      >
        <span className="shrink-0 text-white/30">{icon}</span>
        {children}
      </div>
      {error && <p className="pl-1 text-xs text-red-400">{error}</p>}
    </div>
  );
}

export default function StartPage() {
  const router = useRouter();
  const [zones, setZones] = useState<Zone[]>([]);
  const [form, setForm] = useState({
    full_name: "",
    phone: "",
    email: "",
    delivery_area: "",
  });
  const [errors, setErrors] = useState<Errors>({});
  const [loading, setLoading] = useState(false);
  const [done, setDone] = useState(false);
  const [customerName, setCustomerName] = useState("");
  const [checkingAuth, setCheckingAuth] = useState(true);

  useEffect(() => {
    getMe()
      .then(() => router.replace("/app"))
      .catch(() => setCheckingAuth(false));
    listZones().then(setZones).catch(() => {});
  }, [router]);

  function validate(): Errors {
    const e: Errors = {};
    if (!form.full_name.trim()) e.full_name = "Please enter your name.";
    if (!form.phone.trim()) e.phone = "Please enter your phone number.";
    else if (!/^\+?[\d\s\-().]{7,20}$/.test(form.phone.trim()))
      e.phone = "Enter a valid phone number.";
    if (form.email && !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(form.email.trim()))
      e.email = "Enter a valid email address.";
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
      const customer = await registerCustomer({
        full_name: form.full_name.trim(),
        phone: form.phone.trim(),
        email: form.email.trim() || undefined,
        delivery_area: form.delivery_area || undefined,
      });
      setCustomerName(customer.full_name ?? form.full_name.trim());
      setDone(true);
    } catch (err) {
      const apiErr = err as ApiError;
      setErrors({ form: apiErr?.detail ?? "Something went wrong. Please try again." });
    } finally {
      setLoading(false);
    }
  }

  if (checkingAuth) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-[#0b0c09]">
        <Loader2 className="h-6 w-6 animate-spin text-white/30" />
      </main>
    );
  }

  if (done) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-[#0b0c09] px-5 py-16">
        <div className="w-full max-w-md space-y-8 text-center">
          <div className="flex justify-center">
            <span className="inline-flex h-[72px] w-[72px] items-center justify-center rounded-full border border-emerald-500/30 bg-emerald-500/12">
              <CheckCircle className="h-9 w-9 text-emerald-400" />
            </span>
          </div>
          <div className="space-y-2.5">
            <h1 className="font-syne text-[26px] font-bold text-white">
              Welcome, {customerName.split(" ")[0]}.
            </h1>
            <p className="text-sm leading-relaxed text-white/55">
              You&apos;re registered with Peaceway Online. We&apos;ll reach out on Telegram or by phone to confirm your first order.
            </p>
          </div>
          <div className="flex flex-col gap-3">
            <Link
              href="/app"
              className="inline-flex items-center justify-center gap-2 rounded-xl bg-emerald-500 px-6 py-3.5 text-sm font-semibold text-black transition hover:bg-emerald-400"
            >
              Open the Web App
              <ChevronRight className="h-4 w-4" />
            </Link>
            <a
              href="https://t.me/Peacewayonline_bot"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center justify-center gap-2 rounded-xl border border-white/10 px-6 py-3.5 text-sm font-semibold text-white/70 transition hover:border-white/20 hover:text-white"
            >
              Order on Telegram
            </a>
          </div>
        </div>
      </main>
    );
  }

  return (
    <main className="flex min-h-screen items-start justify-center bg-[#0b0c09] px-5 py-12">
      <div className="w-full max-w-md space-y-8">

        {/* Brand mark */}
        <div className="flex flex-col items-center gap-3 pt-4 text-center">
          <PeacewayMark />
          <div>
            <p className="font-syne text-lg font-bold text-white">Peaceway Online</p>
            <p className="text-xs text-white/40">Igando · Lagos · Licensed Pharmacy</p>
          </div>
        </div>

        {/* Form card */}
        <div className="rounded-2xl border border-white/8 bg-white/[0.03] px-6 py-7 space-y-6">
          <div className="space-y-1.5">
            <p className="text-[10px] font-semibold uppercase tracking-widest text-emerald-400">
              Get Started
            </p>
            <h1 className="font-syne text-2xl font-bold leading-tight text-white">
              Tell us how to reach you.
            </h1>
            <p className="text-sm leading-relaxed text-white/50">
              We use your details to confirm orders and send updates. No spam.
            </p>
            <p className="text-xs text-white/30">
              Already registered? Enter your phone number to sign back in.
            </p>
          </div>

          <form onSubmit={handleSubmit} noValidate className="space-y-4">
            <FieldGroup
              label="Full Name"
              icon={<User className="h-4 w-4" />}
              error={errors.full_name}
            >
              <input
                type="text"
                placeholder="e.g. Amaka Johnson"
                value={form.full_name}
                onChange={(e) => setForm((f) => ({ ...f, full_name: e.target.value }))}
                className="flex-1 bg-transparent text-sm text-white placeholder-white/25 outline-none"
                autoComplete="name"
              />
            </FieldGroup>

            <FieldGroup
              label="Phone Number"
              icon={<Phone className="h-4 w-4" />}
              error={errors.phone}
            >
              <input
                type="tel"
                placeholder="e.g. 08012345678"
                value={form.phone}
                onChange={(e) => setForm((f) => ({ ...f, phone: e.target.value }))}
                className="flex-1 bg-transparent text-sm text-white placeholder-white/25 outline-none"
                autoComplete="tel"
              />
            </FieldGroup>

            <FieldGroup
              label="Email Address"
              optional
              icon={<Mail className="h-4 w-4" />}
              error={errors.email}
            >
              <input
                type="email"
                placeholder="For receipts and updates"
                value={form.email}
                onChange={(e) => setForm((f) => ({ ...f, email: e.target.value }))}
                className="flex-1 bg-transparent text-sm text-white placeholder-white/25 outline-none"
                autoComplete="email"
              />
            </FieldGroup>

            <FieldGroup
              label="Delivery Area"
              optional
              icon={<MapPin className="h-4 w-4" />}
              error={errors.delivery_area}
            >
              <select
                value={form.delivery_area}
                onChange={(e) => setForm((f) => ({ ...f, delivery_area: e.target.value }))}
                className="flex-1 bg-transparent text-sm text-white outline-none appearance-none [&>option]:bg-[#0b0c09]"
              >
                <option value="">Select your area…</option>
                {zones.map((z) => (
                  <option key={z.id} value={z.name}>
                    {z.name} · ₦{z.fee.toLocaleString()}
                    {z.eta_minutes ? ` · ~${z.eta_minutes}min` : ""}
                  </option>
                ))}
              </select>
            </FieldGroup>

            {errors.form && (
              <p className="rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400">
                {errors.form}
              </p>
            )}

            <button
              type="submit"
              disabled={loading}
              className="mt-2 inline-flex w-full items-center justify-center gap-2 rounded-xl bg-emerald-500 px-6 py-3.5 text-sm font-semibold text-black transition hover:bg-emerald-400 disabled:cursor-not-allowed disabled:opacity-60"
              style={{ minHeight: 52 }}
            >
              {loading ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Saving…
                </>
              ) : (
                <>
                  Continue
                  <ChevronRight className="h-4 w-4" />
                </>
              )}
            </button>

            <p className="text-center text-[11px] leading-relaxed text-white/30">
              By continuing you agree that Peaceway may contact you by phone or Telegram to process your request.
            </p>
          </form>
        </div>

        <div className="text-center">
          <Link href="/" className="text-xs text-white/30 transition hover:text-white/60">
            ← Back to home
          </Link>
        </div>
      </div>
    </main>
  );
}
