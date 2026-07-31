"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { ArrowLeft, Plus, X, AlertTriangle } from "lucide-react";
import { localDateKey } from "@/lib/date";
import { AppShell } from "@/components/app/app-shell";
import { GuestWall, SectionLabel, Spinner } from "@/components/app/ui";
import { getMe } from "@/lib/api/customers";
import { isAuthError } from "@/lib/api";
import { createReminder } from "@/lib/api/reminders";
import { TactileButton } from "@/components/app/tactile-button";
import { usePageTitle } from "@/components/app/page-title";

type Step = 1 | 2 | 3;

function StepDots({ current }: { current: Step }) {
  return (
    // The dots carry the only "where am I" signal in a three-step flow, and
    // they carried it in colour and width alone - nothing to announce, nothing
    // to read. The label states the position; the dots stay decorative.
    <div
      className="flex items-center justify-center gap-2"
      role="group"
      aria-label={`Step ${current} of 3`}
    >
      {([1, 2, 3] as const).map((n) => (
        <span
          key={n}
          aria-hidden="true"
          className={`h-2 rounded-full transition-all ${
            n === current
              ? "w-6 bg-emerald-500"
              : n < current
              ? "w-2 bg-emerald-500/60"
              : "w-2 bg-white/20"
          }`}
        />
      ))}
    </div>
  );
}

const PRESET_TIMES = ["06:00", "08:00", "12:00", "14:00", "18:00", "21:00"];

