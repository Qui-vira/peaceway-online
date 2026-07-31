"use client";

import { Suspense, useEffect, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import {
  CheckCircle,
  ChevronRight,
  Loader2,
  Mail,
  Phone,
  User,
} from "lucide-react";
import { getMe, invalidateMeCache } from "@/lib/api/customers";
import { sendOtp, verifyOtp } from "@/lib/api/otp";
import { clearReferral, readReferral } from "@/lib/referral";
import { OtpInput } from "@/components/app/otp-input";
import { TactileButton, TactileLink } from "@/components/app/tactile-button";
import type { ApiError } from "@/lib/api";
import { usePageTitle } from "@/components/app/page-title";

type Tab = "signup" | "login";

type FormErrors = Partial<Record<"full_name" | "phone" | "email" | "form", string>>;

function PeacewayMark() {
  return (
    <svg width="40" height="40" viewBox="0 0 40 40" fill="none" xmlns="http://www.w3.org/2000/svg">
      <circle cx="20" cy="20" r="18" fill="rgba(52,217,138,0.15)" stroke="#34d98a" strokeWidth="1.8"/>
      <line x1="20" y1="8" x2="20" y2="32" stroke="#34d98a" strokeWidth="2.2" strokeLinecap="round"/>
      <line x1="8" y1="20" x2="32" y2="20" stroke="#34d98a" strokeWidth="2.2" strokeLinecap="round"/>
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
      <label className="flex items-center gap-2 text-[11px] font-semibold uppercase tracking-widest text-[#b1bdb0]">
        {label}
        {optional && (
          <span className="rounded-full bg-white/8 px-1.5 py-px text-[11px] normal-case tracking-normal font-normal text-[#b1bdb0]">
            optional
          </span>
        )}
      </label>
      <div
        className={[
          "flex min-w-0 items-center gap-3 rounded-xl border px-4 py-3.5 transition-colors",
          "bg-white/4 backdrop-blur-sm",
          error
            ? "border-red-500/50 focus-within:border-red-400"
            : "border-white/10 focus-within:border-emerald-500/50",
        ].join(" ")}
      >
        <span className="shrink-0 text-[#b1bdb0]">{icon}</span>
        {children}
      </div>
      {error && <p className="pl-1 text-xs text-red-400">{error}</p>}
    </div>
  );
}

/**
 * Where to send someone after they sign in.
 *
 * Allowlisted rather than "any path starting with /": `next` arrives from the
 * URL, so an unchecked value is an open redirect, and a protocol-relative
 * "//evil.example" is a path by the naive test.
 */
const NEXT_ALLOWED = [
  "/app",
  "/cart",
  "/checkout",
  "/orders",
  "/prescription",
  "/profile",
  "/referral",
  "/reminders",
  "/reminders/new",
  "/request",
  "/requests",
  "/shop",
  "/ask-pharmacist",
] as const;

function safeNext(raw: string | null): string {
  if (!raw) return "/app";
  return (NEXT_ALLOWED as readonly string[]).includes(raw) ? raw : "/app";
}

function StartPageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  // Carries the destination through the sign-in round trip. Without it,
  // "Proceed to Checkout" while signed out sent the customer to a registration
  // form and then dropped them on the home screen, cart intact but forgotten.
  const next = safeNext(searchParams.get("next"));

  // Auth check
  const [checkingAuth, setCheckingAuth] = useState(true);

  // Tab / step
  const [tab, setTab] = useState<Tab>("signup");
  const [step, setStep] = useState<1 | 2>(1);

  // Step 1 form
  const [form, setForm] = useState({ full_name: "", phone: "", email: "" });
  const [formErrors, setFormErrors] = useState<FormErrors>({});

  // Step 2 OTP
  const [otp, setOtp] = useState("      ");
  const [emailHint, setEmailHint] = useState("");
  const [otpError, setOtpError] = useState("");

  // Shared
  const [loading, setLoading] = useState(false);
  const [done, setDone] = useState(false);
  const [customerName, setCustomerName] = useState("");

  // Resend countdown
  const [resendCooldown, setResendCooldown] = useState(0);
  const countdownRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    getMe()
      .then(() => router.replace(next))
      .catch(() => setCheckingAuth(false));
  }, [router, next]);

  useEffect(() => {
    if (resendCooldown <= 0) {
      if (countdownRef.current) {
        clearInterval(countdownRef.current);
        countdownRef.current = null;
      }
      return;
    }
    countdownRef.current = setInterval(() => {
      setResendCooldown((c) => {
        if (c <= 1) {
          clearInterval(countdownRef.current!);
          countdownRef.current = null;
          return 0;
        }
        return c - 1;
      });
    }, 1000);
    return () => {
      if (countdownRef.current) clearInterval(countdownRef.current);
    };
  }, [resendCooldown]);

  function updateField(field: keyof typeof form, value: string) {
    setForm((f) => ({ ...f, [field]: value }));
    setFormErrors((e) => {
      const { form: _f, [field]: _field, ...rest } = e;
      return rest;
    });
  }

  function switchTab(t: Tab) {
    setTab(t);
    setStep(1);
    setForm({ full_name: "", phone: "", email: "" });
    setFormErrors({});
    setOtp("      ");
    setOtpError("");
  }

  function validateStep1(): FormErrors {
    const e: FormErrors = {};
    if (tab === "signup") {
      if (!form.full_name.trim()) e.full_name = "Please enter your full name.";
    }
    if (!form.phone.trim()) {
      e.phone = "Please enter your phone number.";
    } else if (!/^\+?[\d\s\-().]{7,20}$/.test(form.phone.trim())) {
      e.phone = "Enter a valid phone number.";
    }
    if (tab === "signup") {
      if (!form.email.trim()) {
        e.email = "Please enter your email address.";
      } else if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(form.email.trim())) {
        e.email = "Enter a valid email address.";
      }
    }
    return e;
  }

  async function handleSendOtp(e: React.FormEvent) {
    e.preventDefault();
    const errs = validateStep1();
    if (Object.keys(errs).length) {
      setFormErrors(errs);
      return;
    }
    setFormErrors({});
    setLoading(true);
    try {
      const res = await sendOtp({
        phone: form.phone.trim(),
        email: tab === "signup" ? form.email.trim() : undefined,
        full_name: tab === "signup" ? form.full_name.trim() : undefined,
        mode: tab,
      });
      setEmailHint(res.email_hint);
      setOtp("      ");
      setOtpError("");
      setStep(2);
      setResendCooldown(30);
    } catch (err) {
      const apiErr = err as ApiError;
      const msg =
        apiErr?.detail ?? "We couldn't send your code. Please check the details and try again.";
      setFormErrors({ form: msg });
    } finally {
      setLoading(false);
    }
  }

  async function handleVerifyOtp() {
    setOtpError("");
    setLoading(true);
    try {
      invalidateMeCache();
      const customer = await verifyOtp({
        phone: form.phone.trim(),
        code: otp.replace(/\s/g, ""),
        // Only meaningful on signup, and the server ignores it for an existing
        // customer - but sending it unconditionally keeps the call site honest.
        referral_code: readReferral() ?? undefined,
      });
      // Attribution is recorded server-side now; holding the code would only
      // mean re-sending it on a future sign-in.
      clearReferral();
      if (tab === "signup") {
        setCustomerName(customer.full_name ?? form.full_name.trim());
        setDone(true);
      } else {
        router.replace(next);
      }
    } catch (err) {
      const apiErr = err as ApiError;
      setOtpError(apiErr?.detail ?? "Invalid code. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  async function handleResend() {
    setLoading(true);
    setOtpError("");
    setOtp("      ");
    try {
      const res = await sendOtp({
        phone: form.phone.trim(),
        email: tab === "signup" ? form.email.trim() : undefined,
        full_name: tab === "signup" ? form.full_name.trim() : undefined,
        mode: tab,
      });
      setEmailHint(res.email_hint);
      setResendCooldown(30);
    } catch (err) {
      const apiErr = err as ApiError;
      setOtpError(apiErr?.detail ?? "Could not resend code. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  if (checkingAuth) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-[#0b0c09]">
        <Loader2 className="h-6 w-6 animate-spin text-[#b1bdb0]" />
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
            {/* 24, not 26: DESIGN.md's ramp is 11·12·13·14·16·19·24·32·46·76. */}
            <h1 className="font-syne text-[24px] font-bold text-white">
              Welcome, {customerName.split(" ")[0]}.
            </h1>
            {/* Someone who came here from a full cart is mid-purchase; telling
                them the pharmacy will call to confirm an order they have not
                placed yet is both wrong and a reason to stop. Say what happens
                next for the thing they were actually doing. */}
            <p className="text-sm leading-relaxed text-white/55">
              {next === "/checkout"
                ? "You're registered. Your cart is waiting — let's finish your order."
                : "You're registered with Peaceway Online. We'll reach out on Telegram or by phone to confirm your first order."}
            </p>
          </div>
          <div className="flex flex-col gap-3">
            <TactileLink href={next}>
              {next === "/checkout" ? "Back to Checkout" : "Open the Web App"}
              <ChevronRight className="h-4 w-4" />
            </TactileLink>
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
    <main className="flex min-h-svh items-center justify-center bg-[#0b0c09] px-5 py-10">
      <div className="w-full max-w-md space-y-6">

        {/* Brand mark */}
        <div className="flex flex-col items-center gap-3 text-center">
          <PeacewayMark />
          <div>
            <p className="font-syne text-lg font-bold text-white">Peaceway Online</p>
            <p className="text-xs text-[#b1bdb0]">Igando · Lagos · Licensed Pharmacy</p>
          </div>
        </div>

        {/* Card */}
        <div className="rounded-2xl border border-white/8 bg-white/[0.04] px-5 py-6 shadow-2xl shadow-black/30 space-y-5 sm:px-6 sm:py-7 sm:space-y-6">

          {/* Tab switcher */}
          <div className="flex rounded-xl bg-white/5 p-1">
            <button
              type="button"
              onClick={() => switchTab("signup")}
              className={[
                "flex-1 rounded-lg py-2 text-sm font-medium transition",
                tab === "signup"
                  ? "bg-emerald-500 text-black font-semibold shadow"
                  : "text-white/50 hover:text-white/70",
              ].join(" ")}
            >
              Create Account
            </button>
            <button
              type="button"
              onClick={() => switchTab("login")}
              className={[
                "flex-1 rounded-lg py-2 text-sm font-medium transition",
                tab === "login"
                  ? "bg-emerald-500 text-black font-semibold shadow"
                  : "text-white/50 hover:text-white/70",
              ].join(" ")}
            >
              Sign In
            </button>
          </div>

          {/* Step 1: Form */}
          {step === 1 && (
            <form onSubmit={handleSendOtp} noValidate className="space-y-4">
              <div className="space-y-1">
                <p className="text-[11px] font-semibold uppercase tracking-widest text-emerald-400">
                  {tab === "signup" ? "Get Started" : "Welcome Back"}
                </p>
                <h1 className="font-syne text-2xl font-bold leading-tight text-white">
                  {tab === "signup" ? "Create your account." : "Welcome back."}
                </h1>
                <p className="text-sm leading-relaxed text-white/50">
                  {tab === "signup"
                    ? "Enter your details and we'll send you a verification code."
                    : "Enter your phone number and we'll send you a verification code."}
                </p>
              </div>

              <div className="space-y-3.5">
                {tab === "signup" && (
                  <FieldGroup
                    label="Full Name"
                    icon={<User className="h-4 w-4" />}
                    error={formErrors.full_name}
                  >
                    <input
                      type="text"
                      placeholder="e.g. Amaka Johnson"
                      value={form.full_name}
                      onChange={(e) => updateField("full_name", e.target.value)}
                      className="flex-1 bg-transparent text-base text-white placeholder-[#b1bdb0] outline-none"
                      autoComplete="name"
                    />
                  </FieldGroup>
                )}

                <FieldGroup
                  label="Phone Number"
                  icon={<Phone className="h-4 w-4" />}
                  error={formErrors.phone}
                >
                  <input
                    type="tel"
                    placeholder="e.g. 08012345678"
                    value={form.phone}
                    onChange={(e) => updateField("phone", e.target.value)}
                    className="flex-1 bg-transparent text-base text-white placeholder-[#b1bdb0] outline-none"
                    autoComplete="tel"
                  />
                </FieldGroup>

                {tab === "signup" && (
                  <FieldGroup
                    label="Email Address"
                    icon={<Mail className="h-4 w-4" />}
                    error={formErrors.email}
                  >
                    <input
                      type="email"
                      placeholder="For your verification code"
                      value={form.email}
                      onChange={(e) => updateField("email", e.target.value)}
                      className="flex-1 bg-transparent text-base text-white placeholder-[#b1bdb0] outline-none"
                      autoComplete="email"
                    />
                  </FieldGroup>
                )}
              </div>

              {formErrors.form && (
                <p className="rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400">
                  {formErrors.form}
                </p>
              )}

              <TactileButton
                type="submit"
                disabled={loading}
                className="mt-1 w-full min-h-[52px] disabled:cursor-not-allowed disabled:opacity-60"
              >
                {loading ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Sending…
                  </>
                ) : (
                  <>
                    Send Verification Code
                    <ChevronRight className="h-4 w-4" />
                  </>
                )}
              </TactileButton>
            </form>
          )}

          {/* Step 2: OTP */}
          {step === 2 && (
            <div className="space-y-5">
              <div className="space-y-1">
                <p className="text-[11px] font-semibold uppercase tracking-widest text-emerald-400">
                  Verify Email
                </p>
                <h1 className="font-syne text-2xl font-bold leading-tight text-white">
                  Check your email.
                </h1>
                <p className="text-sm leading-relaxed text-white/50">
                  Enter the 6-digit code we sent to{" "}
                  <span className="font-medium text-white">{emailHint}</span>
                </p>
              </div>

              <OtpInput value={otp} onChange={setOtp} disabled={loading} />

              {otpError && (
                <p className="rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400">
                  {otpError}
                </p>
              )}

              {/* Resend */}
              <div className="text-center">
                {resendCooldown > 0 ? (
                  <p className="text-xs text-[#b1bdb0]">
                    Resend in {resendCooldown}s
                  </p>
                ) : (
                  <button
                    type="button"
                    onClick={handleResend}
                    disabled={loading}
                    className="text-xs text-emerald-400 transition hover:text-emerald-300 disabled:opacity-50"
                  >
                    Resend code
                  </button>
                )}
              </div>

              <TactileButton
                type="button"
                onClick={handleVerifyOtp}
                disabled={otp.trim().length < 6 || loading}
                className="w-full min-h-[52px] disabled:cursor-not-allowed disabled:opacity-60"
              >
                {loading ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Verifying…
                  </>
                ) : (
                  "Verify →"
                )}
              </TactileButton>

              <button
                type="button"
                onClick={() => {
                  setStep(1);
                  setOtp("      ");
                  setOtpError("");
                  setResendCooldown(0);
                }}
                className="flex w-full items-center justify-center text-xs text-[#b1bdb0] transition hover:text-white/70"
              >
                ← Back
              </button>
            </div>
          )}
        </div>

        <div className="text-center">
          {/* Every route into /start comes from the app - the dashboard, the
              GuestWall, or /track - so "home" here is the app, not the
              marketing landing. */}
          <Link href="/app" className="text-xs text-[#b1bdb0] transition hover:text-white/60">
            ← Back to home
          </Link>
        </div>
      </div>
    </main>
  );
}

/**
 * `useSearchParams` opts a statically-rendered page into client rendering, and
 * Next requires the boundary to say so explicitly. Same shape as /track.
 */
export default function StartPage() {
  usePageTitle("Sign in");
  return (
    <Suspense fallback={<div className="min-h-svh bg-[#0b0c09]" />}>
      <StartPageContent />
    </Suspense>
  );
}
