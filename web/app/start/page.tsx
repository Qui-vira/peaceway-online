"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { CheckCircle, ChevronRight, Loader2, MapPin, Phone, User, Mail } from "lucide-react";
import { listZones, registerCustomer, type Zone } from "@/lib/api/customers";
import type { ApiError } from "@/lib/api";

type Field = "full_name" | "phone" | "email" | "delivery_area";
type Errors = Partial<Record<Field | "form", string>>;

function Label({ children }: { children: React.ReactNode }) {
  return (
    <label className="block text-xs font-semibold uppercase tracking-widest text-white/40 mb-2">
      {children}
    </label>
  );
}

function InputRow({
  icon,
  error,
  children,
}: {
  icon: React.ReactNode;
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
        <span className="shrink-0 text-white/30">{icon}</span>
        {children}
      </div>
      {error && <p className="text-xs text-red-400 pl-1">{error}</p>}
    </div>
  );
}

export default function StartPage() {
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

  useEffect(() => {
    listZones().then(setZones).catch(() => {});
  }, []);

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

  if (done) {
    return (
      <main className="min-h-screen flex items-center justify-center px-5 py-20">
        <div className="w-full max-w-md text-center space-y-6">
          <div className="flex justify-center">
            <span className="inline-flex h-16 w-16 items-center justify-center rounded-full bg-emerald-500/15 border border-emerald-500/30">
              <CheckCircle className="h-8 w-8 text-emerald-400" />
            </span>
          </div>
          <div className="space-y-2">
            <h1 className="text-2xl font-bold text-white">
              Welcome, {customerName.split(" ")[0]}.
            </h1>
            <p className="text-white/55 text-sm leading-relaxed">
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
    <main className="min-h-screen flex items-start justify-center px-5 py-20">
      <div className="w-full max-w-md space-y-8">

        {/* Header */}
        <div className="space-y-2">
          <p className="text-xs font-semibold uppercase tracking-widest text-emerald-400">
            Peaceway Online · Get Started
          </p>
          <h1 className="text-3xl font-bold text-white leading-tight">
            Tell us how to reach you.
          </h1>
          <p className="text-white/50 text-sm leading-relaxed">
            We use your details to confirm orders, answer pharmacist questions, and send delivery updates. No spam.
          </p>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} noValidate className="space-y-4">

          <div>
            <Label>Full Name *</Label>
            <InputRow icon={<User className="h-4 w-4" />} error={errors.full_name}>
              <input
                type="text"
                placeholder="e.g. Amaka Johnson"
                value={form.full_name}
                onChange={(e) => setForm((f) => ({ ...f, full_name: e.target.value }))}
                className="flex-1 bg-transparent text-sm text-white placeholder-white/25 outline-none"
                autoComplete="name"
              />
            </InputRow>
          </div>

          <div>
            <Label>Phone Number *</Label>
            <InputRow icon={<Phone className="h-4 w-4" />} error={errors.phone}>
              <input
                type="tel"
                placeholder="e.g. 08012345678"
                value={form.phone}
                onChange={(e) => setForm((f) => ({ ...f, phone: e.target.value }))}
                className="flex-1 bg-transparent text-sm text-white placeholder-white/25 outline-none"
                autoComplete="tel"
              />
            </InputRow>
          </div>

          <div>
            <Label>Email Address (optional)</Label>
            <InputRow icon={<Mail className="h-4 w-4" />} error={errors.email}>
              <input
                type="email"
                placeholder="For order receipts and updates"
                value={form.email}
                onChange={(e) => setForm((f) => ({ ...f, email: e.target.value }))}
                className="flex-1 bg-transparent text-sm text-white placeholder-white/25 outline-none"
                autoComplete="email"
              />
            </InputRow>
          </div>

          <div>
            <Label>Delivery Area (optional)</Label>
            <InputRow icon={<MapPin className="h-4 w-4" />} error={errors.delivery_area}>
              <select
                value={form.delivery_area}
                onChange={(e) => setForm((f) => ({ ...f, delivery_area: e.target.value }))}
                className="flex-1 bg-transparent text-sm text-white outline-none appearance-none [&>option]:bg-[#0b0c09]"
              >
                <option value="">Select your area…</option>
                {zones.map((z) => (
                  <option key={z.id} value={z.name}>
                    {z.name} — ₦{z.fee.toLocaleString()}
                    {z.eta_minutes ? ` · ~${z.eta_minutes}min` : ""}
                  </option>
                ))}
              </select>
            </InputRow>
          </div>

          {errors.form && (
            <p className="rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400">
              {errors.form}
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
                Saving…
              </>
            ) : (
              <>
                Continue
                <ChevronRight className="h-4 w-4" />
              </>
            )}
          </button>

          <p className="text-center text-xs text-white/30 leading-relaxed pt-1">
            By continuing you agree that Peaceway may contact you by phone or Telegram to process your request.
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
