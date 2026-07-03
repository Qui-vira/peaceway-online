"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Bell, ChevronRight } from "lucide-react";
import { getMe, type CustomerProfile } from "@/lib/api/customers";
import { listTodayReminders, type MedicationReminder } from "@/lib/api/reminders";
import { AppShell } from "@/components/app/app-shell";
import {
  FeatureCard,
  GuestWall,
  MedCard,
  SectionLabel,
  SkeletonCard,
  Spinner,
} from "@/components/app/ui";
import {
  AvailabilityIcon,
  AskPharmacistIcon,
  RequestsListIcon,
  MedicationsIcon,
  TelegramIcon,
} from "@/components/app/drug-icons";
import { siteConfig } from "@/lib/constants";

function todayLabel(): string {
  return new Date().toLocaleDateString("en-NG", {
    weekday: "short",
    day: "numeric",
    month: "short",
  });
}

function TodayMedsSection() {
  const [reminders, setReminders] = useState<MedicationReminder[] | null>(null);

  useEffect(() => {
    listTodayReminders()
      .then(setReminders)
      .catch(() => setReminders([]));
  }, []);

  return (
    <div className="space-y-3 px-5">
      <div className="flex items-center justify-between">
        <SectionLabel>Today&apos;s Medications</SectionLabel>
        <Link
          href="/reminders/new"
          className="rounded-full bg-emerald-500/15 px-3 py-1 text-[11px] font-semibold text-emerald-400 transition hover:bg-emerald-500/25"
        >
          + Add
        </Link>
      </div>

      {reminders === null ? (
        <div className="flex gap-3 overflow-x-auto pb-1">
          <SkeletonCard lines={3} />
        </div>
      ) : reminders.length === 0 ? (
        <div className="flex items-center gap-4 rounded-2xl border border-white/8 bg-white/3 px-5 py-4">
          <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-white/6">
            <Bell className="h-5 w-5 text-white/30" />
          </span>
          <div className="min-w-0 flex-1">
            <p className="text-sm font-medium text-white/70">No reminders today</p>
            <p className="text-xs text-white/35">Track your medications easily</p>
          </div>
          <Link
            href="/reminders/new"
            className="shrink-0 text-xs font-semibold text-emerald-400 transition hover:text-emerald-300"
          >
            Set one <ChevronRight className="inline h-3 w-3" />
          </Link>
        </div>
      ) : (
        <div className="flex gap-3 overflow-x-auto pb-1 -mx-5 px-5">
          {reminders.map((r) => (
            <Link key={r.id} href={`/reminders/${r.id}`} className="shrink-0 w-44">
              <div className="flex flex-col gap-2 rounded-2xl border border-white/8 bg-white/4 p-4 h-full">
                <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border border-emerald-500/20 bg-emerald-500/12">
                  <MedicationsIcon size={22} />
                </span>
                <p className="truncate text-sm font-semibold text-white leading-tight">
                  {r.medicine_name}
                </p>
                {r.times[0] && (
                  <span className="inline-flex w-fit items-center rounded-full border border-emerald-500/25 bg-emerald-500/15 px-2 py-0.5 text-[11px] font-medium text-emerald-400">
                    {r.times[0]}
                  </span>
                )}
              </div>
            </Link>
          ))}
          <Link
            href="/reminders"
            className="flex shrink-0 w-16 flex-col items-center justify-center rounded-2xl border border-white/8 bg-white/3 gap-1"
          >
            <ChevronRight className="h-5 w-5 text-white/30" />
            <span className="text-[10px] text-white/30">All</span>
          </Link>
        </div>
      )}
    </div>
  );
}

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
        <div className="space-y-6 px-5 pt-10 pb-4">
          <div className="space-y-1">
            <p className="text-[10px] font-semibold uppercase tracking-widest text-emerald-400">
              Peaceway Online
            </p>
            <h1 className="font-syne text-[26px] font-bold text-white">
              Welcome to Peaceway.
            </h1>
          </div>
          <GuestWall />
        </div>
      ) : (
        <div className="space-y-7 pb-4">

          {/* Greeting */}
          <div className="px-5 pt-10 pb-2">
            <div className="flex items-center justify-between">
              <p className="text-[10px] font-semibold uppercase tracking-widest text-white/35">
                Peaceway Online
              </p>
              <p className="text-[10px] text-white/30">{todayLabel()}</p>
            </div>
            <h1 className="mt-1 font-syne text-[26px] font-bold leading-tight text-white">
              Hello, {me.full_name?.split(" ")[0] ?? "there"}.
            </h1>
            <div className="mt-4 h-px bg-white/6" />
          </div>

          {/* Today's medications */}
          <TodayMedsSection />

          {/* Feature cards */}
          <div className="px-5 space-y-3">
            <SectionLabel>Quick Access</SectionLabel>
            <div className="grid grid-cols-2 gap-3">
              <FeatureCard
                href="/request"
                icon={<AvailabilityIcon size={28} />}
                title="Check Availability"
                subtitle="Find a medicine"
              />
              <FeatureCard
                href="/ask-pharmacist"
                icon={<AskPharmacistIcon size={28} />}
                title="Ask a Pharmacist"
                subtitle="Dosage & guidance"
              />
              <FeatureCard
                href="/requests"
                icon={<RequestsListIcon size={28} />}
                title="My Requests"
                subtitle="Track availability"
              />
              <FeatureCard
                href="/reminders"
                icon={<MedicationsIcon size={28} />}
                title="My Medications"
                subtitle="Reminders & schedule"
              />
            </div>
          </div>

          {/* Telegram CTA */}
          <div className="px-5">
            <a
              href={siteConfig.telegramBotUrl}
              target="_blank"
              rel="noreferrer noopener"
              className="flex items-center gap-4 rounded-2xl border border-white/6 bg-white/[0.025] px-5 py-4 transition-colors hover:border-white/12"
            >
              <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-white/6">
                <TelegramIcon size={20} />
              </span>
              <span className="min-w-0 flex-1">
                <span className="block text-sm font-semibold text-white/75">
                  Order faster on Telegram
                </span>
                <span className="block text-xs text-white/35">
                  Full ordering & delivery tracking in the bot
                </span>
              </span>
              <ChevronRight className="h-4 w-4 shrink-0 text-white/20" />
            </a>
          </div>

        </div>
      )}
    </AppShell>
  );
}
