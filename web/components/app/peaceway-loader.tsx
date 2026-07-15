"use client";

import { motion, useReducedMotion } from "framer-motion";

const HEX = "M70 16 L90 50 L70 84 L30 84 L10 50 L30 16 Z";
const CROSS = "M50 42 L50 58 M42 50 L58 50";
const EASE = [0.22, 0.61, 0.36, 1] as const;

/**
 * Peaceway loading mark.
 *
 * This is the most-seen animation in the app - it fires on every entry to
 * /app, /reminders, /requests and /profile - so it is deliberately plain. It
 * used to assemble in 3D over ~2s (a 1.3s outline draw, a spring cross, and
 * two infinite 5.6s tilt/breathe loops), which announced the latency instead
 * of covering it; a faster spinner makes the same wait feel shorter. The mark
 * now lands in 250ms and holds a single-property opacity pulse.
 *
 * Static, fully-formed mark under reduced-motion.
 */
export function PeacewayLoader({ fullscreen = true }: { fullscreen?: boolean }): JSX.Element {
  const reduce = useReducedMotion();
  const wrap = fullscreen
    ? "fixed inset-0 z-50 flex items-center justify-center"
    : "flex min-h-[62vh] items-center justify-center";
  const bg = fullscreen
    ? {
        background:
          "radial-gradient(ellipse 60% 55% at 50% 45%, rgba(26,138,80,0.10) 0%, transparent 70%), #0b0c09",
      }
    : undefined;

  const mark = (
    <svg
      viewBox="0 0 100 100"
      width={104}
      height={104}
      fill="none"
      aria-hidden
      style={{ filter: "drop-shadow(0 0 10px rgba(52,217,138,0.4))" }}
    >
      <path d={HEX} stroke="#34d98a" strokeWidth={4} strokeLinejoin="round" strokeLinecap="round" />
      <circle cx={50} cy={50} r={15} stroke="#34d98a" strokeWidth={4} />
      <path d={CROSS} stroke="#eafff3" strokeWidth={4} strokeLinecap="round" />
    </svg>
  );

  if (reduce) {
    return (
      <div className={wrap} style={bg} role="status" aria-label="Loading">
        {mark}
      </div>
    );
  }

  return (
    <div className={wrap} style={bg} role="status" aria-label="Loading">
      {/* Entrance from 0.95, never from 0 - nothing appears from nothing. */}
      <motion.div
        initial={{ scale: 0.95, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        transition={{ duration: 0.25, ease: EASE }}
      >
        {/* The wait indicator itself: one property, on the GPU. */}
        <motion.div
          animate={{ opacity: [1, 0.45, 1] }}
          transition={{ duration: 1.1, ease: "easeInOut", repeat: Infinity }}
        >
          {mark}
        </motion.div>
      </motion.div>
    </div>
  );
}
