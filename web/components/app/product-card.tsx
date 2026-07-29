"use client";

import { useEffect, useRef } from "react";
import Link from "next/link";
import gsap from "gsap";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { Check, Plus } from "lucide-react";
import { DrugIcon } from "@/components/app/drug-icons";
import { EASE } from "@/components/app/motion";
import { mediaSrc } from "@/lib/api";
import type { Product } from "@/lib/api/catalog";

const FOCUS =
  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-400/70 focus-visible:ring-offset-2 focus-visible:ring-offset-[#0b0c09]";

/**
 * A product with no price set must not render "₦0".
 *
 * `selling_price` arrives as a string, so "0.00" is truthy and the old `!price`
 * guard sailed straight past it — an unpriced item showed as free. Products are
 * listed before pricing (the catalogue is imported, then priced by staff), so this
 * is the normal state for a lot of the shop, not an edge case.
 */
function isPriced(price: string | null | undefined): boolean {
  if (price === null || price === undefined || price === "") return false;
  const n = Number(price);
  return Number.isFinite(n) && n > 0;
}

function fmt(price: string | null) {
  return isPriced(price) ? `₦${Number(price).toLocaleString("en-NG")}` : "Price on request";
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
  const reduce = useReducedMotion();

  useEffect(() => {
    const card = cardRef.current;
    const icon = iconRef.current;
    const cta = ctaRef.current;
    if (!card || !icon || !cta) return;

    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    // `pointer: fine` as well as `hover: hover`: a touchscreen laptop reports
    // hover-capable but its finger is a coarse pointer, and a pointer-driven
    // lift has no meaning without a real pointer to drive it.
    const canHover = window.matchMedia("(hover: hover) and (pointer: fine)").matches;
    // Touch gets its press from `.pw-tile-press`-style CSS on the element below,
    // not from GSAP: a pointer-driven lift has no meaning without a pointer.
    // The card's own touch feedback is `active:scale-[0.98]` in the markup, which
    // is why this early return is correct rather than a gap.
    if (reduce || !canHover) return;

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
          {/* iconRef stays on the wrapper either way so the GSAP hover scale applies
              to a real photo exactly as it did to the fallback icon. */}
          <div ref={iconRef} className="h-full w-full will-change-transform">
            {p.image_url ? (
              /* next/image is the wrong tool for these. file_storage already
                 normalizes every upload to 800px on the long edge, WebP, EXIF
                 stripped, so the optimizer would re-encode an asset that is
                 already optimal. Intrinsic dimensions never reach the client
                 either: MediaAsset stores width/height but the API returns only
                 image_url, and the long-edge cap means the aspect ratio varies
                 per photo. mediaSrc() also resolves to the API host, so this
                 would need images.remotePatterns and would bill per source
                 image on Vercel for no gain. */
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={mediaSrc(p.image_url)}
                alt={p.name}
                loading="lazy"
                className="h-full w-full object-cover"
              />
            ) : (
              <div className="flex h-full w-full items-center justify-center">
                <DrugIcon form={p.dosage_form ?? undefined} size={40} />
              </div>
            )}
          </div>
        </div>
        {/* Hover CTA (fades in via GSAP on pointer devices; hidden otherwise) */}
        <span
          ref={ctaRef}
          className="pointer-events-none absolute right-2 top-2 rounded-full bg-black/60 px-2.5 py-1 text-[11px] font-semibold text-white backdrop-blur-sm"
        >
          View
        </span>
      </Link>
      <div className="flex flex-1 flex-col gap-1.5 p-3">
        <Link href={`/shop/${p.id}`} className={`rounded ${FOCUS}`}>
          <p className="line-clamp-2 text-[13px] font-semibold leading-snug text-white">{p.name}</p>
          {p.strength && <p className="text-[11px] text-[#b1bdb0]">{p.strength}</p>}
        </Link>
        <p className="text-[13px] font-bold text-emerald-400">{fmt(p.selling_price)}</p>
        {/* An unpriced product must never offer Add: adding it would put a ₦0 line
            into the customer's cart and through checkout. */}
        {!p.is_in_stock || !isPriced(p.selling_price) ? (
          <span className="mt-auto text-[11px] text-[#b1bdb0]">
            {!p.is_in_stock ? "Out of stock" : "Ask us for the price"}
          </span>
        ) : (
          /* Add -> Added is the one state change on this screen the customer
             causes themselves, and it was a hard cut: the button was simply a
             different element on the next render. The crossfade is what makes
             the tap feel acknowledged rather than merely obeyed. Both states are
             the same height, so nothing below reflows and the swap costs no CLS.
             `mode="wait"` would leave a 140ms hole in the grid; the two states
             overlap in a fixed-height box instead. */
          <div className="relative mt-auto min-h-[40px]">
            <AnimatePresence initial={false}>
              {added ? (
                <motion.div
                  key="added"
                  initial={reduce ? { opacity: 0 } : { opacity: 0, scale: 0.96 }}
                  animate={{ opacity: 1, scale: 1 }}
                  exit={{ opacity: 0 }}
                  transition={{ duration: 0.18, ease: EASE }}
                  className="absolute inset-0 inline-flex w-full items-center justify-center gap-1.5 rounded-xl bg-emerald-500/20 text-[12px] font-bold text-emerald-400"
                >
                  <Check className="h-3.5 w-3.5" aria-hidden /> Added
                </motion.div>
              ) : (
                <motion.button
                  key="add"
                  onClick={() => onAdd(p)}
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  transition={{ duration: 0.14, ease: EASE }}
                  whileTap={reduce ? undefined : { scale: 0.96 }}
                  className={`pw-btn-sm absolute inset-0 w-full ${FOCUS}`}
                >
                  <Plus className="h-3.5 w-3.5" aria-hidden /> Add
                </motion.button>
              )}
            </AnimatePresence>
          </div>
        )}
      </div>
    </div>
  );
}
