"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import type { ReactNode } from "react";
import { cn } from "@/lib/utils";
import { useDesktopPointer, usePrefersReducedMotion } from "@/lib/motion";

type GlassCardProps = {
  title: string;
  text: string;
  variant?: "green" | "red" | "neutral";
  icon?: ReactNode;
  className?: string;
  delay?: number;
};

export function GlassCard({
  title,
  text,
  variant = "neutral",
  icon,
  className,
  delay = 0
}: GlassCardProps): JSX.Element {
  const shouldReduceMotion = usePrefersReducedMotion();
  const canTilt = useDesktopPointer();
  const cardRef = useRef<HTMLElement | null>(null);
  const [visible, setVisible] = useState(true);
  const [tilt, setTilt] = useState({ x: 0, y: 0 });

  const tone =
    variant === "green"
      ? "border-emerald-500/25 bg-emerald-500/10"
      : variant === "red"
        ? "border-red-500/25 bg-red-500/10"
        : "border-white/10 bg-white/6";

  useEffect(() => {
    const node = cardRef.current;
    if (!node) {
      return;
    }

    if (shouldReduceMotion) {
      setVisible(true);
    }
  }, [shouldReduceMotion]);

  const style = useMemo(() => {
    if (!canTilt || shouldReduceMotion) {
      return undefined;
    }

    return {
      transform: `perspective(1100px) rotateX(${tilt.y}deg) rotateY(${tilt.x}deg) scale(${visible ? 1 : 0.98})`,
      transformStyle: "preserve-3d" as const
    };
  }, [canTilt, shouldReduceMotion, tilt.x, tilt.y, visible]);

  return (
    <article
      ref={cardRef}
      className={cn(
        "glass rounded-2xl p-5 md:p-6 transition-all duration-500 ease-out",
        tone,
        className,
        "translate-y-0 opacity-100"
      )}
      data-hoverable="true"
      style={{
        transitionDelay: `${delay}s`,
        boxShadow: "0 22px 55px rgba(0, 0, 0, 0.22)",
        ...style
      }}
      onPointerMove={(event) => {
        if (!canTilt || shouldReduceMotion) {
          return;
        }
        const target = event.currentTarget as HTMLElement;
        const bounds = target.getBoundingClientRect();
        const x = (event.clientX - bounds.left) / bounds.width - 0.5;
        const y = (event.clientY - bounds.top) / bounds.height - 0.5;
        setTilt({ x: x * 10, y: -y * 10 });
      }}
      onPointerLeave={() => {
        if (!canTilt || shouldReduceMotion) {
          return;
        }
        setTilt({ x: 0, y: 0 });
      }}
    >
      {icon ? <div className="mb-4">{icon}</div> : null}
      <h3 className="section-title mb-2 text-[1rem] font-bold text-white">{title}</h3>
      <p className="text-sm leading-6 text-white/72">{text}</p>
    </article>
  );
}
