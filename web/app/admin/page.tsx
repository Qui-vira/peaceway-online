"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  LayoutGrid, ClipboardList, Package, Users, DollarSign, ShoppingBag,
  LogOut, ChevronRight,
} from "lucide-react";
const ADMIN_KEY = "pw_admin_session";
const ADMIN_PWD_KEY = "pw_admin_pwd";

function adminFetch<T>(path: string, pwd: string, options: RequestInit = {}): Promise<T> {
  const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";
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
  { key: "requests", icon: ClipboardList, label: "Requests" },
  { key: "orders", icon: Package, label: "Orders" },
  { key: "customers", icon: Users, label: "Customers" },
  { key: "payments", icon: DollarSign, label: "Payments" },
  { key: "catalog", icon: ShoppingBag, label: "Catalog" },
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
          <div className="py-10 text-center text-white/40">Catalog management — coming soon</div>
        )}
      </main>
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
