"use client";

import { useEffect, useState } from "react";
import {
  ClipboardList,
  MessageCircle,
  Search,
  Send,
  User,
} from "lucide-react";
import { getMe, type CustomerProfile } from "@/lib/api/customers";
import { AppShell, AppHeader } from "@/components/app/app-shell";
import { ActionCard, GuestWall, Spinner } from "@/components/app/ui";
import { siteConfig } from "@/lib/constants";

export default function AppDashboard() {
  const [me, setMe] = useState<CustomerProfile | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getMe()
      .then(setMe)
      .catch(() => setMe(null))
      .finally(() => setLoading(false));
  }, []);

  return (
    <AppShell>
      {loading ? (
        <Spinner />
      ) : !me ? (
        <>
          <AppHeader
            title="Welcome to Peaceway"
            subtitle="Check medicine availability, ask a pharmacist, and track your requests, right here on the web."
          />
          <GuestWall />
        </>
      ) : (
        <>
          <AppHeader
            title={`Hello, ${me.full_name?.split(" ")[0] ?? "there"}.`}
            subtitle="What would you like to do today?"
          />

          <div className="space-y-3 px-5">
            <ActionCard
              href="/request"
              icon={<Search className="h-5 w-5" />}
              title="Check Medicine Availability"
              description="Tell us what you need and we'll confirm stock"
            />
            <ActionCard
              href="/ask-pharmacist"
              icon={<MessageCircle className="h-5 w-5" />}
              title="Ask a Pharmacist"
              description="Dosage, interactions, side effects, ask freely"
            />
            <ActionCard
              href="/requests"
              icon={<ClipboardList className="h-5 w-5" />}
              title="Track My Requests"
              description="See the status of everything you've asked for"
            />
            <ActionCard
              href="/profile"
              icon={<User className="h-5 w-5" />}
              title="My Profile"
              description={me.phone ?? "Your contact details"}
            />
          </div>

          <div className="px-5 pt-8">
            <p className="mb-3 text-xs font-semibold uppercase tracking-widest text-white/30">
              Prefer Telegram?
            </p>
            <a
              href={siteConfig.telegramBotUrl}
              target="_blank"
              rel="noreferrer noopener"
              className="flex items-center gap-4 rounded-2xl border border-white/8 bg-white/2 px-5 py-4 transition-colors hover:border-white/20"
            >
              <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-white/6 text-white/50">
                <Send className="h-4 w-4" />
              </span>
              <span className="min-w-0 flex-1">
                <span className="block text-sm font-semibold text-white/80">
                  Order on Telegram
                </span>
                <span className="block text-xs text-white/40">
                  Full ordering and delivery tracking live in the bot
                </span>
              </span>
            </a>
          </div>
        </>
      )}
    </AppShell>
  );
}
