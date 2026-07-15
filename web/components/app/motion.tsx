"use client";

import {
  Children,
  cloneElement,
  isValidElement,
  type ReactElement,
  type ReactNode,
} from "react";
import { motion, useReducedMotion, type Variants } from "framer-motion";

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

/** 30-80ms is the legible stagger band; 40ms reads as a reveal, not a wait. */
const STAGGER_MS = 0.04;
/** Base offset before the first item, so the list doesn't start mid-transition. */
const LEAD_MS = 0.02;
/**
 * Cap the stagger at the first few items. Framer's `staggerChildren` has no cap,
 * so on an uncapped list the Nth item's delay is N * step: a 50-item catalogue
 * would leave its back half invisible for ~2s, and a 100-item one for ~4s. Past
 * this index every remaining item shares one delay and arrives together - the
 * reveal stays legible without holding late content hostage to list length.
 */
const STAGGER_CAP = 6;

type StaggerItemProps = {
  children: ReactNode;
  className?: string;
  /** Injected by StaggerList; callers don't pass it. */
  index?: number;
};

/**
 * List container. Hands each StaggerItem its position so the item can compute a
 * capped delay itself - this is why the delay lives on the item and not on a
 * `staggerChildren` here, which cannot be bounded.
 *
 * Only StaggerItem children receive an index, and only they advance the counter,
 * so a mixed list (a SectionLabel followed by rows) staggers the rows correctly
 * and leaves the label alone.
 */
export function StaggerList({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) {
  let itemIndex = 0;
  const positioned = Children.map(children, (child) => {
    if (isValidElement(child) && child.type === StaggerItem) {
      const withIndex = cloneElement(child as ReactElement<StaggerItemProps>, {
        index: itemIndex,
      });
      itemIndex += 1;
      return withIndex;
    }
    return child;
  });

  return (
    <motion.div className={className} initial="hidden" animate="show">
      {positioned}
    </motion.div>
  );
}

/**
 * A list row / card. Rises 8px and fades, after a delay set by its position.
 *
 * `hidden` is the resting state, but the element is in the DOM and hit-testable
 * throughout - this is an entrance, not a gate. If the animation never fires
 * (a hidden tab, a headless renderer), framer still applies the `show` state on
 * mount, so the row cannot ship invisible. That failure mode is exactly how this
 * project's hero headline disappeared on iOS.
 */
export function StaggerItem({ children, className, index = 0 }: StaggerItemProps) {
  const reduce = useReducedMotion();
  const delay = reduce ? 0 : LEAD_MS + Math.min(index, STAGGER_CAP) * STAGGER_MS;
  const item: Variants = {
    hidden: reduce ? { opacity: 0 } : { opacity: 0, y: 8 },
    show: {
      opacity: 1,
      y: 0,
      transition: { duration: reduce ? 0.15 : 0.24, ease: EASE, delay },
    },
  };
  return (
    <motion.div className={className} variants={item}>
      {children}
    </motion.div>
  );
}
