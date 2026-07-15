"use client";

import { useEffect, useState } from "react";
import { RefreshCcw, ShieldAlert, UserPlus } from "lucide-react";
import { AdminFetchError, adminFetch, getAdminToken } from "@/lib/admin-auth";
import { Button, PageHeader } from "@/components/app/ui";

type PartnerRow = {
  id: string;
  key: string;
  name: string;
  partner_type: string;
  channel_type: string;
  portal_login_email: string | null;
  portal_contact: string | null;
  is_active: boolean;
};

type LoadState = "loading" | "ready" | "forbidden" | "error";

const EMPTY_FORM = {
  name: "",
  key: "",
  partner_type: "wholesaler",
  channel_type: "portal",
  portal_login_email: "",
  portal_contact: "",
};

function CreatePartnerForm({ onCreated }: { onCreated: () => void }) {
  const [form, setForm] = useState({ ...EMPTY_FORM });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [ok, setOk] = useState("");

  function set<K extends keyof typeof form>(k: K, v: string) {
    setForm((f) => ({ ...f, [k]: v }));
  }

  async function submit() {
    if (!form.name.trim() || !form.key.trim()) {
      setError("Name and key are required.");
      return;
    }
    setBusy(true);
    setError("");
    setOk("");
    try {
      await adminFetch("/admin/network-partners", {
        method: "POST",
        body: JSON.stringify({
          ...form,
          key: form.key.trim().toLowerCase(),
          portal_login_email: form.portal_login_email.trim().toLowerCase() || null,
          portal_contact: form.portal_contact.trim() || null,
        }),
      });
      setOk(`${form.name.trim()} added.`);
      setForm({ ...EMPTY_FORM });
      onCreated();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not create partner.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="rounded-3xl border border-white/8 bg-white/4 p-5">
      <div className="mb-4 flex items-center gap-3">
        <UserPlus className="h-5 w-5 text-emerald-400" />
        <div>
          <p className="text-lg font-semibold text-white">Onboard a Partner</p>
          <p className="text-sm text-white/45">
            The portal email is how the wholesaler or supplier signs in at <span className="text-white/70">/partners</span>.
          </p>
        </div>
      </div>
      <div className="grid gap-3 md:grid-cols-2">
        <label className="space-y-1">
          <span className="text-[11px] text-white/50">Business name</span>
          <input
            value={form.name}
            onChange={(e) => set("name", e.target.value)}
            placeholder="Acme Wholesale Ltd"
            className="w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-white outline-none focus:border-emerald-500/50"
          />
        </label>
        <label className="space-y-1">
          <span className="text-[11px] text-white/50">Unique key (slug)</span>
          <input
            value={form.key}
            onChange={(e) => set("key", e.target.value)}
            placeholder="acme-wholesale"
            className="w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-white outline-none focus:border-emerald-500/50"
          />
        </label>
        <label className="space-y-1">
          <span className="text-[11px] text-white/50">Type</span>
          <select
            value={form.partner_type}
            onChange={(e) => set("partner_type", e.target.value)}
            className="w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-white outline-none focus:border-emerald-500/50"
          >
            <option value="wholesaler">Wholesaler</option>
            <option value="supplier">Supplier</option>
          </select>
        </label>
        <label className="space-y-1">
          <span className="text-[11px] text-white/50">Channel</span>
          <select
            value={form.channel_type}
            onChange={(e) => set("channel_type", e.target.value)}
            className="w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-white outline-none focus:border-emerald-500/50"
          >
            <option value="portal">Portal (email login)</option>
            <option value="api">API integration</option>
          </select>
        </label>
        <label className="space-y-1">
          <span className="text-[11px] text-white/50">Portal login email</span>
          <input
            type="email"
            value={form.portal_login_email}
            onChange={(e) => set("portal_login_email", e.target.value)}
            placeholder="sourcing@acme.com"
            className="w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-white outline-none focus:border-emerald-500/50"
          />
        </label>
        <label className="space-y-1">
          <span className="text-[11px] text-white/50">Contact (optional)</span>
          <input
            value={form.portal_contact}
            onChange={(e) => set("portal_contact", e.target.value)}
            placeholder="Name / phone"
            className="w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-white outline-none focus:border-emerald-500/50"
          />
        </label>
      </div>
      {error && <p className="mt-3 text-[13px] text-red-400">{error}</p>}
      {ok && <p className="mt-3 text-[13px] text-emerald-400">{ok}</p>}
      <div className="mt-4">
        <Button onClick={submit} disabled={busy}>
          {busy ? "Adding…" : "Add Partner"}
        </Button>
      </div>
    </section>
  );
}

function PartnerRowCard({ partner, onChanged }: { partner: PartnerRow; onChanged: () => void }) {
  const [editing, setEditing] = useState(false);
  const [email, setEmail] = useState(partner.portal_login_email ?? "");
  const [contact, setContact] = useState(partner.portal_contact ?? "");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function patch(body: Record<string, unknown>) {
    setBusy(true);
    setError("");
    try {
      await adminFetch(`/admin/network-partners/${partner.id}`, {
        method: "PATCH",
        body: JSON.stringify(body),
      });
      setEditing(false);
      onChanged();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Update failed.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="rounded-2xl border border-white/8 bg-black/20 p-4">
      <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <p className="text-sm font-semibold text-white">{partner.name}</p>
            <span
              className={`rounded-full border px-2 py-0.5 text-[11px] font-semibold uppercase tracking-wide ${
                partner.is_active
                  ? "border-emerald-500/25 bg-emerald-500/15 text-emerald-400"
                  : "border-white/10 bg-white/8 text-[#b1bdb0]"
              }`}
            >
              {partner.is_active ? "Active" : "Disabled"}
            </span>
          </div>
          <p className="mt-1 text-xs text-white/45">
            {partner.partner_type} · {partner.channel_type} · {partner.key}
          </p>
          {!editing && (
            <p className="mt-2 text-xs text-white/55">
              {partner.portal_login_email ?? "No portal email set - partner cannot log in"}
              {partner.portal_contact ? ` · ${partner.portal_contact}` : ""}
            </p>
          )}
        </div>
        <div className="flex shrink-0 gap-2">
          <Button variant="secondary" onClick={() => setEditing((v) => !v)} className="px-3 py-1.5 text-xs">
            {editing ? "Cancel" : "Edit"}
          </Button>
          <Button
            variant={partner.is_active ? "danger" : "primary"}
            onClick={() => patch({ is_active: !partner.is_active })}
            disabled={busy}
            className="px-3 py-1.5 text-xs"
          >
            {partner.is_active ? "Disable" : "Enable"}
          </Button>
        </div>
      </div>

      {editing && (
        <div className="mt-3 space-y-2 rounded-xl border border-white/10 bg-white/[0.03] p-3">
          <label className="block space-y-1">
            <span className="text-[11px] text-white/50">Portal login email</span>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-white outline-none focus:border-emerald-500/50"
            />
          </label>
          <label className="block space-y-1">
            <span className="text-[11px] text-white/50">Contact</span>
            <input
              value={contact}
              onChange={(e) => setContact(e.target.value)}
              className="w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-white outline-none focus:border-emerald-500/50"
            />
          </label>
          {error && <p className="text-[12px] text-red-400">{error}</p>}
          <Button
            onClick={() => patch({ portal_login_email: email.trim().toLowerCase() || null, portal_contact: contact.trim() || null })}
            disabled={busy}
            className="px-4 py-2 text-xs"
          >
            {busy ? "Saving…" : "Save"}
          </Button>
        </div>
      )}
      {error && !editing && <p className="mt-2 text-[12px] text-red-400">{error}</p>}
    </div>
  );
}

export default function AdminPartnersPage() {
  const [rows, setRows] = useState<PartnerRow[]>([]);
  const [state, setState] = useState<LoadState>("loading");
  const [error, setError] = useState("");

  async function load() {
    setState("loading");
    setError("");
    try {
      const data = await adminFetch<PartnerRow[]>("/admin/network-partners");
      setRows(data);
      setState("ready");
    } catch (e) {
      if (e instanceof AdminFetchError && e.status === 403) {
        setState("forbidden");
      } else {
        setError(e instanceof Error ? e.message : "Could not load partners.");
        setState("error");
      }
    }
  }

  useEffect(() => {
    if (!getAdminToken()) {
      window.location.href = "/admin";
      return;
    }
    load();
  }, []);

  return (
    <div className="min-h-screen bg-[#0b0c09] px-5 py-8 text-white">
      <div className="mx-auto max-w-4xl">
        <PageHeader
          title="Partner Directory"
          fallbackHref="/admin"
          right={
            <Button variant="secondary" onClick={load} className="px-4 py-2">
              <RefreshCcw className="h-4 w-4" />
              Refresh
            </Button>
          }
        />

        <div className="space-y-6 pt-4">
          <p className="text-sm text-white/45">
            Approved wholesalers and suppliers. Set a portal login email so they can sign in and confirm sourcing requests.
          </p>

          {state === "forbidden" && (
            <div className="flex items-start gap-3 rounded-2xl border border-amber-500/20 bg-amber-500/8 px-4 py-4 text-sm text-amber-100/85">
              <ShieldAlert className="mt-0.5 h-5 w-5 shrink-0 text-amber-400" />
              <div>
                <p className="font-semibold">You don&apos;t have access to this view</p>
                <p className="mt-1 text-amber-100/70">Managing partners needs pricing permissions. Ask a System Owner.</p>
              </div>
            </div>
          )}

          {state === "error" && (
            <div className="rounded-2xl border border-red-500/20 bg-red-500/10 px-4 py-3 text-sm text-red-300">{error}</div>
          )}

          {(state === "ready" || state === "loading") && (
            <>
              <CreatePartnerForm onCreated={load} />
              <section className="rounded-3xl border border-white/8 bg-white/4 p-5">
                <p className="mb-4 text-xs uppercase tracking-[0.18em] text-[#b1bdb0]">{rows.length} partners</p>
                <div className="space-y-3">
                  {rows.map((partner) => (
                    <PartnerRowCard key={partner.id} partner={partner} onChanged={load} />
                  ))}
                  {state === "ready" && rows.length === 0 && (
                    <div className="rounded-2xl border border-dashed border-white/10 p-4 text-sm text-white/45">
                      No partners yet. Add your first approved wholesaler or supplier above.
                    </div>
                  )}
                </div>
              </section>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
