"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import {
  LayoutGrid, ClipboardList, Package, Users, DollarSign, ShoppingBag,
  LogOut, Mail, Search, Save, RefreshCcw, ShieldCheck, Truck, Workflow, Building2,
} from "lucide-react";
import {
  adminFetch, setAdminToken, clearAdminToken, getAdminToken, anyPermission,
} from "@/lib/admin-auth";

// ── Types ─────────────────────────────────────────────────────────────────────
interface AdminMe {
  telegram_id: number | null;
  full_name: string | null;
  roles: string[];
  role_labels?: string[];
  permissions: string[];
}

interface AdminRequest {
  id: string;
  product_name: string;
  status: string;
  customer_phone: string | null;
  created_at: string;
}

interface AdminOrder {
  id: string;
  code: string;
  status: string;
  fulfillment_status?: string | null;
  customer_facing_status?: string | null;
  total: string;
  created_at: string;
}

interface AdminProduct {
  id: string;
  name: string;
  generic_name: string;
  brand_name: string | null;
  dosage_form: string | null;
  strength: string | null;
  category: string | null;
  requires_prescription: boolean;
  requires_review: boolean;
  is_listed: boolean;
  cost_price: string | null;
  selling_price: string | null;
  stock_qty: number;
  is_in_stock: boolean;
  updated_at: string;
}

interface AdminProductsResponse {
  items: AdminProduct[];
  total: number;
  limit: number;
  offset: number;
  metrics: {
    total: number;
    listed: number;
    in_stock: number;
    unpriced: number;
  };
}

type ProductDraft = {
  selling_price: string;
  cost_price: string;
  stock_qty: string;
  is_listed: boolean;
  requires_prescription: boolean;
};

// ── Nav definition (permission-gated) ────────────────────────────────────────
const ALL_NAV = [
  { key: "overview",  icon: LayoutGrid,    label: "Overview",   permissions: [] as string[] },
  { key: "catalog",   icon: ShoppingBag,   label: "Inventory",  permissions: ["edit_pricing", "view_all_products"] },
  { key: "sourcing",  icon: Workflow,      label: "Sourcing",   permissions: ["view_sourcing_requests", "view_partner_directory", "view_all_orders", "edit_pricing"] },
  { key: "dispatch",  icon: Truck,         label: "Dispatch",   permissions: ["view_dispatch_queue", "assign_rider", "mark_picked_up"] },
  { key: "requests",  icon: ClipboardList, label: "Requests",   permissions: ["view_product_requests"] },
  { key: "orders",    icon: Package,       label: "Orders",     permissions: ["view_all_orders", "view_customer_orders"] },
  { key: "customers", icon: Users,         label: "Customers",  permissions: ["view_customers"] },
  { key: "payments",  icon: DollarSign,    label: "Payments",   permissions: ["review_payment_proof", "view_payment_history", "view_payment_status"] },
];

function visibleNav(permissions: string[]) {
  return ALL_NAV.filter(
    (item) => item.permissions.length === 0 || anyPermission(permissions, item.permissions)
  );
}

// ── Status labels / colors ────────────────────────────────────────────────────
const REQ_STATUS_COLOR: Record<string, string> = {
  NEW: "bg-white/8 text-white/50 border-white/12",
  CHECKING_AVAILABILITY: "bg-amber-500/15 text-amber-400 border-amber-500/25",
  AVAILABLE: "bg-emerald-500/15 text-emerald-400 border-emerald-500/25",
  NOT_AVAILABLE: "bg-red-500/15 text-red-400 border-red-500/25",
  FULFILLED: "bg-emerald-500/15 text-emerald-400 border-emerald-500/25",
};
const REQ_STATUS_LABEL: Record<string, string> = {
  NEW: "New",
  CHECKING_AVAILABILITY: "Checking",
  AVAILABLE: "Available",
  NOT_AVAILABLE: "Not avail.",
  READY_TO_ORDER: "Ready",
  FULFILLED: "Fulfilled",
  CLOSED: "Closed",
};

