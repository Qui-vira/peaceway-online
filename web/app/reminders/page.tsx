"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { Bell, Plus } from "lucide-react";
import { isAuthError } from "@/lib/api";
import { listReminders, type MedicationReminder } from "@/lib/api/reminders";
import { useRouter } from "next/navigation";
import { localDateKey } from "@/lib/date";
import { AppShell } from "@/components/app/app-shell";
import { StaggerItem, StaggerList } from "@/components/app/motion";
import {
  LoadFailed,
  EmptyState,
  GuestWall,
  MedCard,
  SectionLabel,
  SkeletonCard,
} from "@/components/app/ui";
import { GenericIcon } from "@/components/app/drug-icons";

type State =
  | { kind: "loading" }
  | { kind: "guest" }
  | { kind: "failed" }
  | { kind: "ready"; reminders: MedicationReminder[] };

export default function RemindersPage() {
  const router = useRouter();
  const [state, setState] = useState<State>({ kind: "loading" });

  // A 401 means the backend looked and said "not you" - that is real.
  // Anything else (offline, timeout, 500) means nobody looked, so we must
  // not render a guest wall and tell a signed-in customer their account
  // is gone.
  const load = useCallback(() => {
    setState({ kind: "loading" });
    listReminders()
      .then((reminders) => setState({ kind: "ready", reminders }))
      .catch((e) =>
        setState(isAuthError(e) ? { kind: "guest" } : { kind: "failed" })
      );
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const today = localDateKey();
  const todayReminders =
    state.kind === "ready"
      ? state.reminders.filter(
          (r) =>
            r.status === "ACTIVE" &&
            r.start_date <= today &&
            (r.end_date === null || r.end_date >= today)
        )
      : [];

  const allReminders = state.kind === "ready" ? state.reminders : [];

  return (
    <AppShell>
      <div className="space-y-6 px-5 pt-10 pb-6">

        {/* Header */}
        <div className="flex items-center justify-between">
          <h1 className="font-syne text-[22px] font-bold text-white">My Medications</h1>
          <Link
            href="/reminders/new"
            className="inline-flex items-center gap-1.5 rounded-full bg-emerald-500 px-3.5 py-1.5 text-[12px] font-semibold text-black transition hover:bg-emerald-400"
          >
            <Plus className="h-3.5 w-3.5" />
            Add
          </Link>
        </div>

        {state.kind === "loading" && (
          <div className="space-y-3">
            <SkeletonCard lines={3} />
            <SkeletonCard lines={3} />
            <SkeletonCard lines={3} />
          </div>
        )}

        {state.kind === "guest" && <GuestWall />}

        {state.kind === "failed" && <LoadFailed what="your reminders" onRetry={load} />}

        {state.kind === "ready" && allReminders.length === 0 && (
          <EmptyState
            icon={<Bell className="h-6 w-6" />}
            title="No medications yet"
            message="Add your first medication reminder to track your daily doses."
            ctaHref="/reminders/new"
            ctaLabel="Add Medication"
          />
        )}

        {state.kind === "ready" && allReminders.length > 0 && (
          <div className="space-y-6">

            {/* Today's meds */}
            {todayReminders.length > 0 && (
              <div className="space-y-3">
                <SectionLabel>Today</SectionLabel>
                <div className="flex gap-3 overflow-x-auto pb-1 -mx-5 px-5">
                  {todayReminders.map((r) => (
                    <Link key={r.id} href={`/reminders/${r.id}`} className="shrink-0 w-44">
                      <div className="flex flex-col gap-2.5 rounded-2xl border border-white/8 bg-white/4 p-4 h-full hover:border-emerald-500/30">
                        <span className="flex h-10 w-10 items-center justify-center rounded-xl border border-emerald-500/20 bg-emerald-500/12">
                          <GenericIcon size={24} />
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
                </div>
              </div>
            )}

            {/* All medications */}
            <StaggerList className="space-y-3">
              <SectionLabel>All Medications</SectionLabel>
              {allReminders.map((r) => (
                <StaggerItem key={r.id}>
                  <MedCard
                    reminder={r}
                    onClick={() => router.push(`/reminders/${r.id}`)}
                  />
                </StaggerItem>
              ))}
            </StaggerList>
          </div>
        )}
      </div>
    </AppShell>
  );
}
