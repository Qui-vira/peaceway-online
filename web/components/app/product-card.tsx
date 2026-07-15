"use client";

import { useEffect, useRef } from "react";
import Link from "next/link";
import gsap from "gsap";
import { Check, Plus } from "lucide-react";
import { DrugIcon } from "@/components/app/drug-icons";
import type { Product } from "@/lib/api/catalog";

const FOCUS =
  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-400/70 focus-visible:ring-offset-2 focus-visible:ring-offset-[#0b0c09]";

function fmt(price: string | null) {
  if (!price) return "-";
  return `₦${Number(price).toLocaleString("en-NG")}`;
}

/**
 * Product card with a springy GSAP hover: the card lifts, its shadow grows, the
 * icon scales up inside its frame, and a "View" CTA fades in. quickTo keeps it
 * cheap across a grid of cards. prefers-reduced-motion disables the motion;
 * hover-less (touch) devices get a press/tap state instead of hover.
 */
export function ProductCard({
  product: p,
  added,
  onAdd,
}: {
  product: Product;
  added: boolean;
  onAdd: (p: Product) => void;
}) {
  const cardRef = useRef<HTMLDivElement>(null);
  const iconRef = useRef<HTMLDivElement>(null);
  const ctaRef = useRef<HTMLSpanElement>(null);

  useEffect(() => {
    const card = cardRef.current;
    const icon = iconRef.current;
    const cta = ctaRef.current;
    if (!card || !icon || !cta) return;

    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const canHover = window.matchMedia("(hover: hover)").matches;
    if (reduce || !canHover) return; // touch/reduced-motion use the CSS :active/base state

    const ctx = gsap.context(() => {
      // quickTo avoids re-creating tweens on every pointer event across the grid.
      // Hover feedback is held under ~200ms; at 350-400ms the card visibly
      // trailed the cursor, which reads as lag rather than polish.
      const y = gsap.quickTo(card, "y", { duration: 0.2, ease: "power3.out" });
      const shadow = (v: string) =>
        gsap.to(card, { boxShadow: v, duration: 0.2, ease: "power2.out" });
      const iconScale = gsap.quickTo(icon, "scale", { duration: 0.16, ease: "power2.out" });
      gsap.set(cta, { autoAlpha: 0, y: 6 });

      const enter = () => {
        y(-6);
        iconScale(1.09);
        shadow("0 22px 46px -14px rgba(0,0,0,0.6), 0 4px 0 0 rgba(255,255,255,0.06)");
        gsap.to(cta, { autoAlpha: 1, y: 0, duration: 0.28, ease: "back.out(1.7)" });
      };
      const leave = () => {
        y(0);
        iconScale(1);
        shadow("0 4px 0 0 rgba(255,255,255,0.05), 0 10px 22px -12px rgba(0,0,0,0.6)");
        gsap.to(cta, { autoAlpha: 0, y: 6, duration: 0.2, ease: "power1.in" });
      };

      card.addEventListener("mouseenter", enter);
      card.addEventListener("mouseleave", leave);
      return () => {
        card.removeEventListener("mouseenter", enter);
        card.removeEventListener("mouseleave", leave);
      };
    }, card);

    return () => ctx.revert();
  }, []);

  return (
    <div
      ref={cardRef}
      className="pw-tile group relative flex flex-col overflow-hidden active:scale-[0.98] motion-reduce:active:scale-100"
    >
      <Link href={`/shop/${p.id}`} aria-label={p.name} className={`relative block ${FOCUS}`}>
        <div className="flex h-24 items-center justify-center overflow-hidden border-b border-white/6 bg-emerald-500/[0.06] sm:h-28">
          <div ref={iconRef} className="will-change-transform">
            <DrugIcon form={p.dosage_form ?? undefined} size={40} />
          </div>
        </div>
        {/* Hover CTA (fades in via GSAP on pointer devices; hidden otherwise) */}
        <span
          ref={ctaRef}
          className="pointer-events-none absolute right-2 top-2 rounded-full bg-black/60 px-2.5 py-1 text-[10px] font-semibold text-white backdrop-blur-sm"
        >
          View
        </span>
      </Link>
      <div className="flex flex-1 flex-col gap-1.5 p-3">
        <Link href={`/shop/${p.id}`} className={`rounded ${FOCUS}`}>
          <p className="line-clamp-2 text-[13px] font-semibold leading-snug text-white">{p.name}</p>
          {p.strength && <p className="text-[11px] text-white/40">{p.strength}</p>}
        </Link>
        <p className="text-[13px] font-bold text-emerald-400">{fmt(p.selling_price)}</p>
        {!p.is_in_stock ? (
          <span className="mt-auto text-[11px] text-white/30">Out of stock</span>
        ) : added ? (
          <div className="mt-auto inline-flex min-h-[40px] w-full items-center justify-center gap-1.5 rounded-xl bg-emerald-500/20 text-[12px] font-bold text-emerald-400">
            <Check className="h-3.5 w-3.5" /> Added
          </div>
        ) : (
          <button
            onClick={() => onAdd(p)}
            className={`pw-btn-sm mt-auto w-full ${FOCUS}`}
          >
            <Plus className="h-3.5 w-3.5" /> Add
          </button>
        )}
      </div>
    </div>
  );
}
