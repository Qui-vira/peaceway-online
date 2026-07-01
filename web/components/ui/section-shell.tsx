"use client";

import type { ReactNode } from "react";
import { useEffect, useRef } from "react";
import { cn } from "@/lib/utils";
import { VideoBackground } from "@/components/ui/video-background";
import { usePrefersReducedMotion } from "@/lib/motion";

type SectionShellProps = {
  id: string;
  eyebrow: string;
  title: string;
  description: string;
  videoSrc: string;
  poster?: string;
  children: ReactNode;
  align?: "left" | "center";
  className?: string;
  compact?: boolean;
};

export function SectionShell({
  id,
  eyebrow,
  title,
  description,
  videoSrc,
  poster,
  children,
  align = "left",
  className,
  compact = false
}: SectionShellProps): JSX.Element {
  const centered = align === "center";
  const shouldReduceMotion = usePrefersReducedMotion();
  const sectionRef = useRef<HTMLElement | null>(null);

  useEffect(() => {
    const node = sectionRef.current;
    if (!node) {
      return;
    }

    if (shouldReduceMotion) {
      return;
    }

    const observer = new IntersectionObserver(
      () => undefined,
      { threshold: 0.15, rootMargin: "0px" }
    );

    observer.observe(node);
    return () => observer.disconnect();
  }, [shouldReduceMotion]);

  const active = !shouldReduceMotion;
  const reveal = true;

  return (
    <section
      ref={sectionRef}
      id={id}
      className={cn(
        "relative isolate overflow-hidden",
        compact ? "py-16 md:py-20" : "py-20 md:py-24",
        className
      )}
    >
      <VideoBackground src={videoSrc} poster={poster} active={active} />
      <div className="absolute inset-0 bg-[linear-gradient(to_bottom,rgba(7,8,6,0.72)_0%,rgba(7,8,6,0.34)_34%,rgba(7,8,6,0.82)_100%)]" />
      <div
        className={cn(
          "mx-auto flex max-w-[1240px] items-center px-5 md:px-14 transition-all duration-700 ease-out",
          centered ? "justify-center text-center" : "justify-start",
          reveal ? "translate-y-0 opacity-100" : "translate-y-3 opacity-0"
        )}
      >
        <div className={cn("relative z-10 w-full", centered ? "max-w-4xl" : "max-w-6xl")}>
          <p
            className={cn(
              "mb-2 text-[11px] font-semibold uppercase tracking-[0.18em] text-red-400 transition-all duration-500 ease-out",
              "translate-y-0 opacity-100"
            )}
          >
            {eyebrow}
          </p>
          <h2
            className={cn(
              "section-title mb-3 max-w-4xl text-[clamp(24px,3.2vw,46px)] font-extrabold leading-[1.05] tracking-[-0.022em] text-white transition-all duration-500 ease-out",
              "translate-y-0 opacity-100"
            )}
          >
            {title}
          </h2>
          <p
            className={cn(
              "max-w-[560px] text-[clamp(13px,1.2vw,16px)] leading-[1.7] text-white/72 transition-all duration-500 ease-out",
              centered ? "mx-auto" : "",
              "translate-y-0 opacity-100"
            )}
          >
            {description}
          </p>
          <div
            className={cn(
              "mt-8 transition-all duration-500 ease-out md:mt-10",
              "translate-y-0 opacity-100"
            )}
          >
            {children}
          </div>
        </div>
      </div>
    </section>
  );
}
