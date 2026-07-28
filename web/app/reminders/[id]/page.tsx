"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { ArrowLeft, Clock, CalendarPlus } from "lucide-react";
import {
  getReminder,
  pauseReminder,
  resumeReminder,
  stopReminder,
  deleteReminder,
  type MedicationReminder,
} from "@/lib/api/reminders";
import { AppShell } from "@/components/app/app-shell";
import {
  ReminderStatusBadge,
  SectionLabel,
  Spinner,
  TimeChip,
} from "@/components/app/ui";
import { GenericIcon } from "@/components/app/drug-icons";
import { TactileButton } from "@/components/app/tactile-button";

type State =
  | { kind: "loading" }
  | { kind: "error"; message: string }
  | { kind: "ready"; reminder: MedicationReminder };

/** Build a Google Calendar deep-link for one occurrence (first time slot).
 *  Opens pre-filled in browser - no OAuth needed. */
function buildGCalUrl(r: MedicationReminder): string {
  const firstTime = r.times[0] ?? "08:00";
  const [hh, mm] = firstTime.split(":").map(Number);

  // Build start datetime on start_date at firstTime (local, no TZ offset needed - GCal handles it)
  const dateStr = r.start_date.replace(/-/g, "");
  const pad = (n: number) => String(n).padStart(2, "0");
  const startDt = `${dateStr}T${pad(hh)}${pad(mm)}00`;
  // Duration: 15 minutes
  const endMin = mm + 15;
  const endHh = hh + Math.floor(endMin / 60);
  const endDt = `${dateStr}T${pad(endHh % 24)}${pad(endMin % 60)}00`;

  const title = encodeURIComponent(`💊 ${r.medicine_name}`);
  const details = encodeURIComponent(
    r.instructions_text ? r.instructions_text : `Medication reminder set via Peaceway Online.`
  );

  // Daily recurrence; until end_date if set
  const until = r.end_date ? `UNTIL=${r.end_date.replace(/-/g, "")}T235959Z` : "";
  const rrule = encodeURIComponent(`RRULE:FREQ=DAILY${until ? `;${until}` : ""}`);

  return (
    `https://calendar.google.com/calendar/render?action=TEMPLATE` +
    `&text=${title}` +
    `&dates=${startDt}/${endDt}` +
    `&details=${details}` +
    `&recur=${rrule}`
  );
}

