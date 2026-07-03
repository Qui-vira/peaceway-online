"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { CheckCircle, Loader2, LogOut, Mail, MapPin, Phone, User } from "lucide-react";
import {
  getMe,
  formatZoneOption,
  listZones,
  logout,
  updateProfile,
  type CustomerProfile,
  type Zone,
} from "@/lib/api/customers";
import type { ApiError } from "@/lib/api";
import { AppShell } from "@/components/app/app-shell";
import { GuestWall, SectionLabel, Spinner } from "@/components/app/ui";

function FieldShell({
  icon,
  children,
}: {
  icon: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <div className="flex min-w-0 items-center gap-3 rounded-xl border border-white/10 bg-white/4 px-4 py-3.5 backdrop-blur-sm transition-colors focus-within:border-emerald-500/50">
      <span className="shrink-0 text-white/30">{icon}</span>
      {children}
    </div>
  );
}

function Label({ children }: { children: React.ReactNode }) {
  return (
    <label className="mb-2 block text-[10px] font-semibold uppercase tracking-widest text-white/40">
      {children}
    </label>
  );
}

export default function ProfilePage() {
  const router = useRouter();
  const [me, setMe] = useState<CustomerProfile | null>(null);
  const [zones, setZones] = useState<Zone[]>([]);
  const [guest, setGuest] = useState(false);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [signingOut, setSigningOut] = useState(false);
  const [error, setError] = useState("");

  const [form, setForm] = useState({ full_name: "", email: "", delivery_area: "" });

  useEffect(() => {
    Promise.all([getMe(), listZones().catch(() => [] as Zone[])])
      .then(([profile, zoneList]) => {
        setMe(profile);
        setZones(zoneList);
        setForm({
          full_name: profile.full_name ?? "",
          email: profile.email ?? "",
          delivery_area: profile.delivery_area ?? "",
        });
      })
      .catch(() => setGuest(true))
      .finally(() => setLoading(false));
  }, []);

  async function handleSignOut() {
    setSigningOut(true);
    try {
      await logout();
    } catch {
      // drop session view even if network call fails
    }
    router.push("/");
  }

  async function handleSave(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setSaved(false);
    setError("");
    try {
      const updated = await updateProfile({
        full_name: form.full_name.trim() || undefined,
        email: form.email.trim() || undefined,
        delivery_area: form.delivery_area || undefined,
      });
      setMe(updated);
      setSaved(true);
      setTimeout(() => setSaved(false), 2500);
    } catch (err) {
      const apiErr = err as ApiError;
      setError(apiErr?.detail ?? "Could not save. Please try again.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <AppShell>
      <div className="space-y-6 px-5 pt-10 pb-8">

        {loading && <Spinner />}
        {guest && <GuestWall />}

        {me && !loading && (
          <>
            {/* Avatar section */}
            <div className="flex flex-col items-center gap-3 py-4 text-center">
              <div className="flex h-16 w-16 items-center justify-center rounded-full border border-emerald-500/30 bg-emerald-500/15">
                <span className="font-syne text-[26px] font-bold text-emerald-400">
                  {(me.full_name ?? "?").charAt(0).toUpperCase()}
                </span>
              </div>
              <div className="space-y-0.5">
                <p className="text-lg font-bold text-white">{me.full_name ?? "Your Profile"}</p>
                {me.phone && (
                  <p className="text-sm text-white/45">{me.phone}</p>
                )}
                {me.delivery_area && (
                  <p className="text-xs text-white/35">{me.delivery_area}</p>
                )}
              </div>
            </div>

            {/* Divider */}
            <div className="h-px bg-white/6" />

            {/* Edit form */}
            <form onSubmit={handleSave} className="space-y-6">
              <div className="space-y-4">
                <SectionLabel>Edit Your Details</SectionLabel>

                <div>
                  <Label>Full Name</Label>
                  <FieldShell icon={<User className="h-4 w-4" />}>
                    <input
                      type="text"
                      value={form.full_name}
                      onChange={(e) => setForm((f) => ({ ...f, full_name: e.target.value }))}
                      className="flex-1 bg-transparent text-sm text-white placeholder-white/25 outline-none"
                      autoComplete="name"
                    />
                  </FieldShell>
                </div>

                <div>
                  <Label>Phone Number</Label>
                  <FieldShell icon={<Phone className="h-4 w-4" />}>
                    <span className="flex-1 text-sm text-white/50">{me.phone ?? "Not set"}</span>
                  </FieldShell>
                  <p className="mt-1.5 pl-1 text-xs text-white/30">
                    Phone is your login. Contact us to change it.
                  </p>
                </div>

                <div>
                  <Label>Email Address</Label>
                  <FieldShell icon={<Mail className="h-4 w-4" />}>
                    <input
                      type="email"
                      placeholder="For receipts and updates"
                      value={form.email}
                      onChange={(e) => setForm((f) => ({ ...f, email: e.target.value }))}
                      className="flex-1 bg-transparent text-sm text-white placeholder-white/25 outline-none"
                      autoComplete="email"
                    />
                  </FieldShell>
                </div>

                <div>
                  <Label>Delivery Area</Label>
                  <FieldShell icon={<MapPin className="h-4 w-4" />}>
                    <select
                      value={form.delivery_area}
                      onChange={(e) => setForm((f) => ({ ...f, delivery_area: e.target.value }))}
                      className="min-w-0 flex-1 appearance-none bg-transparent pr-2 text-sm text-white outline-none [&>option]:bg-[#0b0c09] [&>option]:text-white"
                    >
                      <option value="">Select your area…</option>
                      {form.delivery_area &&
                        !zones.some((z) => z.name === form.delivery_area) && (
                          <option value={form.delivery_area}>{form.delivery_area}</option>
                        )}
                      {zones.map((z) => (
                        <option key={z.id} value={z.name}>
                          {formatZoneOption(z)}
                        </option>
                      ))}
                    </select>
                  </FieldShell>
                </div>
              </div>

              {error && (
                <p className="rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400">
                  {error}
                </p>
              )}

              <button
                type="submit"
                disabled={saving}
                className="inline-flex w-full items-center justify-center gap-2 rounded-xl bg-emerald-500 px-6 py-3.5 text-sm font-semibold text-black transition hover:bg-emerald-400 disabled:cursor-not-allowed disabled:opacity-60"
                style={{ minHeight: 52 }}
              >
                {saving ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Saving…
                  </>
                ) : saved ? (
                  <>
                    <CheckCircle className="h-4 w-4" />
                    Saved
                  </>
                ) : (
                  "Save Changes"
                )}
              </button>
            </form>

            {/* Divider */}
            <div className="h-px bg-white/6" />

            {/* Quick links */}
            <div className="space-y-3">
              <SectionLabel>More</SectionLabel>
              {[
                { href: "/prescription", label: "Upload Prescription", sub: "Send a script for review" },
                { href: "/orders", label: "My Orders", sub: "Track your deliveries" },
                { href: "/referral", label: "Refer a Friend", sub: "Earn ₦200 per referral" },
                { href: "/track", label: "Track an Order", sub: "No account needed" },
              ].map((link) => (
                <a
                  key={link.href}
                  href={link.href}
                  className="flex items-center justify-between rounded-xl border border-white/8 bg-white/3 px-4 py-3.5 transition hover:border-white/15"
                >
                  <div>
                    <p className="text-[13px] font-medium text-white">{link.label}</p>
                    <p className="text-[11px] text-white/40">{link.sub}</p>
                  </div>
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="rgba(255,255,255,0.25)" strokeWidth="2"><polyline points="9 18 15 12 9 6"/></svg>
                </a>
              ))}
            </div>

            {/* Account section */}
            <div className="space-y-4">
              <SectionLabel>Account</SectionLabel>

              <button
                type="button"
                onClick={handleSignOut}
                disabled={signingOut}
                className="inline-flex w-full items-center justify-center gap-2 rounded-xl border border-red-500/25 px-6 py-3.5 text-sm font-semibold text-red-400 transition hover:border-red-500/50 hover:bg-red-500/8 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {signingOut ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <LogOut className="h-4 w-4" />
                )}
                Sign Out
              </button>

              <p className="text-center text-[11px] leading-relaxed text-white/30">
                Signing out ends your session on this device. Your requests and profile stay safe
                and come back when you sign in with your phone number again.
              </p>
            </div>
          </>
        )}
      </div>
    </AppShell>
  );
}
