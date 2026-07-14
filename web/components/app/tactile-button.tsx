"use client";

import Link from "next/link";
import { motion, useReducedMotion, type HTMLMotionProps } from "framer-motion";
import type { ReactNode } from "react";

/**
 * Tactile "pressable key" buttons. The solid bottom EDGE (a box-shadow) is the
 * physical depth; Framer Motion drives the PRESS as a spring so it depresses
 * with real physics (not a linear CSS transition) and the edge collapses in
 * sync. Primary presses also fire a short haptic (UI/UX Pro Max: "tactile
 * feedback improves interaction feel — navigator.vibrate(10) for important
 * actions"). Reduced-motion drops the movement but keeps the visual state.
 *
 * The `.pw-btn* ` classes in globals.css own the resting look (size, colour,
 * radius, focus ring); this component owns the motion + edge shadow.
 */
type Variant = "primary" | "sm" | "secondary";

const EDGE: Record<Variant, { cls: string; rest: string; tap: string; y: number }> = {
  primary: {
    cls: "pw-btn",
    rest: "0 4px 0 0 #0f673c, 0 6px 14px -6px rgba(0,0,0,0.55)",
    tap: "0 0px 0 0 #0f673c, 0 1px 3px 0 rgba(0,0,0,0.40)",
    y: 4,
  },
  sm: {
    cls: "pw-btn-sm",
    rest: "0 3px 0 0 #0f673c, 0 5px 10px -6px rgba(0,0,0,0.5)",
    tap: "0 0px 0 0 #0f673c, 0 1px 2px 0 rgba(0,0,0,0.4)",
    y: 3,
  },
  secondary: {
    cls: "pw-btn-2",
    rest: "0 4px 0 0 rgba(255,255,255,0.08)",
    tap: "0 0px 0 0 rgba(255,255,255,0.08)",
    y: 4,
  },
};

const SPRING = { type: "spring" as const, stiffness: 620, damping: 22, mass: 0.6 };

function haptic(): void {
  if (typeof navigator !== "undefined" && typeof navigator.vibrate === "function") {
    try {
      navigator.vibrate(10);
    } catch {
      /* not supported / blocked - non-fatal */
    }
  }
}

const MotionLink = motion.create(Link);

type Common = { variant?: Variant };

export function TactileButton({
  variant = "primary",
  className = "",
  disabled,
  onClick,
  children,
  ...rest
}: Common & Omit<HTMLMotionProps<"button">, "ref"> & { children: ReactNode }) {
  const reduce = useReducedMotion();
  const e = EDGE[variant];
  const off = reduce || disabled;
  return (
    <motion.button
      className={`${e.cls} ${className}`.trim()}
      style={{ boxShadow: e.rest }}
      whileTap={off ? undefined : { y: e.y, boxShadow: e.tap }}
      transition={SPRING}
      disabled={disabled}
      onClick={(ev) => {
        if (!disabled && variant === "primary") haptic();
        onClick?.(ev);
      }}
      {...rest}
    >
      {children}
    </motion.button>
  );
}

export function TactileLink({
  variant = "primary",
  className = "",
  href,
  children,
  ...rest
}: Common & Omit<HTMLMotionProps<"a">, "ref"> & { href: string; children: ReactNode }) {
  const reduce = useReducedMotion();
  const e = EDGE[variant];
  return (
    <MotionLink
      href={href}
      className={`${e.cls} ${className}`.trim()}
      style={{ boxShadow: e.rest }}
      whileTap={reduce ? undefined : { y: e.y, boxShadow: e.tap }}
      transition={SPRING}
      onClick={() => {
        if (variant === "primary") haptic();
      }}
      {...rest}
    >
      {children}
    </MotionLink>
  );
}