export default function ReminderDetailPage() {
  const params = useParams();
  const router = useRouter();
  const id = params?.id as string;

  const [state, setState] = useState<State>({ kind: "loading" });
  const [acting, setActing] = useState(false);
  const [confirmStop, setConfirmStop] = useState(false);

  useEffect(() => {
    if (!id) return;
    getReminder(id)
      .then((r) => setState({ kind: "ready", reminder: r }))
      .catch(() =>
        setState({ kind: "error", message: "Could not load this reminder." })
      );
  }, [id]);

  async function act(fn: () => Promise<MedicationReminder>) {
    setActing(true);
    try {
      const updated = await fn();
      setState({ kind: "ready", reminder: updated });
    } catch {
      // silently ignore - user can retry
    } finally {
      setActing(false);
      setConfirmStop(false);
    }
  }

  async function handleDelete() {
    setActing(true);
    try {
      await deleteReminder(id);
      router.push("/reminders");
    } catch {
      setActing(false);
    }
  }

  if (state.kind === "loading") return <AppShell><Spinner /></AppShell>;

  if (state.kind === "error") {
    return (
      <AppShell>
        <div className="flex flex-col items-center gap-4 px-5 py-20 text-center">
          <p className="text-white/60">{state.message}</p>
          <Link href="/reminders" className="text-sm text-emerald-400 hover:underline">
            ← Back to Medications
          </Link>
        </div>
      </AppShell>
    );
  }

  const { reminder } = state;
  const isActive = reminder.status === "ACTIVE";
  const isPaused = reminder.status === "PAUSED";
  const isDone = reminder.status === "STOPPED" || reminder.status === "COMPLETED";
  const gcalUrl = buildGCalUrl(reminder);

  return (
    <AppShell>
      <div className="pb-8 space-y-6">
        {/* Sub-header */}
        <div className="flex items-center gap-3 px-5 pt-8">
          <Link
            href="/reminders"
            className="flex h-9 w-9 items-center justify-center rounded-full border border-white/10 bg-white/5"
          >
            <ArrowLeft className="h-4 w-4 text-white/70" />
          </Link>
          <p className="flex-1 truncate text-[13px] text-[#b1bdb0]">My Medications</p>
        </div>

        {/* Hero */}
        <div className="flex flex-col items-center gap-3 px-5">
          <span className="flex h-20 w-20 items-center justify-center rounded-2xl border border-emerald-500/25 bg-emerald-500/12">
            <GenericIcon size={44} />
          </span>
          <ReminderStatusBadge status={reminder.status} />
          <h1 className="font-syne text-[22px] font-bold text-white text-center leading-tight">
            {reminder.medicine_name}
          </h1>
          {reminder.instructions_text && (
            <p className="text-[13px] text-white/50 text-center max-w-xs">
              {reminder.instructions_text}
            </p>
          )}
        </div>

        {/* Next dose / paused notice */}
        <div className="mx-5">
          {isActive && reminder.next_run_at ? (
            <div className="flex items-center gap-3 rounded-2xl border border-emerald-500/20 bg-emerald-500/8 px-4 py-3.5">
              <Clock className="h-4 w-4 shrink-0 text-emerald-400" />
              <div>
                <p className="text-[11px] font-medium uppercase tracking-wide text-emerald-400">
                  Next dose
                </p>
                <p className="text-sm font-semibold text-white">
                  {new Date(reminder.next_run_at).toLocaleTimeString([], {
                    hour: "2-digit",
                    minute: "2-digit",
                  })}
                </p>
              </div>
            </div>
          ) : isPaused ? (
            <div className="flex items-center gap-3 rounded-2xl border border-amber-500/20 bg-amber-500/8 px-4 py-3.5">
              <Clock className="h-4 w-4 shrink-0 text-amber-400" />
              <p className="text-sm text-amber-300">Paused - no upcoming doses</p>
            </div>
          ) : null}
        </div>

        {/* Schedule */}
        <div className="px-5 space-y-3">
          <SectionLabel>Schedule</SectionLabel>
          <div className="flex flex-wrap gap-2">
            {reminder.times.map((t) => (
              <TimeChip key={t} time={t} status="upcoming" />
            ))}
          </div>
          <p className="text-[12px] text-[#b1bdb0]">
            From {reminder.start_date}
            {reminder.end_date ? ` → ${reminder.end_date}` : " · Ongoing"}
          </p>

          {/* Google Calendar CTA */}
          <a
            href={gcalUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="mt-1 inline-flex items-center gap-2 rounded-xl border border-white/10 bg-white/4 px-4 py-2.5 text-[13px] font-medium text-white/60 transition hover:border-white/20 hover:text-white/80"
          >
            <CalendarPlus className="h-4 w-4 text-[#4285F4]" />
            Add to Google Calendar
          </a>
        </div>

        {/* Controls */}
        <div className="px-5 space-y-2.5">
          {isActive && (
            <>
              <button
                disabled={acting}
                onClick={() => act(() => pauseReminder(id))}
                className="w-full rounded-xl border border-amber-500/30 py-3.5 text-sm font-semibold text-amber-400 transition hover:bg-amber-500/10 disabled:opacity-50"
              >
                {acting ? "Updating…" : "Pause Reminder"}
              </button>
              {!confirmStop ? (
                <button
                  disabled={acting}
                  onClick={() => setConfirmStop(true)}
                  className="w-full rounded-xl border border-red-500/25 py-2.5 text-sm font-medium text-red-400 transition hover:bg-red-500/10 disabled:opacity-50"
                >
                  Stop Reminder
                </button>
              ) : (
                <div className="rounded-xl border border-red-500/25 bg-red-500/8 p-4 space-y-3">
                  <p className="text-[13px] text-white/70 text-center">
                    Stop this reminder permanently?
                  </p>
                  <div className="flex gap-2">
                    <button
                      onClick={() => setConfirmStop(false)}
                      className="flex-1 rounded-xl border border-white/10 py-2.5 text-sm text-white/50"
                    >
                      Cancel
                    </button>
                    <button
                      disabled={acting}
                      onClick={() => act(() => stopReminder(id))}
                      className="flex-1 rounded-xl bg-red-500/20 border border-red-500/30 py-2.5 text-sm font-semibold text-red-400 disabled:opacity-50"
                    >
                      {acting ? "Stopping…" : "Yes, Stop"}
                    </button>
                  </div>
                </div>
              )}
            </>
          )}

          {isPaused && (
            <>
              <TactileButton
                disabled={acting}
                onClick={() => act(() => resumeReminder(id))}
                className="w-full disabled:opacity-50"
              >
                {acting ? "Resuming…" : "Resume Reminder"}
              </TactileButton>
              <button
                disabled={acting}
                onClick={() => act(() => stopReminder(id))}
                className="w-full rounded-xl border border-red-500/25 py-2.5 text-sm font-medium text-red-400 transition hover:bg-red-500/10 disabled:opacity-50"
              >
                Stop Reminder
              </button>
            </>
          )}

          {isDone && (
            <Link
              href="/reminders/new"
              className="block w-full rounded-xl border border-emerald-500/30 py-3.5 text-center text-sm font-semibold text-emerald-400 transition hover:bg-emerald-500/10"
            >
              Create Similar Reminder
            </Link>
          )}
        </div>

        {/* Danger zone - delete */}
        <div className="px-5">
          <div className="rounded-2xl border border-white/6 bg-white/3 px-4 py-4">
            <p className="text-[11px] font-semibold uppercase tracking-wide text-[#b1bdb0] mb-3">
              Danger Zone
            </p>
            <button
              disabled={acting}
              onClick={handleDelete}
              className="text-[13px] text-red-400/70 hover:text-red-400 disabled:opacity-50"
            >
              Delete this reminder permanently
            </button>
          </div>
        </div>
      </div>
    </AppShell>
  );
}
