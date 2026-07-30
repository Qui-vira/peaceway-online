"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { Building2, LogOut, RefreshCcw, ShieldAlert, Truck, Workflow } from "lucide-react";
import {
  PartnerFetchError,
  clearPartnerToken,
  getPartnerToken,
  partnerFetch,
  setPartnerToken,
} from "@/lib/partner-auth";
import { Button, FulfillmentBadge } from "@/components/app/ui";

type PartnerMe = {
  id: string;
  key: string;
  name: string;
  partner_type: string;
  channel_type: string;
  portal_login_email: string | null;
  portal_contact: string | null;
};

type SourcingRow = {
  id: string;
  order_id: string;
  fulfillment_status: string;
  customer_facing_status: string | null;
  requested_items: { product_name: string; requested_qty?: number; quantity?: number }[] | null;
  ready_for_pickup_at: string | null;
  pickup_code: string | null;
  updated_at: string;
  last_error: string | null;
};

// Rows a partner can still act on (before Peaceway takes over dispatch).
const ACTIONABLE = new Set(["source_from_network", "sourcing_requested", "partner_confirmed"]);

function PartnerOtpGate({ onLogin }: { onLogin: (me: PartnerMe) => void }) {
  const [step, setStep] = useState<"email" | "code">("email");
  const [email, setEmail] = useState("");
  const [code, setCode] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSendCode() {
    const normalizedEmail = email.trim().toLowerCase();
    if (!normalizedEmail || !normalizedEmail.includes("@")) {
      setError("Enter the email assigned to your wholesaler or supplier portal account.");
      return;
    }
    setLoading(true);
    setError("");
    try {
      await partnerFetch<{ ok: boolean }>("/partner/request-otp", {
        method: "POST",
        body: JSON.stringify({ email: normalizedEmail }),
      });
      setStep("code");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not send code.");
    } finally {
      setLoading(false);
    }
  }

  async function handleVerify() {
    const c = code.trim();
    if (c.length !== 6) {
      setError("Enter the 6-digit code from your email.");
      return;
    }
    setLoading(true);
    setError("");
    try {
      const { token } = await partnerFetch<{ token: string }>("/partner/verify-otp", {
        method: "POST",
        body: JSON.stringify({ email: email.trim().toLowerCase(), code: c }),
      });
      setPartnerToken(token);
      const me = await partnerFetch<PartnerMe>("/partner/me");
      onLogin(me);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Invalid code.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-[#0b0c09] px-5">
      <div className="w-full max-w-md space-y-6">
        <div className="text-center">
          <p className="font-syne text-[20px] font-bold text-white">Partner Portal</p>
          <p className="mt-1 text-[13px] text-[#b1bdb0]">Approved wholesalers and suppliers only</p>
        </div>
        <div className="rounded-2xl border border-white/8 bg-white/4 p-6 space-y-4">
          <div className="rounded-2xl border border-emerald-500/20 bg-emerald-500/8 px-4 py-3 text-[12px] text-white/75">
            Peaceway staff should not sign in here.{" "}
            <Link href="/admin" className="font-semibold text-emerald-300 underline-offset-2 hover:underline">
              Use the staff portal
            </Link>
            .
          </div>
          {step === "email" ? (
            <>
              <div className="space-y-1.5">
                <label className="text-[11px] font-medium text-white/50">Partner work email</label>
                <input
                  type="email"
                  autoComplete="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && handleSendCode()}
                  placeholder="sourcing@partner.com"
                  className="w-full rounded-xl border border-white/10 bg-white/5 px-4 py-3 text-base text-white placeholder-[#b1bdb0] outline-none focus:border-emerald-500/50"
                />
                <p className="text-[11px] text-[#b1bdb0]">Use the email linked to your approved Peaceway partner account.</p>
              </div>
              {error && <p className="text-[13px] text-red-400">{error}</p>}
              <Button onClick={handleSendCode} disabled={loading || !email.trim()} className="w-full">
                {loading ? "Sending…" : "Send Code via Email"}
              </Button>
            </>
          ) : (
            <>
              <div className="space-y-1.5">
                <label className="text-[11px] font-medium text-white/50">6-digit code</label>
                <input
                  type="text"
                  inputMode="numeric"
                  maxLength={6}
                  value={code}
                  onChange={(e) => setCode(e.target.value.replace(/\D/g, ""))}
                  onKeyDown={(e) => e.key === "Enter" && handleVerify()}
                  placeholder="000000"
                  className="w-full rounded-xl border border-white/10 bg-white/5 px-4 py-3 text-base tracking-[0.3em] text-white placeholder-[#b1bdb0] outline-none focus:border-emerald-500/50"
                  autoFocus
                />
                <p className="text-[11px] text-[#b1bdb0]">Check your email inbox. The code expires in 5 minutes.</p>
              </div>
              {error && <p className="text-[13px] text-red-400">{error}</p>}
              <Button onClick={handleVerify} disabled={loading || code.trim().length !== 6} className="w-full">
                {loading ? "Verifying…" : "Verify & Sign In"}
              </Button>
              <button
                onClick={() => {
                  setStep("email");
                  setCode("");
                  setError("");
                }}
                className="w-full text-center text-[12px] text-[#b1bdb0] hover:text-[#dcdddb]"
              >
                ← Resend / use different email
              </button>
            </>
          )}
        </div>
        {/* Same dead end as the staff gate: no way back to the app. */}
        <p className="text-center">
          <Link
            href="/app"
            className="-my-2 inline-flex min-h-[44px] items-center rounded px-2 py-2 text-[12px] text-[#b1bdb0] transition hover:text-[#dcdddb]"
          >
            ← Back to Peaceway Online
          </Link>
        </p>
      </div>
    </div>
  );
}

function ConfirmForm({ row, onDone }: { row: SourcingRow; onDone: () => void }) {
  const [qty, setQty] = useState("");
  const [price, setPrice] = useState("");
  const [batch, setBatch] = useState("");
  const [pickup, setPickup] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function submit() {
    if (!qty || !price || !batch.trim()) {
      setError("Quantity, price, and expiry/batch confirmation are required.");
      return;
    }
    setBusy(true);
    setError("");
    try {
      await partnerFetch(`/partner/sourcing/${row.id}/action`, {
        method: "POST",
        body: JSON.stringify({
          action: "partner_confirmed",
          confirmed_quantity: Number(qty),
          confirmed_price: price,
          expiry_or_batch_confirmation: batch.trim(),
          ready_for_pickup_at: pickup ? new Date(pickup).toISOString() : null,
        }),
      });
      onDone();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not confirm.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mt-3 space-y-3 rounded-xl border border-emerald-500/20 bg-emerald-500/[0.06] p-4">
      <p className="text-[12px] font-semibold text-emerald-200">Confirm this request</p>
      <div className="grid gap-3 sm:grid-cols-2">
        <label className="space-y-1">
          <span className="text-[11px] text-white/50">Confirmed quantity</span>
          <input
            type="number"
            min={1}
            value={qty}
            onChange={(e) => setQty(e.target.value)}
            className="w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-base text-white outline-none focus:border-emerald-500/50"
          />
        </label>
        <label className="space-y-1">
          <span className="text-[11px] text-white/50">Confirmed price (₦)</span>
          <input
            type="number"
            min={0}
            value={price}
            onChange={(e) => setPrice(e.target.value)}
            className="w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-base text-white outline-none focus:border-emerald-500/50"
          />
        </label>
      </div>
      <label className="block space-y-1">
        <span className="text-[11px] text-white/50">Expiry / batch confirmation</span>
        <input
          value={batch}
          onChange={(e) => setBatch(e.target.value)}
          placeholder="e.g. Batch A23, expiry 2027-05"
          className="w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-base text-white outline-none focus:border-emerald-500/50"
        />
      </label>
      <label className="block space-y-1">
        <span className="text-[11px] text-white/50">Ready for pickup at (optional)</span>
        <input
          type="datetime-local"
          value={pickup}
          onChange={(e) => setPickup(e.target.value)}
          className="w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-base text-white outline-none focus:border-emerald-500/50"
        />
      </label>
      {error && <p className="text-[12px] text-red-400">{error}</p>}
      <div className="flex gap-2">
        <Button onClick={submit} disabled={busy} className="px-4 py-2">
          {busy ? "Saving…" : "Confirm"}
        </Button>
      </div>
    </div>
  );
}

function SourcingCard({ row, onChanged }: { row: SourcingRow; onChanged: () => void }) {
  const [confirming, setConfirming] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const canAct = ACTIONABLE.has(row.fulfillment_status);
  const canConfirm = row.fulfillment_status === "source_from_network" || row.fulfillment_status === "sourcing_requested";
  const canPackReady = row.fulfillment_status === "partner_confirmed";

  async function act(action: "partner_rejected" | "pack_ready") {
    setBusy(true);
    setError("");
    try {
      await partnerFetch(`/partner/sourcing/${row.id}/action`, {
        method: "POST",
        body: JSON.stringify({ action }),
      });
      onChanged();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Action failed.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="rounded-2xl border border-white/8 bg-black/20 p-4">
      <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
        <div className="min-w-0">
          <FulfillmentBadge status={row.fulfillment_status} />
          <p className="mt-2 text-xs text-white/45">Order {row.order_id}</p>
          {row.requested_items && (
            <p className="mt-2 text-xs text-white/60">
              {row.requested_items
                .map((item) => `${item.product_name} ×${item.requested_qty ?? item.quantity ?? 1}`)
                .join(", ")}
            </p>
          )}
          {row.last_error && (
            <div className="mt-2 inline-flex items-center gap-1 rounded-full border border-amber-500/20 bg-amber-500/10 px-2 py-1 text-[11px] text-amber-200">
              <ShieldAlert className="h-3 w-3" />
              {row.last_error}
            </div>
          )}
        </div>
        <div className="text-xs text-white/45 md:text-right">
          {row.ready_for_pickup_at && <p>Ready: {new Date(row.ready_for_pickup_at).toLocaleString("en-NG")}</p>}
          {row.pickup_code && (
            <p className="mt-1">
              Pickup code: <span className="font-semibold text-white">{row.pickup_code}</span>
            </p>
          )}
          <p className="mt-1">Updated {new Date(row.updated_at).toLocaleString("en-NG")}</p>
        </div>
      </div>

      {error && <p className="mt-2 text-[12px] text-red-400">{error}</p>}

      {canAct && (
        <div className="mt-3 flex flex-wrap gap-2">
          {canConfirm && (
            <Button variant="secondary" onClick={() => setConfirming((v) => !v)} className="px-4 py-2">
              {confirming ? "Cancel" : "Confirm availability"}
            </Button>
          )}
          {canPackReady && (
            <Button onClick={() => act("pack_ready")} disabled={busy} className="px-4 py-2">
              Mark pack ready
            </Button>
          )}
          <Button variant="danger" onClick={() => act("partner_rejected")} disabled={busy} className="px-4 py-2">
            Can’t fulfil
          </Button>
        </div>
      )}

      {confirming && canConfirm && (
        <ConfirmForm
          row={row}
          onDone={() => {
            setConfirming(false);
            onChanged();
          }}
        />
      )}
    </div>
  );
}

function PartnerDashboard({ me }: { me: PartnerMe }) {
  const [rows, setRows] = useState<SourcingRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  async function load() {
    setLoading(true);
    setError("");
    try {
      const sourcingRows = await partnerFetch<SourcingRow[]>("/partner/sourcing");
      setRows(sourcingRows);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not load your sourcing requests.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  const dispatchReady = useMemo(
    () => rows.filter((row) => ["pack_ready", "dispatch_assigned", "picked_up"].includes(row.fulfillment_status)),
    [rows]
  );

  async function signOut() {
    try {
      await partnerFetch("/partner/session", { method: "DELETE" });
    } catch {
      // ignore
    }
    clearPartnerToken();
    window.location.reload();
  }

  return (
    <div className="min-h-screen bg-[#0b0c09] px-5 py-8 text-white">
      <div className="mx-auto max-w-5xl space-y-6">
        <div className="flex flex-col gap-4 rounded-3xl border border-white/8 bg-white/4 p-6 md:flex-row md:items-start md:justify-between">
          <div>
            <p className="text-[11px] uppercase tracking-[0.18em] text-[#b1bdb0]">Peaceway Partner Portal</p>
            <p className="mt-2 font-syne text-3xl font-bold">{me.name}</p>
            <p className="mt-2 text-sm text-white/55">
              Confirm sourcing requests, prepare verified packs, and hand off cleanly into Peaceway dispatch tracking.
            </p>
            <p className="mt-3 text-xs font-medium text-emerald-300/80">
              {me.partner_type} · {me.channel_type}
            </p>
          </div>
          <div className="flex gap-3">
            <Button variant="secondary" onClick={load} className="px-4 py-2">
              <RefreshCcw className="h-4 w-4" />
              Refresh
            </Button>
            <Button variant="secondary" onClick={signOut} className="px-4 py-2">
              <LogOut className="h-4 w-4" />
              Sign out
            </Button>
          </div>
        </div>

        {error && (
          <div className="rounded-2xl border border-red-500/20 bg-red-500/10 px-4 py-3 text-sm text-red-300">{error}</div>
        )}

        <div className="grid gap-3 md:grid-cols-3">
          <div className="rounded-2xl border border-white/8 bg-white/4 p-4">
            <p className="text-[22px] font-bold text-white">{rows.length}</p>
            <p className="mt-1 text-[11px] text-[#b1bdb0]">Assigned sourcing requests</p>
          </div>
          <div className="rounded-2xl border border-white/8 bg-white/4 p-4">
            <p className="text-[22px] font-bold text-white">{dispatchReady.length}</p>
            <p className="mt-1 text-[11px] text-[#b1bdb0]">Pack-ready or dispatched</p>
          </div>
          <div className="rounded-2xl border border-white/8 bg-white/4 p-4">
            <p className="truncate text-[15px] font-semibold text-white">{me.portal_login_email ?? me.key}</p>
            <p className="mt-1 text-[11px] text-[#b1bdb0]">Signed in as</p>
          </div>
        </div>

        <section className="rounded-3xl border border-white/8 bg-white/4 p-5">
          <div className="mb-4 flex items-center gap-3">
            <Building2 className="h-5 w-5 text-emerald-400" />
            <div>
              <p className="text-lg font-semibold">Your Partner Profile</p>
              <p className="text-sm text-white/45">This is the identity Peaceway uses to route requests to you.</p>
            </div>
          </div>
          <div className="rounded-2xl border border-white/8 bg-black/20 p-4">
            <p className="text-sm font-semibold">{me.name}</p>
            <p className="mt-1 text-xs text-white/45">
              {me.partner_type} · {me.channel_type}
            </p>
            <p className="mt-3 text-xs text-white/55">{me.portal_contact ?? me.portal_login_email ?? me.key}</p>
          </div>
        </section>

        <section className="rounded-3xl border border-white/8 bg-white/4 p-5">
          <div className="mb-4 flex items-center gap-3">
            <Workflow className="h-5 w-5 text-emerald-400" />
            <div>
              <p className="text-lg font-semibold">Assigned Sourcing Requests</p>
              <p className="text-sm text-white/45">Only requests routed to your organisation appear here.</p>
            </div>
          </div>
          <div className="space-y-3">
            {rows.map((row) => (
              <SourcingCard key={row.id} row={row} onChanged={load} />
            ))}
            {!loading && rows.length === 0 && (
              <div className="rounded-2xl border border-dashed border-white/10 p-4 text-sm text-white/45">
                No sourcing requests are currently assigned to your organisation.
              </div>
            )}
          </div>
        </section>

        <section className="rounded-3xl border border-white/8 bg-white/4 p-5">
          <div className="mb-4 flex items-center gap-3">
            <Truck className="h-5 w-5 text-emerald-400" />
            <div>
              <p className="text-lg font-semibold">Dispatch Handoff</p>
              <p className="text-sm text-white/45">What happens after you confirm and pack an order.</p>
            </div>
          </div>
          <div className="grid gap-3 md:grid-cols-3">
            {[
              "Peaceway routes an out-of-stock request to your organisation.",
              "You confirm stock, quantity, price, and verified batch or expiry details.",
              "Once packed, Peaceway dispatch picks up under Peaceway verification and tracking.",
            ].map((item) => (
              <div key={item} className="rounded-2xl border border-white/8 bg-black/20 p-4 text-sm text-white/70">
                {item}
              </div>
            ))}
          </div>
        </section>
      </div>
    </div>
  );
}

export default function PartnerPortalPage() {
  const [me, setMe] = useState<PartnerMe | null>(null);
  const [checked, setChecked] = useState(false);

  useEffect(() => {
    const token = getPartnerToken();
    if (token) {
      partnerFetch<PartnerMe>("/partner/me")
        .then((profile) => setMe(profile))
        .catch((e) => {
          if (e instanceof PartnerFetchError && e.status !== 401) clearPartnerToken();
        })
        .finally(() => setChecked(true));
    } else {
      setChecked(true);
    }
  }, []);

  if (!checked) return <div className="min-h-screen bg-[#0b0c09]" />;
  if (me) return <PartnerDashboard me={me} />;
  return <PartnerOtpGate onLogin={setMe} />;
}
