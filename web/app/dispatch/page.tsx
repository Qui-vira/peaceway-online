"use client";

import { useCallback, useEffect, useState } from "react";
import {
  DispatchFetchError,
  clearDispatchToken,
  dispatchFetch,
  getDispatchToken,
  setDispatchToken,
} from "@/lib/dispatch-auth";

type Rider = { id: string; name: string; phone: string | null; email: string };

type Delivery = {
  order_id: string;
  order_code: string;
  recipient_name: string | null;
  phone: string | null;
  address: string | null;
  zone: string | null;
  landmark: string | null;
  delivery_window: string | null;
  delivery_status: string;
  handling_flag: string;
  amount_to_collect: string;
  awaiting_pharmacist_verification: boolean;
};

const NEXT: Record<string, string[]> = {
  RIDER_ASSIGNED: ["PICKED_UP"],
  READY_FOR_DISPATCH: ["PICKED_UP"],
  NONE: ["PICKED_UP"],
  PICKED_UP: ["IN_TRANSIT", "FAILED_DELIVERY"],
  IN_TRANSIT: ["NEAR_CUSTOMER", "FAILED_DELIVERY"],
  NEAR_CUSTOMER: ["DELIVERED", "FAILED_DELIVERY"],
};

const LABEL: Record<string, string> = {
  PICKED_UP: "Picked up",
  IN_TRANSIT: "In transit",
  NEAR_CUSTOMER: "Near customer",
  DELIVERED: "Delivered",
  FAILED_DELIVERY: "Failed",
};

const card = "rounded-2xl bg-[#ffffff08] p-4";
const inputCls =
  "w-full rounded-xl bg-[#ffffff0a] px-4 py-3 text-[16px] text-[#dcdddb] outline-none focus:bg-[#ffffff12] placeholder:text-[#868f85]";

function Btn(props: React.ButtonHTMLAttributes<HTMLButtonElement> & { tone?: "green" | "plain" | "danger" }) {
  const { tone = "plain", className = "", ...rest } = props;
  const tones = {
    green: "bg-[#187f4a] text-white hover:bg-[#0f673c]",
    plain: "bg-[#ffffff12] text-[#dcdddb] hover:bg-[#ffffff1f]",
    danger: "bg-[#a80b16] text-white hover:opacity-90",
  } as const;
  return (
    <button
      {...rest}
      className={`rounded-xl px-4 py-3 text-[14px] font-medium transition disabled:opacity-40 ${tones[tone]} ${className}`}
    />
  );
}