export default function NewReminderPage() {
  usePageTitle("Add reminder");
  const router = useRouter();

  // Every sibling route walls a signed-out visitor immediately; this one let
  // them fill in three steps and fail at submit. Same gate, same component.
  const [authState, setAuthState] = useState<"checking" | "guest" | "ok">("checking");

  useEffect(() => {
    getMe()
      .then(() => setAuthState("ok"))
      .catch((e) => setAuthState(isAuthError(e) ? "guest" : "ok"));
  }, []);

  const [step, setStep] = useState<Step>(1);
  const [name, setName] = useState("");
  const [instructions, setInstructions] = useState("");
  const [times, setTimes] = useState<string[]>([]);
  const [customTime, setCustomTime] = useState("");
  const [startDate, setStartDate] = useState(localDateKey());
  const [hasEnd, setHasEnd] = useState(false);
  const [endDate, setEndDate] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  function addTime(t: string) {
    if (!t || times.includes(t)) return;
    setTimes((prev) => [...prev, t].sort());
  }

  function removeTime(t: string) {
    setTimes((prev) => prev.filter((x) => x !== t));
  }

  async function handleSubmit() {
    setError("");
    setSubmitting(true);
    try {
      const rem = await createReminder({
        medicine_name: name.trim(),
        instructions_text: instructions.trim() || undefined,
        times,
        start_date: startDate,
        end_date: hasEnd && endDate ? endDate : undefined,
        timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
      });
      router.push(`/reminders/${rem.id}`);
    } catch {
      setError("We couldn't save your reminder. Nothing was set — please try again.");
      setSubmitting(false);
    }
  }

  const today = localDateKey();

  if (authState === "checking") return <AppShell><Spinner /></AppShell>;
  if (authState === "guest")
    return (
      <AppShell>
        <GuestWall message="So your reminders follow you to any phone you sign in on." />
      </AppShell>
    );

  return (
    <AppShell>
      <div className="px-5 pt-8 pb-8 space-y-6">
        {/* Header */}
        <div className="flex items-center gap-3">
          {/* h-11, not h-9: this was a 36px, unlabelled, focus-ring-less back
              button - a third implementation of a control the app already has
              twice, and the smallest of the three. */}
          <button
            onClick={() => (step === 1 ? router.back() : setStep((s) => (s - 1) as Step))}
            aria-label={step === 1 ? "Go back" : "Previous step"}
            className="flex h-11 w-11 items-center justify-center rounded-full border border-white/10 bg-white/5 transition hover:border-white/20 focus-visible:outline-none focus-visible:ring-[3px] focus-visible:ring-[rgba(52,217,138,0.5)]"
          >
            <ArrowLeft className="h-4 w-4 text-white/70" />
          </button>
          <div className="flex-1 text-center">
            <h1 className="font-syne text-[19px] font-bold text-white">Add reminder</h1>
          </div>
          <div className="h-11 w-11" />
        </div>

        <StepDots current={step} />

        {/* Step 1 - What */}
        {step === 1 && (
          <div className="space-y-4">
            <SectionLabel>Medication Info</SectionLabel>

            <div className="rounded-2xl border border-white/8 bg-white/4 px-4 py-4 space-y-4">
              <div className="space-y-1.5">
                <label className="block text-[11px] font-medium text-white/50">
                  Medicine Name <span className="text-red-400">*</span>
                </label>
                <input
                  autoFocus
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="e.g. Paracetamol 500mg"
                  className="w-full rounded-xl border border-white/10 bg-white/5 px-4 py-3 text-base text-white placeholder-[#b1bdb0] outline-none focus:border-emerald-500/50 focus:ring-1 focus:ring-emerald-500/20"
                />
              </div>

              <div className="space-y-1.5">
                <label className="block text-[11px] font-medium text-white/50">
                  Instructions (optional)
                </label>
                <textarea
                  value={instructions}
                  onChange={(e) => setInstructions(e.target.value)}
                  placeholder="e.g. Take with food, twice daily"
                  rows={3}
                  className="w-full resize-none rounded-xl border border-white/10 bg-white/5 px-4 py-3 text-base text-white placeholder-[#b1bdb0] outline-none focus:border-emerald-500/50 focus:ring-1 focus:ring-emerald-500/20"
                />
              </div>
            </div>

            {/* Disclaimer */}
            <div className="flex items-start gap-2.5 rounded-xl border border-amber-500/25 bg-amber-500/8 px-3.5 py-2.5">
              <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0 text-amber-400" />
              <p className="text-[11px] leading-relaxed text-amber-300/80">
                Personal reminder only. Not medical advice. Consult your pharmacist.
              </p>
            </div>

            <TactileButton
              disabled={!name.trim()}
              onClick={() => setStep(2)}
              className="w-full disabled:opacity-40"
            >
              Next
            </TactileButton>
          </div>
        )}

        {/* Step 2 - When */}
        {step === 2 && (
          <div className="space-y-4">
            <SectionLabel>Schedule</SectionLabel>

            <div className="rounded-2xl border border-white/8 bg-white/4 px-4 py-4 space-y-4">
              {/* Time preset chips */}
              <div className="space-y-2">
                <label className="block text-[11px] font-medium text-white/50">
                  Reminder Times <span className="text-red-400">*</span>
                </label>
                <div className="flex flex-wrap gap-2">
                  {PRESET_TIMES.map((t) => (
                    <button
                      key={t}
                      onClick={() => (times.includes(t) ? removeTime(t) : addTime(t))}
                      className={`rounded-full border px-3 py-1 text-[12px] font-medium transition ${
                        times.includes(t)
                          ? "border-emerald-500/50 bg-emerald-500/20 text-emerald-400"
                          : "border-white/10 bg-white/5 text-white/60 hover:border-white/20"
                      }`}
                    >
                      {t}
                    </button>
                  ))}
                </div>
              </div>

              {/* Custom time */}
              <div className="flex gap-2">
                <input
                  type="time"
                  value={customTime}
                  onChange={(e) => setCustomTime(e.target.value)}
                  className="flex-1 rounded-xl border border-white/10 bg-white/5 px-4 py-2.5 text-base text-white outline-none focus:border-emerald-500/50"
                />
                <button
                  onClick={() => {
                    addTime(customTime);
                    setCustomTime("");
                  }}
                  disabled={!customTime}
                  className="flex items-center gap-1 rounded-xl border border-white/10 bg-white/5 px-3 py-2.5 text-sm text-white/60 transition hover:border-emerald-500/30 hover:text-emerald-400 disabled:opacity-30"
                >
                  <Plus className="h-4 w-4" />
                </button>
              </div>

              {/* Selected times */}
              {times.length > 0 && (
                <div className="flex flex-wrap gap-2">
                  {times.map((t) => (
                    <span
                      key={t}
                      className="inline-flex items-center gap-1.5 rounded-full border border-emerald-500/30 bg-emerald-500/15 pl-3 pr-2 py-1 text-[12px] font-medium text-emerald-400"
                    >
                      {t}
                      <button onClick={() => removeTime(t)} className="opacity-60 hover:opacity-100">
                        <X className="h-3 w-3" />
                      </button>
                    </span>
                  ))}
                </div>
              )}
            </div>

            <div className="rounded-2xl border border-white/8 bg-white/4 px-4 py-4 space-y-4">
              <div className="space-y-1.5">
                <label className="block text-[11px] font-medium text-white/50">Start Date</label>
                <input
                  type="date"
                  value={startDate}
                  min={today}
                  onChange={(e) => setStartDate(e.target.value)}
                  className="w-full rounded-xl border border-white/10 bg-white/5 px-4 py-3 text-base text-white outline-none focus:border-emerald-500/50"
                />
              </div>

              <div className="flex items-center justify-between">
                <span className="text-[13px] text-white/60">Has an end date?</span>
                <button
                  onClick={() => setHasEnd((v) => !v)}
                  className={`relative h-6 w-11 rounded-full transition-colors ${
                    hasEnd ? "bg-emerald-500" : "bg-white/15"
                  }`}
                >
                  <span
                    className={`absolute top-0.5 left-0.5 h-5 w-5 rounded-full bg-white shadow transition-transform ${
                      hasEnd ? "translate-x-5" : "translate-x-0"
                    }`}
                  />
                </button>
              </div>

              {hasEnd && (
                <div className="space-y-1.5">
                  <label className="block text-[11px] font-medium text-white/50">End Date</label>
                  <input
                    type="date"
                    value={endDate}
                    min={startDate}
                    onChange={(e) => setEndDate(e.target.value)}
                    className="w-full rounded-xl border border-white/10 bg-white/5 px-4 py-3 text-base text-white outline-none focus:border-emerald-500/50"
                  />
                </div>
              )}
            </div>

            <TactileButton
              disabled={times.length === 0}
              onClick={() => setStep(3)}
              className="w-full disabled:opacity-40"
            >
              Next
            </TactileButton>
          </div>
        )}

        {/* Step 3 - Review */}
        {step === 3 && (
          <div className="space-y-4">
            <SectionLabel>Review</SectionLabel>

            <div className="rounded-2xl border border-white/8 bg-white/4 px-5 py-6 flex flex-col items-center gap-3 text-center">
              <span className="flex h-14 w-14 items-center justify-center rounded-2xl border border-emerald-500/25 bg-emerald-500/12">
                <svg width="32" height="32" viewBox="0 0 48 48" fill="none">
                  <rect x="6" y="13" width="36" height="26" rx="4" fill="rgba(52,217,138,0.18)" stroke="#34d98a" strokeWidth="2"/>
                  <circle cx="17" cy="23" r="5" fill="rgba(52,217,138,0.45)" stroke="#34d98a" strokeWidth="1.5"/>
                  <circle cx="31" cy="23" r="5" fill="rgba(52,217,138,0.45)" stroke="#34d98a" strokeWidth="1.5"/>
                  <circle cx="17" cy="33" r="5" fill="rgba(52,217,138,0.45)" stroke="#34d98a" strokeWidth="1.5"/>
                  <circle cx="31" cy="33" r="5" fill="rgba(52,217,138,0.45)" stroke="#34d98a" strokeWidth="1.5"/>
                </svg>
              </span>
              <div>
                <p className="font-syne text-lg font-bold text-white">{name}</p>
                {instructions && (
                  <p className="mt-1 text-[13px] text-white/50">{instructions}</p>
                )}
              </div>
              <div className="flex flex-wrap justify-center gap-1.5 mt-1">
                {times.map((t) => (
                  <span
                    key={t}
                    className="inline-flex items-center rounded-full border border-emerald-500/25 bg-emerald-500/15 px-2.5 py-0.5 text-[11px] font-medium text-emerald-400"
                  >
                    {t}
                  </span>
                ))}
              </div>
              <p className="text-[12px] text-[#b1bdb0]">
                From {startDate}
                {hasEnd && endDate ? ` → ${endDate}` : " · Ongoing"}
              </p>
            </div>

            {error && (
              <p className="text-center text-[13px] text-red-400">{error}</p>
            )}

            <TactileButton
              disabled={submitting}
              onClick={handleSubmit}
              className="w-full min-h-[52px] disabled:opacity-60"
            >
              {submitting ? "Setting reminder…" : "Set Reminder"}
            </TactileButton>

            <button
              onClick={() => setStep(2)}
              className="block w-full text-center text-[13px] text-[#b1bdb0] hover:text-[#dcdddb]"
            >
              ← Edit Schedule
            </button>
          </div>
        )}
      </div>
    </AppShell>
  );
}
