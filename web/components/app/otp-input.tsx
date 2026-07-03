"use client";

import { useRef } from "react";

interface OtpInputProps {
  value: string;
  onChange: (value: string) => void;
  disabled?: boolean;
}

export function OtpInput({ value, onChange, disabled }: OtpInputProps) {
  const refs = useRef<(HTMLInputElement | null)[]>([]);
  const digits = Array.from({ length: 6 }, (_, i) => value[i] ?? "");

  function handleChange(index: number, char: string) {
    const digit = char.replace(/\D/g, "").slice(-1);
    const next = digits.map((d, i) => (i === index ? digit : d)).join("");
    onChange(next.padEnd(6, " ").slice(0, 6));
    if (digit && index < 5) refs.current[index + 1]?.focus();
  }

  function handleKeyDown(index: number, e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Backspace" && !digits[index] && index > 0) {
      refs.current[index - 1]?.focus();
    }
  }

  function handlePaste(e: React.ClipboardEvent) {
    e.preventDefault();
    const pasted = e.clipboardData.getData("text").replace(/\D/g, "").slice(0, 6);
    onChange(pasted.padEnd(6, " ").slice(0, 6));
    const nextFocus = Math.min(pasted.length, 5);
    refs.current[nextFocus]?.focus();
  }

  return (
    <div className="flex gap-2 justify-center">
      {Array.from({ length: 6 }).map((_, i) => (
        <input
          key={i}
          ref={(el) => {
            refs.current[i] = el;
          }}
          type="text"
          inputMode="numeric"
          maxLength={1}
          value={digits[i] === " " ? "" : digits[i]}
          disabled={disabled}
          onChange={(e) => handleChange(i, e.target.value)}
          onKeyDown={(e) => handleKeyDown(i, e)}
          onPaste={handlePaste}
          onFocus={(e) => e.target.select()}
          className={[
            "h-14 w-12 rounded-xl border text-center text-xl font-bold text-white transition",
            "outline-none",
            digits[i] && digits[i] !== " "
              ? "border-emerald-500/60"
              : "border-white/15 focus:border-emerald-500/50",
            "disabled:opacity-40 disabled:cursor-not-allowed",
          ].join(" ")}
          style={{ background: "rgba(255,255,255,0.06)", WebkitTextFillColor: "white", WebkitBoxShadow: "0 0 0px 1000px #141614 inset", caretColor: "white" }}
        />
      ))}
    </div>
  );
}
