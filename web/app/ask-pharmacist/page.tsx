"use client";

import { useEffect, useState } from "react";
import { AlertTriangle, CheckCircle2, Clock, Loader2, MessageCircle, SendHorizontal } from "lucide-react";
import {
  askQuestion,
  listQuestions,
  type PharmacistQuestion,
} from "@/lib/api/ask";
import type { ApiError } from "@/lib/api";
import { AppShell } from "@/components/app/app-shell";
import { GuestWall, SectionLabel, Spinner } from "@/components/app/ui";

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("en-NG", {
    day: "numeric",
    month: "short",
  });
}

export default function AskPharmacistPage() {
  const [questions, setQuestions] = useState<PharmacistQuestion[] | null>(null);
  const [guest, setGuest] = useState(false);
  const [question, setQuestion] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    listQuestions()
      .then(setQuestions)
      .catch(() => setGuest(true));
  }, []);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const q = question.trim();
    if (!q) {
      setError("Please type your question first.");
      return;
    }
    setError("");
    setSending(true);
    try {
      const created = await askQuestion(q);
      setQuestions((prev) => [created, ...(prev ?? [])]);
      setQuestion("");
    } catch (err) {
      const apiErr = err as ApiError;
      setError(apiErr?.detail ?? "Could not send. Please try again.");
    } finally {
      setSending(false);
    }
  }

  return (
    <AppShell>
      <div className="space-y-6 px-5 pt-10 pb-6">

        {/* Header */}
        <div className="flex items-start gap-3">
          <span className="mt-0.5 flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-emerald-500/12 border border-emerald-500/20">
            <MessageCircle className="h-5 w-5 text-emerald-400" />
          </span>
          <div>
            <h1 className="font-syne text-xl font-bold text-white">Ask a Pharmacist</h1>
            <p className="text-sm text-white/50">A qualified pharmacist will reply.</p>
          </div>
        </div>

        {guest && <GuestWall message="Create a profile so our pharmacist can reply to you." />}
        {!guest && questions === null && <Spinner />}

        {!guest && questions !== null && (
          <>
            {/* Compose card */}
            <form onSubmit={handleSubmit}>
              <div
                className={[
                  "relative rounded-2xl border bg-white/4 px-4 pt-4 pb-14 transition-colors",
                  error
                    ? "border-red-500/40"
                    : "border-white/10 focus-within:border-emerald-500/40",
                ].join(" ")}
              >
                <textarea
                  rows={3}
                  maxLength={2000}
                  placeholder="e.g. Can I take ibuprofen with my blood pressure medicine?"
                  value={question}
                  onChange={(e) => setQuestion(e.target.value)}
                  className="w-full resize-none bg-transparent text-sm text-white placeholder-white/25 outline-none"
                />
                <button
                  type="submit"
                  disabled={sending || !question.trim()}
                  className="absolute bottom-3 right-3 flex h-9 w-9 items-center justify-center rounded-full bg-emerald-500 text-black transition hover:bg-emerald-400 disabled:cursor-not-allowed disabled:opacity-40"
                >
                  {sending ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <SendHorizontal className="h-4 w-4" />
                  )}
                </button>
              </div>
              {error && (
                <p className="mt-2 rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-2.5 text-sm text-red-400">
                  {error}
                </p>
              )}
            </form>

            {/* Disclaimer */}
            <div className="flex items-center gap-2.5 rounded-xl border border-amber-500/25 bg-amber-500/8 px-4 py-3">
              <AlertTriangle className="h-4 w-4 shrink-0 text-amber-400" />
              <p className="text-[12px] leading-relaxed text-amber-300/80">
                General guidance only. Not a medical diagnosis. In an emergency, seek care immediately.
              </p>
            </div>

            {/* Questions list */}
            {questions.length > 0 && (
              <div className="space-y-3">
                <SectionLabel>Your Questions</SectionLabel>
                {questions.map((q) => (
                  <div
                    key={q.id}
                    className={[
                      "rounded-2xl border bg-white/4 px-5 py-4 space-y-3",
                      q.is_answered
                        ? "border-l-[3px] border-l-emerald-500 border-white/6"
                        : "border-l-[3px] border-l-amber-500/60 border-white/6",
                    ].join(" ")}
                  >
                    <div className="flex items-start justify-between gap-3">
                      <p className="text-sm leading-relaxed text-white/85">{q.question}</p>
                      <span className="shrink-0 text-[11px] text-white/30 mt-0.5">
                        {formatDate(q.created_at)}
                      </span>
                    </div>

                    {q.is_answered && q.answer ? (
                      <div className="rounded-xl border border-emerald-500/15 bg-emerald-500/8 px-4 py-3">
                        <p className="mb-1.5 flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-widest text-emerald-400">
                          <CheckCircle2 className="h-3 w-3" />
                          Pharmacist
                        </p>
                        <p className="text-sm leading-relaxed text-white/85">{q.answer}</p>
                      </div>
                    ) : (
                      <p className="flex items-center gap-1.5 text-xs text-amber-400/70">
                        <Clock className="h-3.5 w-3.5" />
                        Waiting for pharmacist reply
                      </p>
                    )}
                  </div>
                ))}
              </div>
            )}

            {questions.length === 0 && (
              <div className="flex flex-col items-center gap-4 py-8 text-center">
                <span className="inline-flex h-14 w-14 items-center justify-center rounded-full border border-white/10 bg-white/5">
                  <MessageCircle className="h-6 w-6 text-white/30" />
                </span>
                <div className="space-y-1">
                  <p className="text-base font-semibold text-white">No questions yet</p>
                  <p className="max-w-xs text-sm leading-relaxed text-white/40">
                    Ask anything about your medicines above.
                  </p>
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </AppShell>
  );
}
