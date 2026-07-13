"use client";

import { useState, useRef } from "react";
import Link from "next/link";
import { ArrowLeft, Upload, CheckCircle2, AlertTriangle } from "lucide-react";
import { submitPrescription } from "@/lib/api/orders";
import { AppShell } from "@/components/app/app-shell";

type State = "idle" | "submitting" | "done" | "error";

function fileToBase64(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve((reader.result as string).split(",")[1]);
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}

export default function PrescriptionPage() {
  const [description, setDescription] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [state, setState] = useState<State>("idle");
  const [error, setError] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  async function handleSubmit() {
    if (!description.trim() && !file) return;
    setState("submitting");
    setError("");
    try {
      let file_b64: string | undefined;
      let file_type: string | undefined;
      if (file) {
        file_b64 = await fileToBase64(file);
        file_type = file.type.startsWith("application/pdf") ? "document" : "image";
      }
      await submitPrescription({
        description: description.trim() || file?.name || "Web upload",
        file_b64,
        file_type,
      });
      setState("done");
    } catch {
      setError("Something went wrong. Please try again.");
      setState("error");
    }
  }

  if (state === "done") {
    return (
      <AppShell>
        <div className="flex flex-col items-center gap-6 px-5 py-16 text-center">
          <div className="flex h-16 w-16 items-center justify-center rounded-full border-2 border-emerald-500">
            <CheckCircle2 className="h-8 w-8 text-emerald-400" />
          </div>
          <div>
            <h2 className="font-syne text-[22px] font-bold text-white">Prescription received</h2>
            <p className="mt-2 text-[13px] leading-relaxed text-white/50">
              A pharmacist will review your prescription and contact you via Telegram with the price.
            </p>
          </div>
          <div className="w-full rounded-2xl border border-white/8 bg-white/4 px-4 py-4 text-left space-y-3">
            <p className="text-[10px] font-semibold uppercase tracking-[0.14em] text-white/40">What happens next</p>
            {[
              "Pharmacist reviews your prescription",
              "You'll receive a Telegram message with price and availability",
              "Confirm and pay to complete your order",
            ].map((step, i) => (
              <div key={i} className="flex items-start gap-2.5">
                <span className={`mt-1 h-2 w-2 shrink-0 rounded-full ${i === 0 ? "bg-emerald-500" : "bg-white/20"}`} />
                <p className={`text-[13px] ${i === 0 ? "text-white/80" : "text-white/40"}`}>{step}</p>
              </div>
            ))}
          </div>
          <Link
            href="/requests"
            className="inline-flex items-center gap-2 rounded-xl border border-white/10 px-5 py-3 text-sm text-white/50 transition hover:border-white/20 hover:text-white/70"
          >
            View My Requests
          </Link>
        </div>
      </AppShell>
    );
  }

  return (
    <AppShell>
      <div className="space-y-5 px-5 pt-10 pb-8">
        {/* Header */}
        <div className="flex items-center gap-3">
          <Link
            href="/app"
            className="flex h-9 w-9 items-center justify-center rounded-full border border-white/10 bg-white/5"
          >
            <ArrowLeft className="h-4 w-4 text-white/70" />
          </Link>
          <div>
            <h1 className="font-syne text-[20px] font-bold text-white">Upload Prescription</h1>
            <p className="text-[12px] text-white/40">Send us your script</p>
          </div>
        </div>

        {/* Upload zone */}
        <button
          onClick={() => inputRef.current?.click()}
          className={`flex w-full flex-col items-center gap-3 rounded-2xl border-2 border-dashed px-5 py-8 transition ${
            file
              ? "border-emerald-500/40 bg-emerald-500/6"
              : "border-white/15 bg-white/3 hover:border-white/25"
          }`}
        >
          <Upload className={`h-7 w-7 ${file ? "text-emerald-400" : "text-white/30"}`} />
          {file ? (
            <>
              <p className="text-[13px] font-semibold text-emerald-400">{file.name}</p>
              <p className="text-[11px] text-white/40">Tap to change</p>
            </>
          ) : (
            <>
              <p className="text-[13px] font-semibold text-white">Tap to upload</p>
              <p className="text-[11px] text-white/35">JPG, PNG or PDF · max 10 MB</p>
            </>
          )}
        </button>
        <input
          ref={inputRef}
          type="file"
          accept="image/*,.pdf"
          className="hidden"
          onChange={(e) => {
            const f = e.target.files?.[0];
            if (f && f.size <= 10 * 1024 * 1024) setFile(f);
          }}
        />

        {/* Description */}
        <div className="rounded-2xl border border-white/8 bg-white/4 px-4 py-4 space-y-2">
          <p className="text-[10px] font-semibold uppercase tracking-[0.14em] text-white/40">
            Or describe your prescription
          </p>
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="e.g. Amoxicillin 500mg, 10 tablets - prescribed by Dr. Adeyemi"
            rows={3}
            className="w-full resize-none rounded-xl border border-white/10 bg-white/5 px-4 py-3 text-sm text-white placeholder-white/30 outline-none focus:border-emerald-500/50"
          />
        </div>

        {/* Disclaimer */}
        <div className="flex items-start gap-2.5 rounded-xl border border-amber-500/25 bg-amber-500/8 px-3.5 py-2.5">
          <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0 text-amber-400" />
          <p className="text-[11px] leading-relaxed text-amber-300/80">
            Prescriptions are reviewed by a licensed pharmacist before any medicine is dispensed.
          </p>
        </div>

        {state === "error" && (
          <p className="text-[13px] text-red-400">{error}</p>
        )}

        <button
          disabled={(!description.trim() && !file) || state === "submitting"}
          onClick={handleSubmit}
          className="w-full rounded-xl bg-emerald-500 py-3.5 text-sm font-semibold text-black transition hover:bg-emerald-400 disabled:opacity-40"
        >
          {state === "submitting" ? "Sending…" : "Send Prescription →"}
        </button>
      </div>
    </AppShell>
  );
}
