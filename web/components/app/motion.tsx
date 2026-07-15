"use client";

import { motion, useReducedMotion, type Variants } from "framer-motion";
import type { ReactNode } from "react";

/**
 * The app surface's motion vocabulary.
 *
 * The product had none: zero AnimatePresence, zero layoutId, zero template.tsx,
 * and its only choreography (product-card's GSAP hover) was gated behind
 * `(hover: hover)` and therefore dead on the phone that PRODUCT.md calls the
 * primary device. Content hard-cut into view, which is what made a real product
 * read as a website that renders app data.
 *
 * The rules this follows, from DESIGN.md and the product register:
 * - Motion conveys state, never decoration.
 * - 150-250ms on most transitions. Users are in a task; nobody wants to watch it
 *   load. Nothing here delays usability - entrances are opacity+transform only,
 *   the content is hit-testable immediately.
 * - Ease out, no bounce. `EASE` is the system's existing curve, already used by
 *   the CSS layer, so JS and CSS motion agree.
 * - Transform and opacity only. No layout properties, so no CLS and no
 *   scroll-linked reflow.
 * - prefers-reduced-motion collapses every variant to a plain crossfade rather
 *   than to nothing: the reveal still happens, it just doesn't travel.
 */

/** The system's out-curve. Matches cubic-bezier(0.22,0.61,0.36,1) in globals.css. */
export const EASE = [0.22, 0.61, 0.36, 1] as const;

/** Press physics. Matches TactileButton, so the whole product presses one way. */
export const PRESS_SPRING = {
  type: "spring" as const,
  stiffness: 620,
  damping: 22,
  mass: 0.6,
};

/** 30-80ms is the legible stagger band; 40 with a cap keeps long lists honest. */
const STAGGER_MS = 0.04;
const STAGGER_CAP = 6;

/**
 * List container. Staggers its children in, but only the first few - a 40-item
 * order history should not take two seconds to finish arriving, and stagger is
 * decorative: it must never gate reading.
 */
export function StaggerList({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) {
  const reduce = useReducedMotion();
  const container: Variants = {
    hidden: {},
    show: {
      transition: reduce
        ? {}
        : { staggerChildren: STAGGER_MS, delayChildren: 0.02 },
    },
  };
  return (
    <motion.div
      className={className}
      variants={container}
      initial="hidden"
      animate="show"
    >
      {children}
    </motion.div>
  );
}

/**
 * A list row / card. Rises 8px and fades.
 *
 * `initial` is the hidden state, but the element is in the DOM and hit-testable
 * throughout - this is an entrance, not a gate. If the animation never fires
 * (a hidden tab, a headless renderer), framer still applies the `animate` state
 * on mount, so the row cannot ship invisible. That failure mode is exactly how
 * this project's hero headline disappeared on iOS.
 */
export function StaggerItem({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) {
  const reduce = useReducedMotion();
  const item: Variants = {
    hidden: reduce ? { opacity: 0 } : { opacity: 0, y: 8 },
    show: {
      opacity: 1,
      y: 0,
      transition: { duration: reduce ? 0.15 : 0.24, ease: EASE },
    },
  };
  return (
    <motion.div className={className} variants={item}>
      {children}
    </motion.div>
  );
}

/**
 * Section entrance for a whole block of content. One fade+rise, not a per-child
 * stagger - reserving stagger for real lists keeps it meaningful instead of
 * becoming the uniform reflex applied to every section on the page.
 */
export function FadeIn({
  children,
  className,
  delay = 0,
}: {
  children: ReactNode;
  className?: string;
  delay?: number;
}) {
  const reduce = useReducedMotion();
  return (
    <motion.div
      className={className}
      initial={reduce ? { opacity: 0 } : { opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: reduce ? 0.15 : 0.24, ease: EASE, delay }}
    >
      {children}
    </motion.div>
  );
}
