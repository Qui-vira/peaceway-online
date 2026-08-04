"use client";

import { useEffect, useRef } from "react";
import Image from "next/image";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/dist/ScrollTrigger";
import { media } from "@/lib/media";

/**
 * Parallax depth section: a background layer, a midground product image, and
 * foreground headline text move at slightly different speeds as the section
 * crosses the viewport (background slowest, product image fastest, copy barely
 * moves - per the parallax guidance: never parallax body copy hard). Desktop
 * only; on mobile / reduced-motion it renders static, single-column.
 */
export function ParallaxShowcase({
  eyebrow = "Peaceway Online",
  title = "A licensed pharmacy, online.",
  body = "NAFDAC-registered medicine from traceable suppliers. Every order is reviewed by a registered pharmacist before it is dispensed.",
  imageSrc = media.pharmacyPhoto,
}: {
  eyebrow?: string;
  title?: string;
  body?: string;
  imageSrc?: string;
}) {
  const rootRef = useRef<HTMLElement>(null);

  useEffect(() => {
    const root = rootRef.current;
    if (!root) return;
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const desktop = window.matchMedia("(min-width: 801px)").matches;
    if (reduce || !desktop) return; // mobile / reduced-motion: static

    gsap.registerPlugin(ScrollTrigger);
    const ctx = gsap.context(() => {
      const scroll = { trigger: root, start: "top bottom", end: "bottom top", scrub: 0.6 };
      // background slowest, product image fastest, copy minimal
      gsap.fromTo(".pxs-bg", { yPercent: -6 }, { yPercent: 6, ease: "none", scrollTrigger: scroll });
      gsap.fromTo(".pxs-mid", { yPercent: 12 }, { yPercent: -12, ease: "none", scrollTrigger: scroll });
      gsap.fromTo(".pxs-fore", { yPercent: 3 }, { yPercent: -3, ease: "none", scrollTrigger: scroll });
    }, root);
    return () => ctx.revert();
  }, []);

  return (
    <section
      ref={rootRef}
      className="relative isolate overflow-hidden bg-[#0b0c09] px-6 py-24 md:px-8 md:py-36"
    >
      {/* Background layer (decorative) */}
      <div
        className="pxs-bg pointer-events-none absolute inset-x-0 -inset-y-[10%] -z-10 will-change-transform"
        aria-hidden
        style={{
          background:
            "radial-gradient(60% 50% at 20% 20%, rgba(15,103,60,0.28), transparent 70%), radial-gradient(50% 40% at 85% 80%, rgba(26,163,90,0.18), transparent 70%)",
        }}
      />
      <div
        className="pointer-events-none absolute inset-0 -z-10 opacity-[0.06]"
        aria-hidden
        style={{
          backgroundImage:
            "radial-gradient(rgba(255,255,255,0.7) 1px, transparent 1px)",
          backgroundSize: "22px 22px",
        }}
      />

      <div className="mx-auto grid max-w-6xl items-center gap-10 md:grid-cols-2 md:gap-16">
        {/* Foreground copy */}
        <div className="pxs-fore will-change-transform">
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-emerald-400">
            {eyebrow}
          </p>
          <h2 className="mt-3 font-syne text-[32px] font-bold leading-tight text-white md:text-[46px]">
            {title}
          </h2>
          <p className="mt-4 max-w-md text-base leading-relaxed text-white/55">{body}</p>
        </div>

        {/* Midground product image */}
        <div className="pxs-mid relative aspect-[4/3] w-full will-change-transform">
          <div className="absolute inset-0 rounded-3xl border border-white/10 bg-white/[0.03] shadow-[0_40px_80px_-30px_rgba(0,0,0,0.8)]">
            <Image
              src={imageSrc}
              alt="Peaceway Pharmacy"
              fill
              sizes="(max-width: 800px) 100vw, 40vw"
              className="rounded-3xl object-cover"
            />
          </div>
        </div>
      </div>
    </section>
  );
}
