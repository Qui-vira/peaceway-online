"use client";

import { useEffect, useRef, useState } from "react";
import Image from "next/image";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/dist/ScrollTrigger";
import { media } from "@/lib/media";

type Step = { title: string; body: string; image?: string };

const DEFAULT_STEPS: Step[] = [
  {
    title: "Order in seconds",
    body: "Search the catalogue or message us on Telegram. Add what you need and check out - no queues, no guesswork.",
  },
  {
    title: "A pharmacist reviews it",
    body: "Every prescription order is checked by a licensed pharmacist before it's fulfilled, so you always get the right medicine.",
  },
  {
    title: "Delivered across Lagos",
    body: "We package and dispatch to your door, then check in after delivery to make sure everything's okay.",
  },
];

/**
 * Sticky-scroll walkthrough (product-page style). The visual on the right stays
 * pinned (position: sticky) while the copy blocks on the left scroll past;
 * GSAP ScrollTrigger marks each block active as it reaches viewport centre, and
 * the active block highlights while the others dim (and the visual swaps to it).
 * On mobile / reduced-motion it collapses to a single static column.
 */
export function StickyWalkthrough({
  eyebrow = "How it works",
  heading = "From message to medicine.",
  steps = DEFAULT_STEPS,
  image = media.pharmacyPhoto,
}: {
  eyebrow?: string;
  heading?: string;
  steps?: Step[];
  image?: string;
}) {
  const listRef = useRef<HTMLDivElement>(null);
  const [active, setActive] = useState(0);

  useEffect(() => {
    const list = listRef.current;
    if (!list) return;
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const desktop = window.matchMedia("(min-width: 801px)").matches;
    if (reduce || !desktop) return; // mobile: static single column, all visible

    gsap.registerPlugin(ScrollTrigger);
    const ctx = gsap.context(() => {
      gsap.utils.toArray<HTMLElement>(".swt-step").forEach((block, i) => {
        ScrollTrigger.create({
          trigger: block,
          start: "top center",
          end: "bottom center",
          onToggle: (self) => {
            if (self.isActive) setActive(i);
          },
        });
      });
    }, list);
    return () => ctx.revert();
  }, [steps.length]);

  const activeImage = steps[active]?.image ?? image;

  return (
    <section className="bg-[#0b0c09] px-6 py-20 md:px-8 md:py-28">
      <div className="mx-auto max-w-6xl">
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-emerald-400">{eyebrow}</p>
        <h2 className="mt-3 max-w-xl font-syne text-[30px] font-bold leading-tight text-white md:text-[42px]">
          {heading}
        </h2>

        <div className="mt-10 grid gap-10 md:mt-16 md:grid-cols-2 md:gap-16">
          {/* Copy blocks (left) */}
          <div ref={listRef} className="flex flex-col gap-8 md:gap-[38vh] md:py-[18vh]">
            {steps.map((s, i) => {
              const on = i === active;
              return (
                <div
                  key={i}
                  className={`swt-step border-l-2 pl-5 transition-all duration-300 md:pl-6 ${
                    on
                      ? "border-emerald-500 opacity-100"
                      : "border-white/10 opacity-100 md:opacity-40"
                  }`}
                >
                  <span
                    className={`inline-flex h-8 w-8 items-center justify-center rounded-full text-[13px] font-bold transition-colors ${
                      on ? "bg-emerald-500 text-black" : "bg-white/8 text-white/50"
                    }`}
                  >
                    {i + 1}
                  </span>
                  <h3 className="mt-4 font-syne text-[22px] font-bold text-white md:text-[26px]">
                    {s.title}
                  </h3>
                  <p className="mt-2 max-w-md text-[15px] leading-relaxed text-white/55">{s.body}</p>
                </div>
              );
            })}
          </div>

          {/* Pinned visual (right, desktop only) */}
          <div className="hidden md:block">
            <div className="sticky top-24 aspect-[4/5] overflow-hidden rounded-3xl border border-white/10 bg-white/[0.03] shadow-[0_40px_80px_-30px_rgba(0,0,0,0.8)]">
              <Image
                key={activeImage}
                src={activeImage}
                alt=""
                aria-hidden
                fill
                sizes="40vw"
                className="animate-[fadeIn_0.5s_ease] object-cover"
              />
              <div
                className="pointer-events-none absolute inset-0"
                style={{
                  background:
                    "linear-gradient(180deg, transparent 40%, rgba(7,8,6,0.55) 100%)",
                }}
              />
              <span className="absolute bottom-5 left-5 rounded-full bg-black/60 px-3 py-1 text-[12px] font-semibold text-white backdrop-blur-sm">
                Step {active + 1} of {steps.length}
              </span>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