function LoginGate({ onToken }: { onToken: (t: string) => void }) {
  const [phase, setPhase] = useState<"email" | "code">("email");
  const [email, setEmail] = useState("");
  const [code, setCode] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  async function sendCode() {
    setBusy(true);
    setErr("");
    try {
      await dispatchFetch("/dispatch/request-otp", { method: "POST", body: JSON.stringify({ email }) });
      setPhase("code");
    } catch {
      setErr("Could not send the code. Try again.");
    } finally {
      setBusy(false);
    }
  }

  async function verify() {
    setBusy(true);
    setErr("");
    try {
      const r = await dispatchFetch<{ token: string }>("/dispatch/verify-otp", {
        method: "POST",
        body: JSON.stringify({ email, code }),
      });
      onToken(r.token);
    } catch (e) {
      setErr(e instanceof DispatchFetchError ? e.message : "Invalid code.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto mt-16 w-full max-w-sm px-5">
      <h1 className="text-[24px] font-semibold text-[#dcdddb]">Rider portal</h1>
      <p className="mt-2 text-[14px] text-[#b1bdb0]">Sign in with the email Peaceway registered for you.</p>
      <div className={`${card} mt-6 space-y-3`}>
        {phase === "email" ? (
          <>
            <input
              className={inputCls}
              type="email"
              inputMode="email"
              placeholder="you@example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
            <Btn tone="green" className="w-full" disabled={busy || !email} onClick={sendCode}>
              {busy ? "Sending..." : "Send code"}
            </Btn>
          </>
        ) : (
          <>
            <input
              className={`${inputCls} tracking-[0.4em]`}
              inputMode="numeric"
              maxLength={6}
              placeholder="000000"
              value={code}
              onChange={(e) => setCode(e.target.value.replace(/\D/g, ""))}
            />
            <Btn tone="green" className="w-full" disabled={busy || code.length < 6} onClick={verify}>
              {busy ? "Checking..." : "Sign in"}
            </Btn>
            <button className="w-full py-1 text-[13px] text-[#868f85]" onClick={() => setPhase("email")}>
              Use a different email
            </button>
          </>
        )}
        {err && <p className="text-[13px] text-[#e88]">{err}</p>}
      </div>
    </div>
  );
}

function Deliveries({ onLogout }: { onLogout: () => void }) {
  const [rider, setRider] = useState<Rider | null>(null);
  const [rows, setRows] = useState<Delivery[]>([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");
  const [podFor, setPodFor] = useState<string | null>(null);
  const [podCode, setPodCode] = useState("");
  const [busyId, setBusyId] = useState<string | null>(null);

  const load = useCallback(async () => {
    setErr("");
    try {
      const [me, deliveries] = await Promise.all([
        dispatchFetch<Rider>("/dispatch/me"),
        dispatchFetch<Delivery[]>("/dispatch/deliveries"),
      ]);
      setRider(me);
      setRows(deliveries);
    } catch (e) {
      if (e instanceof DispatchFetchError && e.status === 401) return onLogout();
      setErr("Could not load your deliveries.");
    } finally {
      setLoading(false);
    }
  }, [onLogout]);

  useEffect(() => {
    load();
  }, [load]);

  function geo(): Promise<{ latitude: number; longitude: number } | null> {
    return new Promise((resolve) => {
      if (!navigator.geolocation) return resolve(null);
      navigator.geolocation.getCurrentPosition(
        (p) => resolve({ latitude: p.coords.latitude, longitude: p.coords.longitude }),
        () => resolve(null),
        { enableHighAccuracy: true, timeout: 8000 }
      );
    });
  }

  async function setStatus(orderId: string, status: string, code?: string) {
    setBusyId(orderId);
    setErr("");
    try {
      const at = await geo();
      await dispatchFetch(`/dispatch/deliveries/${orderId}/status`, {
        method: "POST",
        body: JSON.stringify({ status, code, ...(at ?? {}) }),
      });
      setPodFor(null);
      setPodCode("");
      await load();
    } catch (e) {
      setErr(e instanceof DispatchFetchError ? e.message : "Update failed.");
    } finally {
      setBusyId(null);
    }
  }

  return (
    <div className="mx-auto w-full max-w-md px-4 pb-24 pt-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-[19px] font-semibold text-[#dcdddb]">My deliveries</h1>
          {rider && <p className="text-[13px] text-[#868f85]">{rider.name}</p>}
        </div>
        <button className="text-[13px] text-[#868f85]" onClick={onLogout}>
          Sign out
        </button>
      </div>

      {err && <p className="mt-4 text-[14px] text-[#e88]">{err}</p>}

      {loading ? (
        <p className="mt-10 text-center text-[#868f85]">Loading...</p>
      ) : rows.length === 0 ? (
        <div className={`${card} mt-6 text-center text-[#b1bdb0]`}>No active deliveries right now.</div>
      ) : (
        <div className="mt-5 space-y-4">
          {rows.map((d) => {
            const nexts = NEXT[d.delivery_status] ?? [];
            const collect = Number(d.amount_to_collect);
            return (
              <div key={d.order_id} className={card}>
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="text-[14px] font-semibold text-[#dcdddb]">{d.recipient_name || "Recipient"}</p>
                    <p className="text-[13px] text-[#868f85]">
                      {d.order_code} {d.zone ? `- ${d.zone}` : ""}
                    </p>
                  </div>
                  {d.handling_flag === "RX_ID_CHECK" && (
                    <span className="rounded-full bg-[#a80b1622] px-2.5 py-1 text-[11px] font-medium text-[#e79]">
                      ID check
                    </span>
                  )}
                </div>

                <div className="mt-3 space-y-1 text-[14px] text-[#b1bdb0]">
                  {d.address && <p>{d.address}{d.landmark ? `, ${d.landmark}` : ""}</p>}
                  {d.delivery_window && <p className="text-[#868f85]">Window: {d.delivery_window}</p>}
                  <p className="text-[#dcdddb]">
                    {collect > 0 ? `Collect N${collect.toLocaleString()}` : "Prepaid, collect nothing"}
                  </p>
                  {d.phone && (
                    <a href={`tel:${d.phone}`} className="inline-block pt-1 text-[#34d98a]">
                      Call {d.phone}
                    </a>
                  )}
                </div>

                {d.awaiting_pharmacist_verification && (
                  <p className="mt-3 rounded-xl bg-[#a80b1618] px-3 py-2 text-[13px] text-[#e79]">
                    Awaiting pharmacist verification. Do not travel yet.
                  </p>
                )}

                {podFor === d.order_id ? (
                  <div className="mt-4 space-y-2">
                    <p className="text-[13px] text-[#b1bdb0]">Ask the customer for their delivery code.</p>
                    <input
                      className={`${inputCls} tracking-[0.4em]`}
                      inputMode="numeric"
                      maxLength={6}
                      placeholder="000000"
                      value={podCode}
                      onChange={(e) => setPodCode(e.target.value.replace(/\D/g, ""))}
                    />
                    <div className="flex gap-2">
                      <Btn
                        tone="green"
                        className="flex-1"
                        disabled={busyId === d.order_id || podCode.length < 6}
                        onClick={() => setStatus(d.order_id, "DELIVERED", podCode)}
                      >
                        {busyId === d.order_id ? "Confirming..." : "Confirm delivery"}
                      </Btn>
                      <Btn onClick={() => setPodFor(null)}>Cancel</Btn>
                    </div>
                  </div>
                ) : (
                  <div className="mt-4 flex flex-wrap gap-2">
                    {nexts.map((s) =>
                      s === "DELIVERED" ? null : (
                        <Btn
                          key={s}
                          tone={s === "FAILED_DELIVERY" ? "danger" : "plain"}
                          disabled={busyId === d.order_id || d.awaiting_pharmacist_verification}
                          onClick={() => setStatus(d.order_id, s)}
                        >
                          {LABEL[s]}
                        </Btn>
                      )
                    )}
                    {d.delivery_status === "NEAR_CUSTOMER" && (
                      <Btn
                        tone="green"
                        disabled={d.awaiting_pharmacist_verification}
                        onClick={() => setPodFor(d.order_id)}
                      >
                        Delivered
                      </Btn>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

export default function DispatchPortal() {
  const [token, setToken] = useState<string | null>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    setToken(getDispatchToken());
    setReady(true);
  }, []);

  function logout() {
    clearDispatchToken();
    setToken(null);
  }

  if (!ready) return null;

  return (
    <main className="min-h-screen">
      {token ? (
        <Deliveries onLogout={logout} />
      ) : (
        <LoginGate
          onToken={(t) => {
            setDispatchToken(t);
            setToken(t);
          }}
        />
      )}
    </main>
  );
}
