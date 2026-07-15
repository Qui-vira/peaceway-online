"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Copy, Share2, Gift } from "lucide-react";
import { apiFetch, isAuthError } from "@/lib/api";
import { AppShell } from "@/components/app/app-shell";
import { GuestWall, LoadFailed, SectionLabel } from "@/components/app/ui";

interface MeResponse {
  full_name: string | null;
  phone: string | null;
  referral_code: string | null;
  referral_count?: number;
  referral_rewards?: number;
}

function generateCode(name: string, phone: string): string {
  const initials = (name ?? "").split(" ").map((w) => w[0] ?? "").join("").toUpperCase().slice(0, 3);
  const suffix = (phone ?? "").slice(-3);
  return `PW${initials}${suffix}`;
}

export default function ReferralPage() {
  const [me, setMe] = useState<MeResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [copied, setCopied] = useState(false);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    apiFetch<MeResponse>("/me")
      .then(setMe)
      // setMe(null) renders the signed-out view. Only assert that when the
      // backend actually said so.
      .catch((e) => {
        if (isAuthError(e)) setMe(null);
        else setFailed(true);
      })
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <AppShell><div className="py-20" /></AppShell>;
  if (!me) return <AppShell><GuestWall message="Sign in to access your referral code." /></AppShell>;

  const code = me.referral_code ?? generateCode(me.full_name ?? "", me.phone ?? "");
  const referralLink = `https://peaceway.online?ref=${code}`;

  async function copyLink() {
    try {
      await navigator.clipboard.writeText(referralLink);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // fallback - silent
    }
  }

  async function share() {
    if (typeof navigator !== "undefined" && navigator.share) {
      try {
        await navigator.share({
          title: "Peaceway Online",
          text: `Order medicines online with Peaceway Online - use my code ${code} and get ₦200 off your first order!`,
          url: referralLink,
        });
      } catch {
        // user cancelled share
      }
    } else {
      copyLink();
    }
  }

  return (
    <AppShell back={{ title: "Refer a Friend", fallbackHref: "/app" }}>
      <div className="space-y-6 px-5 pt-6 pb-8">
        <h1 className="font-syne text-[22px] font-bold text-white">Refer a Friend</h1>

        {/* Referral card */}
        <div
          className="rounded-2xl border border-emerald-500/25 p-6 text-center"
          style={{ background: "linear-gradient(135deg, rgba(52,217,138,0.12), rgba(52,217,138,0.04))" }}
        >
          <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-full border border-emerald-500/30 bg-emerald-500/15">
            <Gift className="h-5 w-5 text-emerald-400" />
          </div>
          <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-emerald-400/80 mb-2">
            Your referral code
          </p>
          <p className="font-syne text-[28px] font-bold tracking-wider text-emerald-400">{code}</p>
          <p className="mt-2 text-[12px] text-[#b1bdb0]">Friends get ₦200 off their first order</p>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-2 gap-3">
          <div className="rounded-2xl border border-white/8 bg-white/4 p-4 text-center">
            <p className="text-[22px] font-bold text-white">{me.referral_count ?? 0}</p>
            <p className="text-[11px] text-[#b1bdb0] mt-0.5">Friends referred</p>
          </div>
          <div className="rounded-2xl border border-white/8 bg-white/4 p-4 text-center">
            <p className="text-[22px] font-bold text-emerald-400">
              ₦{((me.referral_rewards ?? 0) * 200).toLocaleString()}
            </p>
            <p className="text-[11px] text-[#b1bdb0] mt-0.5">Rewards earned</p>
          </div>
        </div>

        {/* How it works */}
        <div className="rounded-2xl border border-white/8 bg-white/4 px-4 py-4 space-y-3">
          <SectionLabel>How it works</SectionLabel>
          {[
            "Share your code with friends",
            "They get ₦200 off their first order",
            "You earn ₦200 credit when they order",
          ].map((step, i) => (
            <div key={i} className="flex items-center gap-3">
              <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-emerald-500/15 text-[11px] font-bold text-emerald-400">
                {i + 1}
              </span>
              <p className="text-[13px] text-white/70">{step}</p>
            </div>
          ))}
        </div>

        {/* CTAs */}
        <button
          onClick={share}
          className="flex w-full items-center justify-center gap-2 rounded-xl bg-emerald-500 py-3.5 text-sm font-semibold text-black transition hover:bg-emerald-400"
        >
          <Share2 className="h-4 w-4" />
          Share my code
        </button>
        <button
          onClick={copyLink}
          className="flex w-full items-center justify-center gap-2 rounded-xl border border-white/10 py-3 text-[13px] text-white/50 transition hover:border-white/20 hover:text-white/70"
        >
          <Copy className="h-3.5 w-3.5" />
          {copied ? "Copied!" : "Copy referral link"}
        </button>
      </div>
    </AppShell>
  );
}
