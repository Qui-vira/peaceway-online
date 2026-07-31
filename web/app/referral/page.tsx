"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Copy, Share2, Gift } from "lucide-react";
import { apiFetch, isAuthError } from "@/lib/api";
import { AppShell } from "@/components/app/app-shell";
import { GuestWall, LoadFailed, SectionLabel } from "@/components/app/ui";
import { TactileButton } from "@/components/app/tactile-button";
import { siteConfig } from "@/lib/constants";
import { usePageTitle } from "@/components/app/page-title";

interface MeResponse {
  full_name: string | null;
  phone: string | null;
  referral_code: string | null;
  referral_count?: number;
}

export default function ReferralPage() {
  usePageTitle("Refer a Friend");
  const [me, setMe] = useState<MeResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [copied, setCopied] = useState(false);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    // `?referral=1` asks the server to mint the code if this customer has none
    // yet and to count their referrals. The code used to be derived here, in
    // the browser, from the customer's own name and phone - which meant the
    // code they were told to share had never been stored anywhere and could
    // never be matched to anyone who used it.
    apiFetch<MeResponse>("/me?referral=1")
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
  // `failed` was set here and never read: the page fell through to the guest
  // wall, so a network blip told a signed-in customer they were signed out.
  if (failed)
    return (
      <AppShell>
        <div className="px-5 pt-6">
          <LoadFailed
            what="your referral code"
            onRetry={() => window.location.reload()}
          />
        </div>
      </AppShell>
    );
  if (!me) return <AppShell><GuestWall message="Your referral code is tied to your account." /></AppShell>;

  const code = me.referral_code;
  const referralLink = code ? `${siteConfig.url}?ref=${code}` : null;

  async function copyLink() {
    if (!referralLink) return;
    try {
      await navigator.clipboard.writeText(referralLink);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // fallback - silent
    }
  }

  async function share() {
    if (!referralLink) return;
    if (typeof navigator !== "undefined" && navigator.share) {
      try {
        await navigator.share({
          title: "Peaceway Online",
          text: `Order genuine medicine from Peaceway Pharmacy, Lagos - use my code ${code}.`,
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
          <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-emerald-400/80 mb-2">
            Your referral code
          </p>
          <p className="font-syne text-2xl font-bold tracking-wider text-emerald-400">{code}</p>
          <p className="mt-2 text-[12px] text-[#b1bdb0]">
            Share it with anyone who needs a pharmacy they can trust
          </p>
        </div>

        {/* One stat, because one is all the system can actually answer.
            The second tile used to read "Rewards earned" and computed
            `referral_rewards × 200` from a field the API has never returned, so
            it displayed ₦0 to everyone, forever, next to a promise of ₦200 a
            head. Referrals are now recorded against the customer who made them;
            what a referral is worth is a decision the pharmacy makes off-app,
            and the copy says so rather than inventing a balance. */}
        <div className="rounded-2xl border border-white/8 bg-white/4 p-4 text-center">
          <p className="text-[22px] font-bold text-white">{me.referral_count ?? 0}</p>
          <p className="mt-0.5 text-[11px] text-[#b1bdb0]">
            {me.referral_count === 1 ? "Friend joined with your code" : "Friends joined with your code"}
          </p>
        </div>

        {/* How it works */}
        <div className="rounded-2xl border border-white/8 bg-white/4 px-4 py-4 space-y-3">
          <SectionLabel>How it works</SectionLabel>
          {[
            "Share your link or code with a friend",
            "They sign up and their first order is linked to you",
            "Mention your code when you order and a pharmacist applies your thank-you",
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
        <TactileButton onClick={share} className="w-full">
          <Share2 className="h-4 w-4" />
          Share my code
        </TactileButton>
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
