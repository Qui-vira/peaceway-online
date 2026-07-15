"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { ArrowLeft, Plus, X, AlertTriangle } from "lucide-react";
import { AppShell } from "@/components/app/app-shell";
import { SectionLabel } from "@/components/app/ui";
import { createReminder } from "@/lib/api/reminders";

type Step = 1 | 2 | 3;

function StepDots({ current }: { current: Step }) {
  return (
    <div className="flex items-center justify-center gap-2">
      {([1, 2, 3] as const).map((n) => (
        <span
          key={n}
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
  const router = useRouter();

  const [step, setStep] = useState<Step>(1);
  const [name, setName] = useState("");
  const [instructions, setInstructions] = useState("");
  const [times, setTimes] = useState<string[]>([]);
  const [customTime, setCustomTime] = useState("");
  const [startDate, setStartDate] = useState(
    new Date().toISOString().slice(0, 10)
  );
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
      setError("Something went wrong. Please try again.");
      setSubmitting(false);
    }
  }

  const today = new Date().toISOString().slice(0, 10);

  return (
    <AppShell>
      <div className="px-5 pt-8 pb-8 space-y-6">
        {/* Header */}
        <div className="flex items-center gap-3">
          <button
            onClick={() => (step === 1 ? router.back() : setStep((s) => (s - 1) as Step))}
            className="flex h-9 w-9 items-center justify-center rounded-full border border-white/10 bg-white/5"
          >
            <ArrowLeft className="h-4 w-4 text-white/70" />
          </button>
          <div className="flex-1 text-center">
            <p className="font-syne text-[17px] font-bold text-white">Add Medication</p>
          </div>
          <div className="h-9 w-9" />
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
                  className="w-full rounded-xl border border-white/10 bg-white/5 px-4 py-3 text-sm text-white placeholder-white/30 outline-none focus:border-emerald-500/50 focus:ring-1 focus:ring-emerald-500/20"
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
                  className="w-full resize-none rounded-xl border border-white/10 bg-white/5 px-4 py-3 text-sm text-white placeholder-white/30 outline-none focus:border-emerald-500/50 focus:ring-1 focus:ring-emerald-500/20"
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

            <button
              disabled={!name.trim()}
              onClick={() => setStep(2)}
              className="w-full rounded-xl bg-emerald-500 py-3.5 text-sm font-semibold text-black transition hover:bg-emerald-400 disabled:opacity-40"
            >
              Next
            </button>
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
                  className="flex-1 rounded-xl border border-white/10 bg-white/5 px-4 py-2.5 text-sm text-white outline-none focus:border-emerald-500/50"
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
                  className="w-full rounded-xl border border-white/10 bg-white/5 px-4 py-3 text-sm text-white outline-none focus:border-emerald-500/50"
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
                    className="w-full rounded-xl border border-white/10 bg-white/5 px-4 py-3 text-sm text-white outline-none focus:border-emerald-500/50"
                  />
                </div>
              )}
            </div>

            <button
              disabled={times.length === 0}
              onClick={() => setStep(3)}
              className="w-full rounded-xl bg-emerald-500 py-3.5 text-sm font-semibold text-black transition hover:bg-emerald-400 disabled:opacity-40"
            >
              Next
            </button>
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
                <p className="font-syne text-[18px] font-bold text-white">{name}</p>
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
              <p className="text-[12px] text-white/40">
                From {startDate}
                {hasEnd && endDate ? ` → ${endDate}` : " · Ongoing"}
              </p>
            </div>

            {error && (
              <p className="text-center text-[13px] text-red-400">{error}</p>
            )}

            <button
              disabled={submitting}
              onClick={handleSubmit}
              style={{ minHeight: 52 }}
              className="w-full rounded-xl bg-emerald-500 py-3.5 text-sm font-semibold text-black transition hover:bg-emerald-400 disabled:opacity-60"
            >
              {submitting ? "Setting reminder…" : "Set Reminder"}
            </button>

            <button
              onClick={() => setStep(2)}
              className="block w-full text-center text-[13px] text-white/40 hover:text-white/60"
            >
              ← Edit Schedule
            </button>
          </div>
        )}
      </div>
    </AppShell>
  );
}
