"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import {
  LayoutGrid, ClipboardList, Package, Users, DollarSign, ShoppingBag,
  LogOut, Search, Save, RefreshCcw,
} from "lucide-react";
import { getApiBase } from "@/lib/api";
const ADMIN_KEY = "pw_admin_session";
const ADMIN_PWD_KEY = "pw_admin_pwd";

function adminFetch<T>(path: string, pwd: string, options: RequestInit = {}): Promise<T> {
  const API_BASE = getApiBase();
  return fetch(`${API_BASE}${path}`, {
    ...options,
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      "X-Admin-Password": pwd,
      ...(options.headers ?? {}),
    },
  }).then(async (res) => {
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      throw new Error(body?.detail ?? res.statusText);
    }
    return res.json() as Promise<T>;
  });
}

// ── Sidebar items ──────────────────────────────────────────────────────────────
const NAV = [
  { key: "overview", icon: LayoutGrid, label: "Overview" },
  { key: "catalog", icon: ShoppingBag, label: "Inventory" },
  { key: "requests", icon: ClipboardList, label: "Requests" },
  { key: "orders", icon: Package, label: "Orders" },
  { key: "customers", icon: Users, label: "Customers" },
  { key: "payments", icon: DollarSign, label: "Payments" },
];

// ── Types ─────────────────────────────────────────────────────────────────────
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

// ── Login gate ────────────────────────────────────────────────────────────────
function LoginGate({ onLogin }: { onLogin: (pwd: string) => void }) {
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleLogin() {
    setLoading(true);
    setError("");
    try {
      await adminFetch("/admin/auth", password, {
        method: "POST",
        body: JSON.stringify({ password }),
      });
      sessionStorage.setItem(ADMIN_KEY, "1");
      sessionStorage.setItem(ADMIN_PWD_KEY, password);
      onLogin(password);
    } catch {
      setError("Invalid password.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center px-5">
      <div className="w-full max-w-sm space-y-6">
        <div className="text-center">
          <p className="font-syne text-[20px] font-bold text-white">Peaceway Admin</p>
          <p className="mt-1 text-[13px] text-white/40">Staff access only</p>
        </div>
        <div className="rounded-2xl border border-white/8 bg-white/4 p-6 space-y-4">
          <div className="space-y-1.5">
            <label className="text-[11px] font-medium text-white/50">Admin password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleLogin()}
              placeholder="Enter admin password"
              className="w-full rounded-xl border border-white/10 bg-white/5 px-4 py-3 text-sm text-white placeholder-white/30 outline-none focus:border-emerald-500/50"
            />
          </div>
          {error && <p className="text-[13px] text-red-400">{error}</p>}
          <button
            onClick={handleLogin}
            disabled={loading || !password}
            className="w-full rounded-xl bg-emerald-500 py-3.5 text-sm font-semibold text-black disabled:opacity-50"
          >
            {loading ? "Checking…" : "Sign In"}
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Dashboard content ─────────────────────────────────────────────────────────
function Dashboard({ pwd }: { pwd: string }) {
  const [tab, setTab] = useState("overview");
  const [requests, setRequests] = useState<AdminRequest[]>([]);
  const [orders, setOrders] = useState<AdminOrder[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setLoading(true);
    Promise.allSettled([
      adminFetch<AdminRequest[]>("/admin/requests", pwd),
      adminFetch<AdminOrder[]>("/admin/orders", pwd),
    ]).then(([reqRes, ordRes]) => {
      if (reqRes.status === "fulfilled") setRequests(reqRes.value);
      if (ordRes.status === "fulfilled") setOrders(ordRes.value);
      setLoading(false);
    });
  }, [pwd]);

  function signOut() {
    sessionStorage.removeItem(ADMIN_KEY);
    window.location.reload();
  }

  return (
    <div className="flex min-h-screen">
      {/* Sidebar */}
      <aside className="hidden w-[200px] shrink-0 flex-col gap-2 border-r border-white/8 bg-[#0a0b08] px-3 py-6 lg:flex">
        <div className="mb-4 px-3">
          <p className="font-syne text-[13px] font-bold text-white">Peaceway</p>
          <p className="text-[10px] text-white/30">Admin panel</p>
        </div>
        {NAV.map((item) => (
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
        {NAV.map((item) => (
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
          <CatalogTab pwd={pwd} />
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

function CatalogTab({ pwd }: { pwd: string }) {
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
      const result = await adminFetch<AdminProductsResponse>(`/admin/products?${params.toString()}`, pwd);
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
  }, [pwd, q, statusFilter]);

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
      const updated = await adminFetch<AdminProduct>(`/admin/products/${product.id}`, pwd, {
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

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-syne text-[20px] font-bold text-white">Overview</h1>
        <p className="text-[12px] text-white/40 mt-0.5">
          {new Date().toLocaleDateString("en-NG", { weekday: "long", day: "numeric", month: "long" })}
        </p>
      </div>

      {/* Stats grid */}
      <div className="grid grid-cols-2 gap-3">
        {[
          { label: "Pending requests", value: String(pending), note: "Need attention" },
          { label: "Today's orders", value: String(todayOrders.length), note: "New orders" },
          { label: "Today's revenue", value: `₦${todayRevenue.toLocaleString()}`, note: "From orders" },
          { label: "Total requests", value: String(requests.length), note: "All time" },
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

      {/* Recent requests */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <p className="text-[10px] font-semibold uppercase tracking-[0.14em] text-white/40">
            Recent Requests
          </p>
          <button onClick={() => onTab("requests")} className="text-[12px] text-emerald-400 hover:underline">
            View all
          </button>
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
              </div>
              <span className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-[10px] font-semibold ${ORDER_STATUS_COLOR[o.status] ?? "bg-white/8 text-white/50 border-white/12"}`}>
                {o.status}
              </span>
            </div>
          ))
        )}
      </div>
    </div>
  );
}

// ── Root component ────────────────────────────────────────────────────────────
export default function AdminPage() {
  const [pwd, setPwd] = useState<string | null>(null);
  const [checked, setChecked] = useState(false);

  useEffect(() => {
    if (sessionStorage.getItem(ADMIN_KEY) === "1") {
      setPwd(sessionStorage.getItem(ADMIN_PWD_KEY) ?? "");
    }
    setChecked(true);
  }, []);

  if (!checked) return null;

  if (pwd !== null) return <Dashboard pwd={pwd} />;
  return <LoginGate onLogin={(p) => setPwd(p)} />;
}
