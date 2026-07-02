"use client";

import { useEffect, useState } from "react";
import { CheckCircle2, Clock, Loader2, MessageCircle, SendHorizontal } from "lucide-react";
import {
  askQuestion,
  listQuestions,
  type PharmacistQuestion,
} from "@/lib/api/ask";
import type { ApiError } from "@/lib/api";
import { AppShell, AppHeader } from "@/components/app/app-shell";
import { GuestWall, Spinner } from "@/components/app/ui";

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
      <AppHeader
        title="Ask a Pharmacist"
        subtitle="Dosage, interactions, side effects — a qualified pharmacist will answer."
      />

      {guest && <GuestWall message="Create a profile so our pharmacist can reply to you." />}
      {!guest && questions === null && <Spinner />}

      {!guest && questions !== null && (
        <div className="space-y-6 px-5">
          <form onSubmit={handleSubmit} className="space-y-3">
            <div className="rounded-xl border border-white/10 bg-white/4 px-4 py-3.5 backdrop-blur-sm transition-colors focus-within:border-emerald-500/60">
              <textarea
                rows={3}
                maxLength={2000}
                placeholder="e.g. Can I take ibuprofen with my blood pressure medicine?"
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                className="w-full resize-none bg-transparent text-sm text-white placeholder-white/25 outline-none"
              />
            </div>

            {error && (
              <p className="rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400">
                {error}
              </p>
            )}

            <button
              type="submit"
              disabled={sending}
              className="inline-flex w-full items-center justify-center gap-2 rounded-xl bg-emerald-500 px-6 py-3.5 text-sm font-semibold text-black transition hover:bg-emerald-400 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {sending ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Sending…
                </>
              ) : (
                <>
                  Send Question
                  <SendHorizontal className="h-4 w-4" />
                </>
              )}
            </button>

            <p className="text-center text-xs leading-relaxed text-white/30">
              This is general pharmacist guidance, not a medical diagnosis. In an
              emergency, seek care immediately.
            </p>
          </form>

          {questions.length > 0 && (
            <div className="space-y-3 pb-4">
              <p className="text-xs font-semibold uppercase tracking-widest text-white/35">
                Your questions
              </p>
              {questions.map((q) => (
                <div
                  key={q.id}
                  className="space-y-3 rounded-2xl border border-white/10 bg-white/4 px-5 py-4"
                >
                  <div className="flex items-start justify-between gap-3">
                    <p className="text-sm leading-relaxed text-white/85">{q.question}</p>
                    <span className="shrink-0 text-[10px] text-white/30">
                      {formatDate(q.created_at)}
                    </span>
                  </div>

                  {q.is_answered && q.answer ? (
                    <div className="rounded-xl border border-emerald-500/20 bg-emerald-500/8 px-4 py-3">
                      <p className="mb-1 flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-widest text-emerald-400">
                        <CheckCircle2 className="h-3 w-3" />
                        Pharmacist reply
                      </p>
                      <p className="text-sm leading-relaxed text-white/85">{q.answer}</p>
                    </div>
                  ) : (
                    <p className="flex items-center gap-1.5 text-xs text-white/40">
                      <Clock className="h-3.5 w-3.5" />
                      Waiting for pharmacist reply
                    </p>
                  )}
                </div>
              ))}
            </div>
          )}

          {questions.length === 0 && (
            <div className="flex flex-col items-center gap-3 py-6 text-center">
              <MessageCircle className="h-6 w-6 text-white/25" />
              <p className="max-w-xs text-sm text-white/40">
                No questions yet. Ask anything about your medicines above.
              </p>
            </div>
          )}
        </div>
      )}
    </AppShell>
  );
}