// ── Staff OTP login gate ──────────────────────────────────────────────────────
function StaffOtpGate({ onLogin }: { onLogin: (admin: AdminMe) => void }) {
  const [channel, setChannel] = useState<"email" | "telegram">("email");
  const [step, setStep] = useState<"identifier" | "code">("identifier");
  const [telegramId, setTelegramId] = useState("");
  const [email, setEmail] = useState("");
  const [code, setCode] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSendCode() {
    if (channel === "telegram") {
      const tid = telegramId.trim();
      if (!tid || !/^\d+$/.test(tid)) {
        setError("Enter your numeric Telegram ID.");
        return;
      }
      setLoading(true);
      setError("");
      try {
        await adminFetch<{ ok: boolean }>("/admin/request-otp", {
          method: "POST",
          body: JSON.stringify({ telegram_id: Number(tid) }),
        });
        setStep("code");
      } catch (e) {
        setError(e instanceof Error ? e.message : "Could not send code.");
      } finally {
        setLoading(false);
      }
      return;
    }

    const normalizedEmail = email.trim().toLowerCase();
    if (!normalizedEmail || !normalizedEmail.includes("@")) {
      setError("Enter the email assigned to your operations account.");
      return;
    }

    setLoading(true);
    setError("");
    try {
      await adminFetch<{ ok: boolean }>("/admin/request-email-otp", {
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
    if (!c || c.length !== 6) {
      setError("Enter the 6-digit verification code.");
      return;
    }
    setLoading(true);
    setError("");
    try {
      const { token } = channel === "telegram"
        ? await adminFetch<{ token: string }>("/admin/verify-otp", {
            method: "POST",
            body: JSON.stringify({ telegram_id: Number(telegramId.trim()), code: c }),
          })
        : await adminFetch<{ token: string }>("/admin/verify-email-otp", {
            method: "POST",
            body: JSON.stringify({ email: email.trim().toLowerCase(), code: c }),
          });
      setAdminToken(token);
      const me = await adminFetch<AdminMe>("/admin/me");
      onLogin(me);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Invalid code.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center px-5">
      <div className="w-full max-w-md space-y-6">
        <div className="text-center">
          <p className="font-syne text-[20px] font-bold text-white">Peaceway Staff</p>
          <p className="mt-1 text-[13px] text-white/40">Internal team access for Peaceway staff and admins</p>
        </div>
        <div className="rounded-2xl border border-white/8 bg-white/4 p-6 space-y-4">
          <div className="rounded-2xl border border-amber-500/20 bg-amber-500/8 px-4 py-3 text-[12px] text-amber-100/85">
            Wholesalers and suppliers should not sign in here.
            {" "}
            <Link href="/partners" className="font-semibold text-amber-300 underline-offset-2 hover:underline">
              Use the partner portal instead
            </Link>
            .
          </div>
          <div className="grid grid-cols-2 gap-2 rounded-2xl border border-white/8 bg-black/20 p-1">
            <button
              onClick={() => {
                setChannel("email");
                setStep("identifier");
                setCode("");
                setError("");
              }}
              className={[
                "inline-flex items-center justify-center gap-2 rounded-xl px-3 py-2.5 text-sm transition",
                channel === "email" ? "bg-emerald-500 text-black font-semibold" : "text-white/55 hover:text-white",
              ].join(" ")}
            >
              <Mail className="h-4 w-4" />
              Email sign-in
            </button>
            <button
              onClick={() => {
                setChannel("telegram");
                setStep("identifier");
                setCode("");
                setError("");
              }}
              className={[
                "inline-flex items-center justify-center gap-2 rounded-xl px-3 py-2.5 text-sm transition",
                channel === "telegram" ? "bg-emerald-500 text-black font-semibold" : "text-white/55 hover:text-white",
              ].join(" ")}
            >
              <ShieldCheck className="h-4 w-4" />
              Telegram sign-in
            </button>
          </div>

          {step === "identifier" ? (
            <>
              {channel === "telegram" ? (
                <div className="space-y-1.5">
                  <label className="text-[11px] font-medium text-white/50">Your Telegram ID</label>
                  <input
                    type="text"
                    inputMode="numeric"
                    value={telegramId}
                    onChange={(e) => setTelegramId(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && handleSendCode()}
                    placeholder="e.g. 123456789"
                    className="w-full rounded-xl border border-white/10 bg-white/5 px-4 py-3 text-sm text-white placeholder-white/30 outline-none focus:border-emerald-500/50"
                  />
                  <p className="text-[11px] text-white/30">
                    Send <code>/myid</code> to the Peaceway bot to find your ID.
                  </p>
                </div>
              ) : (
                <div className="space-y-1.5">
                  <label className="text-[11px] font-medium text-white/50">Work email</label>
                  <input
                    type="email"
                    autoComplete="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && handleSendCode()}
                    placeholder="operations@company.com"
                    className="w-full rounded-xl border border-white/10 bg-white/5 px-4 py-3 text-sm text-white placeholder-white/30 outline-none focus:border-emerald-500/50"
                  />
                  <p className="text-[11px] text-white/30">
                    Use the email assigned to your Peaceway operations account.
                  </p>
                </div>
              )}
              {error && <p className="text-[13px] text-red-400">{error}</p>}
              <button
                onClick={handleSendCode}
                disabled={loading || (channel === "telegram" ? !telegramId.trim() : !email.trim())}
                className="w-full rounded-xl bg-emerald-500 py-3.5 text-sm font-semibold text-black disabled:opacity-50"
              >
                {loading ? "Sending…" : channel === "telegram" ? "Send Code via Telegram" : "Send Code via Email"}
              </button>
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
                  onChange={(e) => setCode(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && handleVerify()}
                  placeholder="000000"
                  className="w-full rounded-xl border border-white/10 bg-white/5 px-4 py-3 text-sm text-white placeholder-white/30 outline-none focus:border-emerald-500/50 tracking-[0.3em]"
                  autoFocus
                />
                <p className="text-[11px] text-white/30">
                  {channel === "telegram"
                    ? "Check your Telegram — the code expires in 5 minutes."
                    : "Check your email inbox — the code expires in 5 minutes."}
                </p>
              </div>
              {error && <p className="text-[13px] text-red-400">{error}</p>}
              <button
                onClick={handleVerify}
                disabled={loading || code.trim().length !== 6}
                className="w-full rounded-xl bg-emerald-500 py-3.5 text-sm font-semibold text-black disabled:opacity-50"
              >
                {loading ? "Verifying…" : "Verify & Sign In"}
              </button>
              <button
                onClick={() => { setStep("identifier"); setCode(""); setError(""); }}
                className="w-full text-center text-[12px] text-white/30 hover:text-white/60"
              >
                ← Resend / use a different sign-in method
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

// ── Dashboard ─────────────────────────────────────────────────────────────────
function Dashboard({ admin }: { admin: AdminMe }) {
  const nav = visibleNav(admin.permissions);
  const [tab, setTab] = useState(nav[0]?.key ?? "overview");
  const [requests, setRequests] = useState<AdminRequest[]>([]);
  const [orders, setOrders] = useState<AdminOrder[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setLoading(true);
    Promise.allSettled([
      adminFetch<AdminRequest[]>("/admin/requests"),
      adminFetch<AdminOrder[]>("/admin/orders"),
    ]).then(([reqRes, ordRes]) => {
      if (reqRes.status === "fulfilled") setRequests(reqRes.value);
      if (ordRes.status === "fulfilled") setOrders(ordRes.value);
      setLoading(false);
    });
  }, []);

  async function signOut() {
    try {
      await adminFetch("/admin/session", { method: "DELETE" });
    } catch {
      // ignore
    }
    clearAdminToken();
    window.location.reload();
  }

  return (
    <div className="flex min-h-screen">
      {/* Sidebar */}
      <aside className="hidden w-[200px] shrink-0 flex-col gap-2 border-r border-white/8 bg-[#0a0b08] px-3 py-6 lg:flex">
        <div className="mb-4 px-3">
          <p className="font-syne text-[13px] font-bold text-white">Peaceway</p>
          <p className="text-[10px] text-white/50">{admin.full_name ?? "Staff"}</p>
          {(admin.role_labels?.length ?? 0) > 0 && (
            <p className="mt-0.5 text-[10px] font-medium text-emerald-400/80">
              {admin.role_labels!.join(" · ")}
            </p>
          )}
        </div>
        {nav.map((item) => (
          <button
            key={item.key}
            onClick={() => setTab(item.key)}
            className={`flex items-center gap-3 rounded-xl px-3 py-2.5 text-[13px] font-medium transition ${
              tab === item.key
                ? "bg-emerald-500/12 text-emerald-400"
                : "text-white/40 hover:text-white/70"
            }`}
          >
            <item.icon className="h-4 w-4" />
            {item.label}
          </button>
        ))}
        <div className="mt-auto">
          <button
            onClick={signOut}
            className="flex items-center gap-3 rounded-xl px-3 py-2.5 text-[13px] text-white/30 hover:text-white/60"
          >
            <LogOut className="h-4 w-4" />
            Sign out
          </button>
        </div>
      </aside>

      {/* Mobile top nav */}
      <div className="fixed top-0 left-0 right-0 z-10 flex gap-1 overflow-x-auto border-b border-white/8 bg-[#0a0b08] px-3 py-2 lg:hidden">
        {nav.map((item) => (
          <button
            key={item.key}
            onClick={() => setTab(item.key)}
            className={`shrink-0 flex items-center gap-1.5 rounded-lg px-3 py-2 text-[11px] font-medium transition ${
              tab === item.key
                ? "bg-emerald-500/15 text-emerald-400"
                : "text-white/40"
            }`}
          >
            <item.icon className="h-3.5 w-3.5" />
            {item.label}
          </button>
        ))}
      </div>

      {/* Content */}
      <main className="flex-1 overflow-auto p-5 pt-16 lg:pt-6">
        {tab === "overview" && (
          <OverviewTab requests={requests} orders={orders} loading={loading} onTab={setTab} />
        )}
        {tab === "requests" && (
          <RequestsTab requests={requests} loading={loading} />
        )}
        {tab === "orders" && (
          <OrdersTab orders={orders} loading={loading} />
        )}
        {tab === "customers" && (
          <div className="py-10 text-center text-white/40">Customer list — coming soon</div>
        )}
        {tab === "payments" && (
          <div className="py-10 text-center text-white/40">Payment records — coming soon</div>
        )}
        {tab === "catalog" && (
          <CatalogTab />
        )}
        {tab === "sourcing" && (
          <div className="space-y-4">
            <h2 className="font-syne text-[18px] font-bold text-white">Partner Sourcing</h2>
            <div className="rounded-2xl border border-white/8 bg-white/4 p-5 text-sm text-white/60">
              Track out-of-stock rescue workflows, confirm partner stock, and keep the customer under Peaceway tracking.
              <div className="mt-4">
                <Link href="/admin/sourcing" className="inline-flex items-center gap-2 rounded-xl bg-emerald-500 px-4 py-2 font-semibold text-black">
                  Open Sourcing Control
                </Link>
              </div>
            </div>
          </div>
        )}
        {tab === "dispatch" && (
          <div className="space-y-4">
            <h2 className="font-syne text-[18px] font-bold text-white">Dispatch Readiness</h2>
            <div className="rounded-2xl border border-white/8 bg-white/4 p-5 text-sm text-white/60">
              View pickup-ready partner orders and keep last-mile delivery under Peaceway verification.
              <div className="mt-4">
                <Link href="/admin/dispatch" className="inline-flex items-center gap-2 rounded-xl bg-emerald-500 px-4 py-2 font-semibold text-black">
                  Open Dispatch Queue
                </Link>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

function productToDraft(product: AdminProduct): ProductDraft {
  return {
    selling_price: product.selling_price ? String(Number(product.selling_price)) : "",
    cost_price: product.cost_price ? String(Number(product.cost_price)) : "",
    stock_qty: String(product.stock_qty ?? 0),
    is_listed: product.is_listed,
    requires_prescription: product.requires_prescription,
  };
}

function formatMoney(value: string | null): string {
  if (!value || Number(value) <= 0) return "No price";
  return `₦${Number(value).toLocaleString("en-NG")}`;
}

// ── CatalogTab ────────────────────────────────────────────────────────────────
function CatalogTab() {
  const [q, setQ] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [data, setData] = useState<AdminProductsResponse | null>(null);
  const [drafts, setDrafts] = useState<Record<string, ProductDraft>>({});
  const [loading, setLoading] = useState(false);
  const [savingId, setSavingId] = useState<string | null>(null);
  const [message, setMessage] = useState("");

  const loadProducts = useCallback(async () => {
    setLoading(true);
    setMessage("");
    try {
      const params = new URLSearchParams();
      if (q.trim()) params.set("q", q.trim());
      params.set("status_filter", statusFilter);
      params.set("limit", "100");
      const result = await adminFetch<AdminProductsResponse>(`/admin/products?${params.toString()}`);
      setData(result);
      setDrafts((current) => {
        const next = { ...current };
        result.items.forEach((product) => {
          next[product.id] = next[product.id] ?? productToDraft(product);
        });
        return next;
      });
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Could not load products.");
    } finally {
      setLoading(false);
    }
  }, [q, statusFilter]);

  useEffect(() => {
    const timeout = window.setTimeout(loadProducts, 300);
    return () => window.clearTimeout(timeout);
  }, [loadProducts]);

  function updateDraft(id: string, patch: Partial<ProductDraft>) {
    setDrafts((current) => ({
      ...current,
      [id]: {
        ...(current[id] ?? {
          selling_price: "",
          cost_price: "",
          stock_qty: "0",
          is_listed: false,
          requires_prescription: false,
        }),
        ...patch,
      },
    }));
  }

  async function saveProduct(product: AdminProduct, patch?: Partial<ProductDraft>) {
    const draft = { ...(drafts[product.id] ?? productToDraft(product)), ...(patch ?? {}) };
    const stockQty = Number.parseInt(draft.stock_qty || "0", 10);
    if (Number.isNaN(stockQty) || stockQty < 0) {
      setMessage("Stock must be a whole number.");
      return;
    }

    setSavingId(product.id);
    setMessage("");
    try {
      const payload: Record<string, string | number | boolean> = {};
      const sellingPrice = draft.selling_price.trim();
      const costPrice = draft.cost_price.trim();
      if (sellingPrice !== (product.selling_price ? String(Number(product.selling_price)) : "")) {
        payload.selling_price = sellingPrice;
      }
      if (costPrice !== (product.cost_price ? String(Number(product.cost_price)) : "")) {
        payload.cost_price = costPrice;
      }
      if (stockQty !== product.stock_qty) {
        payload.stock_qty = stockQty;
      }
      if (draft.is_listed !== product.is_listed) {
        payload.is_listed = draft.is_listed;
      }
      if (draft.requires_prescription !== product.requires_prescription) {
        payload.requires_prescription = draft.requires_prescription;
      }
      if (Object.keys(payload).length === 0) {
        setMessage("No product changes to save.");
        return;
      }
      const updated = await adminFetch<AdminProduct>(`/admin/products/${product.id}`, {
        method: "PATCH",
        body: JSON.stringify(payload),
      });
      setData((current) => {
        if (!current) return current;
        return {
          ...current,
          items: current.items.map((item) => (item.id === updated.id ? updated : item)),
        };
      });
      setDrafts((current) => ({ ...current, [updated.id]: productToDraft(updated) }));
      setMessage(`Saved ${updated.name}`);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Could not save product.");
    } finally {
      setSavingId(null);
    }
  }

  const metrics = data?.metrics;

  return (
    <div className="space-y-5">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <h2 className="font-syne text-[18px] font-bold text-white">Catalog Inventory</h2>
          <p className="mt-1 text-[12px] text-white/40">
            Search all imported products. Price, stock, and listing changes update the shop immediately.
          </p>
        </div>
        <button
          onClick={loadProducts}
          className="inline-flex h-10 items-center justify-center gap-2 rounded-xl border border-white/10 bg-white/5 px-4 text-[12px] font-semibold text-white/70 hover:border-emerald-500/40 hover:text-white"
        >
          <RefreshCcw className="h-4 w-4" />
          Refresh
        </button>
      </div>

      {metrics && (
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
          {[
            ["Total products", metrics.total.toLocaleString("en-NG")],
            ["Listed in shop", metrics.listed.toLocaleString("en-NG")],
            ["In stock", metrics.in_stock.toLocaleString("en-NG")],
            ["Need price", metrics.unpriced.toLocaleString("en-NG")],
          ].map(([label, value]) => (
            <div key={label} className="rounded-2xl border border-white/8 bg-white/4 p-4">
              <p className="text-[20px] font-bold text-white">{value}</p>
              <p className="mt-0.5 text-[11px] text-white/40">{label}</p>
            </div>
          ))}
        </div>
      )}

      <div className="grid gap-3 lg:grid-cols-[1fr_190px]">
        <div className="flex items-center gap-3 rounded-xl border border-white/10 bg-white/4 px-4 py-3">
          <Search className="h-4 w-4 shrink-0 text-white/30" />
          <input
            value={q}
            onChange={(event) => setQ(event.target.value)}
            placeholder="Search medicine, brand, generic name, NAFDAC..."
            className="flex-1 bg-transparent text-sm text-white placeholder-white/30 outline-none"
          />
        </div>
        <select
          value={statusFilter}
          onChange={(event) => setStatusFilter(event.target.value)}
          className="h-[46px] rounded-xl border border-white/10 bg-[#10110e] px-3 text-sm text-white outline-none"
        >
          <option value="all">All products</option>
          <option value="listed">Listed</option>
          <option value="unlisted">Unlisted</option>
          <option value="in_stock">In stock</option>
          <option value="out_of_stock">Out of stock</option>
          <option value="unpriced">Unpriced</option>
        </select>
      </div>

      {message && (
        <div className="rounded-xl border border-white/10 bg-white/5 px-4 py-3 text-[12px] text-white/70">
          {message}
        </div>
      )}

      <div className="overflow-hidden rounded-2xl border border-white/8 bg-white/4">
        <div className="flex items-center justify-between border-b border-white/6 px-4 py-3">
          <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-white/40">
            {loading ? "Loading products" : `${data?.total.toLocaleString("en-NG") ?? 0} matching products`}
          </p>
          <p className="text-[11px] text-white/30">Showing first 100</p>
        </div>

        {loading && (
          <div className="px-4 py-10 text-center text-[13px] text-white/30">Loading catalog…</div>
        )}
        {!loading && data?.items.length === 0 && (
          <div className="px-4 py-10 text-center text-[13px] text-white/30">No products found</div>
        )}
        {!loading && data && data.items.length > 0 && (
          <div className="divide-y divide-white/6">
            {data.items.map((product) => {
              const draft = drafts[product.id] ?? productToDraft(product);
              const saving = savingId === product.id;
              return (
                <div key={product.id} className="grid gap-4 px-4 py-4 xl:grid-cols-[minmax(260px,1fr)_140px_120px_190px_160px]">
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <p className="truncate text-[14px] font-semibold text-white">{product.name}</p>
                      {product.is_listed ? (
                        <span className="rounded-full border border-emerald-500/25 bg-emerald-500/12 px-2 py-0.5 text-[10px] font-semibold text-emerald-400">Listed</span>
                      ) : (
                        <span className="rounded-full border border-white/10 bg-white/5 px-2 py-0.5 text-[10px] font-semibold text-white/35">Hidden</span>
                      )}
                      {!product.is_in_stock && (
                        <span className="rounded-full border border-red-500/25 bg-red-500/12 px-2 py-0.5 text-[10px] font-semibold text-red-300">Out</span>
                      )}
                    </div>
                    <p className="mt-1 line-clamp-2 text-[11px] text-white/40">
                      {product.generic_name}
                      {product.strength ? ` · ${product.strength}` : ""}
                      {product.category ? ` · ${product.category}` : ""}
                    </p>
                    <p className="mt-1 text-[11px] text-emerald-400/80">{formatMoney(product.selling_price)}</p>
                  </div>

                  <label className="space-y-1">
                    <span className="text-[10px] uppercase tracking-[0.12em] text-white/35">Price</span>
                    <input
                      inputMode="decimal"
                      value={draft.selling_price}
                      onChange={(event) => updateDraft(product.id, { selling_price: event.target.value })}
                      placeholder="0"
                      className="h-10 w-full rounded-xl border border-white/10 bg-black/20 px-3 text-sm text-white outline-none focus:border-emerald-500/50"
                    />
                  </label>

                  <label className="space-y-1">
                    <span className="text-[10px] uppercase tracking-[0.12em] text-white/35">Stock</span>
                    <input
                      inputMode="numeric"
                      value={draft.stock_qty}
                      onChange={(event) => updateDraft(product.id, { stock_qty: event.target.value })}
                      placeholder="0"
                      className="h-10 w-full rounded-xl border border-white/10 bg-black/20 px-3 text-sm text-white outline-none focus:border-emerald-500/50"
                    />
                  </label>

                  <div className="grid grid-cols-2 gap-2 xl:grid-cols-1">
                    <button
                      onClick={() => updateDraft(product.id, { is_listed: !draft.is_listed })}
                      className={`h-10 rounded-xl border px-3 text-[12px] font-semibold ${
                        draft.is_listed
                          ? "border-emerald-500/30 bg-emerald-500/12 text-emerald-400"
                          : "border-white/10 bg-white/5 text-white/45"
                      }`}
                    >
                      {draft.is_listed ? "Listed in shop" : "Hidden from shop"}
                    </button>
                    <button
                      onClick={() => updateDraft(product.id, { requires_prescription: !draft.requires_prescription })}
                      className={`h-10 rounded-xl border px-3 text-[12px] font-semibold ${
                        draft.requires_prescription
                          ? "border-amber-500/30 bg-amber-500/12 text-amber-300"
                          : "border-white/10 bg-white/5 text-white/45"
                      }`}
                    >
                      {draft.requires_prescription ? "Rx required" : "OTC"}
                    </button>
                  </div>

                  <div className="flex gap-2 xl:flex-col">
                    <button
                      onClick={() => saveProduct(product)}
                      disabled={saving}
                      className="inline-flex h-10 flex-1 items-center justify-center gap-2 rounded-xl bg-emerald-500 px-3 text-[12px] font-bold text-black disabled:opacity-50"
                    >
                      <Save className="h-3.5 w-3.5" />
                      {saving ? "Saving…" : "Save"}
                    </button>
                    <button
                      onClick={() => {
                        updateDraft(product.id, { stock_qty: "0" });
                        void saveProduct(product, { stock_qty: "0" });
                      }}
                      disabled={saving}
                      className="h-10 flex-1 rounded-xl border border-red-500/25 bg-red-500/10 px-3 text-[12px] font-semibold text-red-300 disabled:opacity-50"
                    >
                      Mark out
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}

// ── Overview tab ──────────────────────────────────────────────────────────────
function OverviewTab({
  requests, orders, loading, onTab,
}: {
  requests: AdminRequest[];
  orders: AdminOrder[];
  loading: boolean;
  onTab: (t: string) => void;
}) {
  const pending = requests.filter((r) => r.status === "NEW" || r.status === "CHECKING_AVAILABILITY").length;
  const todayOrders = orders.filter((o) => {
    const d = new Date(o.created_at);
    const now = new Date();
    return d.getDate() === now.getDate() && d.getMonth() === now.getMonth();
  });
  const todayRevenue = todayOrders.reduce((s, o) => s + Number(o.total), 0);
  const sourcingOrders = orders.filter((o) => !!o.fulfillment_status && o.fulfillment_status !== "in_stock").length;
  const dispatchReady = orders.filter((o) => ["pack_ready", "dispatch_assigned", "picked_up"].includes(o.fulfillment_status ?? "")).length;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-syne text-[20px] font-bold text-white">Overview</h1>
        <p className="text-[12px] text-white/40 mt-0.5">
          {new Date().toLocaleDateString("en-NG", { weekday: "long", day: "numeric", month: "long" })}
        </p>
      </div>
      <div className="grid grid-cols-2 gap-3">
        {[
          { label: "Pending requests", value: String(pending), note: "Need attention" },
          { label: "Today's orders", value: String(todayOrders.length), note: "New orders" },
          { label: "Today's revenue", value: `₦${todayRevenue.toLocaleString()}`, note: "From orders" },
          { label: "Sourcing orders", value: String(sourcingOrders), note: "Network workflow" },
        ].map((s) => (
          <div key={s.label} className="rounded-2xl border border-white/8 bg-white/4 p-4">
            <p className="text-[22px] font-bold text-white">{s.value}</p>
            <p className="text-[11px] text-white/40 mt-0.5">{s.label}</p>
            <p className={`text-[10px] mt-1 ${s.note === "Need attention" && pending > 0 ? "text-amber-400" : "text-emerald-400"}`}>
              {s.note}
            </p>
          </div>
        ))}
      </div>
      <button
        onClick={() => onTab("catalog")}
        className="flex w-full items-center justify-between rounded-2xl border border-emerald-500/20 bg-emerald-500/10 p-4 text-left transition hover:border-emerald-500/40"
      >
        <div>
          <p className="font-syne text-[15px] font-bold text-white">Open Inventory</p>
          <p className="mt-1 text-[12px] text-white/50">
            Search all products, set price, update stock, and mark items out of stock.
          </p>
        </div>
        <ShoppingBag className="h-5 w-5 shrink-0 text-emerald-400" />
      </button>
      <div className="grid gap-3 md:grid-cols-2">
        <Link
          href="/admin/sourcing"
          className="flex items-center justify-between rounded-2xl border border-white/8 bg-white/4 p-4 transition hover:border-emerald-500/30"
        >
          <div>
            <p className="font-syne text-[15px] font-bold text-white">Sourcing Control</p>
            <p className="mt-1 text-[12px] text-white/50">
              Review out-of-stock orders, partner confirmations, and customer-facing sourcing status.
            </p>
          </div>
          <Workflow className="h-5 w-5 shrink-0 text-emerald-400" />
        </Link>
        <Link
          href="/admin/dispatch"
          className="flex items-center justify-between rounded-2xl border border-white/8 bg-white/4 p-4 transition hover:border-emerald-500/30"
        >
          <div>
            <p className="font-syne text-[15px] font-bold text-white">Dispatch Readiness</p>
            <p className="mt-1 text-[12px] text-white/50">
              {dispatchReady} sourcing order{dispatchReady === 1 ? "" : "s"} are currently at pack-ready or later.
            </p>
          </div>
          <Truck className="h-5 w-5 shrink-0 text-emerald-400" />
        </Link>
        <Link
          href="/admin/partners"
          className="flex items-center justify-between rounded-2xl border border-white/8 bg-white/4 p-4 transition hover:border-emerald-500/30 md:col-span-2"
        >
          <div>
            <p className="font-syne text-[15px] font-bold text-white">Partner Directory</p>
            <p className="mt-1 text-[12px] text-white/50">
              Onboard approved wholesalers and suppliers and manage their portal access.
            </p>
          </div>
          <Building2 className="h-5 w-5 shrink-0 text-emerald-400" />
        </Link>
      </div>
      <div>
        <div className="flex items-center justify-between mb-3">
          <p className="text-[10px] font-semibold uppercase tracking-[0.14em] text-white/40">Recent Requests</p>
          <button onClick={() => onTab("requests")} className="text-[12px] text-emerald-400 hover:underline">View all</button>
        </div>
        <div className="rounded-2xl border border-white/8 bg-white/4 divide-y divide-white/6">
          {loading ? (
            <div className="px-4 py-6 text-center text-[13px] text-white/30">Loading…</div>
          ) : requests.slice(0, 5).length === 0 ? (
            <div className="px-4 py-6 text-center text-[13px] text-white/30">No requests yet</div>
          ) : (
            requests.slice(0, 5).map((r) => (
              <div key={r.id} className="flex items-center justify-between px-4 py-3">
                <div>
                  <p className="text-[13px] font-medium text-white">{r.product_name}</p>
                  <p className="text-[11px] text-white/40">
                    {r.customer_phone} · {new Date(r.created_at).toLocaleTimeString("en-NG", { hour: "2-digit", minute: "2-digit" })}
                  </p>
                </div>
                <span className={`inline-flex items-center rounded-full border px-2 py-0.5 text-[10px] font-semibold ${REQ_STATUS_COLOR[r.status] ?? "bg-white/8 text-white/50 border-white/12"}`}>
                  {REQ_STATUS_LABEL[r.status] ?? r.status}
                </span>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}

// ── Requests tab ──────────────────────────────────────────────────────────────
function RequestsTab({ requests, loading }: { requests: AdminRequest[]; loading: boolean }) {
  return (
    <div className="space-y-4">
      <h2 className="font-syne text-[18px] font-bold text-white">All Requests</h2>
      <div className="rounded-2xl border border-white/8 bg-white/4 divide-y divide-white/6">
        {loading ? (
          <div className="px-4 py-8 text-center text-[13px] text-white/30">Loading…</div>
        ) : requests.length === 0 ? (
          <div className="px-4 py-8 text-center text-[13px] text-white/30">No requests</div>
        ) : (
          requests.map((r) => (
            <div key={r.id} className="flex items-center justify-between px-4 py-4">
              <div className="min-w-0 flex-1 mr-3">
                <p className="text-[14px] font-semibold text-white truncate">{r.product_name}</p>
                <p className="text-[11px] text-white/40 mt-0.5">
                  {r.customer_phone} · {new Date(r.created_at).toLocaleDateString("en-NG")}
                </p>
              </div>
              <span className={`shrink-0 inline-flex items-center rounded-full border px-2.5 py-0.5 text-[10px] font-semibold ${REQ_STATUS_COLOR[r.status] ?? "bg-white/8 text-white/50 border-white/12"}`}>
                {REQ_STATUS_LABEL[r.status] ?? r.status}
              </span>
            </div>
          ))
        )}
      </div>
    </div>
  );
}

// ── Orders tab ────────────────────────────────────────────────────────────────
function OrdersTab({ orders, loading }: { orders: AdminOrder[]; loading: boolean }) {
  const ORDER_STATUS_COLOR: Record<string, string> = {
    DELIVERED: "bg-emerald-500/15 text-emerald-400 border-emerald-500/25",
    PROCESSING: "bg-emerald-500/15 text-emerald-400 border-emerald-500/25",
    AWAITING_PAYMENT: "bg-amber-500/15 text-amber-400 border-amber-500/25",
    CANCELLED: "bg-red-500/15 text-red-400 border-red-500/25",
    NEW: "bg-white/8 text-white/50 border-white/12",
  };
  const FULFILLMENT_LABEL: Record<string, string> = {
    in_stock: "In stock now",
    source_from_network: "Source from network",
    sourcing_requested: "Sourcing requested",
    partner_confirmed: "Partner confirmed",
    partner_rejected: "Partner rejected",
    pack_ready: "Pack ready",
    dispatch_assigned: "Dispatch assigned",
    picked_up: "Picked up",
    delivered: "Delivered",
    failed: "Failed",
  };
  return (
    <div className="space-y-4">
      <h2 className="font-syne text-[18px] font-bold text-white">All Orders</h2>
      <div className="rounded-2xl border border-white/8 bg-white/4 divide-y divide-white/6">
        {loading ? (
          <div className="px-4 py-8 text-center text-[13px] text-white/30">Loading…</div>
        ) : orders.length === 0 ? (
          <div className="px-4 py-8 text-center text-[13px] text-white/30">No orders yet</div>
        ) : (
          orders.map((o) => (
            <div key={o.id} className="flex items-center justify-between px-4 py-4">
              <div>
                <p className="text-[14px] font-semibold text-white">{o.code}</p>
                <p className="text-[11px] text-white/40 mt-0.5">
                  ₦{Number(o.total).toLocaleString()} · {new Date(o.created_at).toLocaleDateString("en-NG")}
                </p>
                {o.customer_facing_status && (
                  <p className="text-[11px] text-emerald-300/75 mt-1">{o.customer_facing_status}</p>
                )}
              </div>
              <div className="text-right">
                <span className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-[10px] font-semibold ${ORDER_STATUS_COLOR[o.status] ?? "bg-white/8 text-white/50 border-white/12"}`}>
                  {o.status}
                </span>
                {o.fulfillment_status && (
                  <p className="mt-1 text-[10px] text-white/40">
                    {FULFILLMENT_LABEL[o.fulfillment_status] ?? o.fulfillment_status}
                  </p>
                )}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}

// ── Root component ────────────────────────────────────────────────────────────
export default function AdminPage() {
  const [admin, setAdmin] = useState<AdminMe | null>(null);
  const [checked, setChecked] = useState(false);

  useEffect(() => {
    const token = getAdminToken();
    if (token) {
      adminFetch<AdminMe>("/admin/me")
        .then((me) => setAdmin(me))
        .catch(() => clearAdminToken())
        .finally(() => setChecked(true));
    } else {
      setChecked(true);
    }
  }, []);

  if (!checked) return null;
  if (admin) {
    return <Dashboard admin={admin} />;
  }
  return <StaffOtpGate onLogin={(me) => setAdmin(me)} />;
}
