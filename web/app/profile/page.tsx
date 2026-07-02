"use client";

import { useEffect, useState } from "react";
import { CheckCircle, Loader2, Mail, MapPin, Phone, User } from "lucide-react";
import {
  getMe,
  listZones,
  updateProfile,
  type CustomerProfile,
  type Zone,
} from "@/lib/api/customers";
import type { ApiError } from "@/lib/api";
import { AppShell, AppHeader } from "@/components/app/app-shell";
import { GuestWall, Spinner } from "@/components/app/ui";

function FieldShell({
  icon,
  children,
}: {
  icon: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <div className="flex items-center gap-3 rounded-xl border border-white/10 bg-white/4 px-4 py-3.5 backdrop-blur-sm transition-colors focus-within:border-emerald-500/60">
      <span className="shrink-0 text-white/30">{icon}</span>
      {children}
    </div>
  );
}

function Label({ children }: { children: React.ReactNode }) {
  return (
    <label className="mb-2 block text-xs font-semibold uppercase tracking-widest text-white/40">
      {children}
    </label>
  );
}

export default function ProfilePage() {
  const [me, setMe] = useState<CustomerProfile | null>(null);
  const [zones, setZones] = useState<Zone[]>([]);
  const [guest, setGuest] = useState(false);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
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
      <AppHeader title="My Profile" subtitle="Keep your contact details up to date." />

      {loading && <Spinner />}
      {guest && <GuestWall />}

      {me && !loading && (
        <form onSubmit={handleSave} className="space-y-4 px-5">
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
              <span className="flex-1 text-sm text-white/55">{me.phone ?? "—"}</span>
            </FieldShell>
            <p className="mt-1.5 pl-1 text-xs text-white/30">
              Phone is your login — contact us to change it.
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
                className="flex-1 appearance-none bg-transparent text-sm text-white outline-none [&>option]:bg-[#0b0c09]"
              >
                <option value="">Select your area…</option>
                {form.delivery_area &&
                  !zones.some((z) => z.name === form.delivery_area) && (
                    <option value={form.delivery_area}>{form.delivery_area}</option>
                  )}
                {zones.map((z) => (
                  <option key={z.id} value={z.name}>
                    {z.name} — ₦{z.fee.toLocaleString()}
                  </option>
                ))}
              </select>
            </FieldShell>
          </div>

          {error && (
            <p className="rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400">
              {error}
            </p>
          )}

          <button
            type="submit"
            disabled={saving}
            className="mt-2 inline-flex w-full items-center justify-center gap-2 rounded-xl bg-emerald-500 px-6 py-3.5 text-sm font-semibold text-black transition hover:bg-emerald-400 disabled:cursor-not-allowed disabled:opacity-60"
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
      )}
    </AppShell>
  );
}
