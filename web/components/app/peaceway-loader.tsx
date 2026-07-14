"use client";

import { motion, useReducedMotion } from "framer-motion";

const HEX = "M70 16 L90 50 L70 84 L30 84 L10 50 L30 16 Z";
const CROSS = "M50 42 L50 58 M42 50 L58 50";
const EASE = [0.22, 0.61, 0.36, 1] as const;

/**
 * Cinematic Peaceway loader. The pharmacy mark assembles in real 3D space:
 * the hexagon outline draws in on a back plane while the circle + cross spring
 * into place on a forward plane, so a slow physical tilt makes them parallax
 * against each other with depth, lighting and a grounded shadow. Static,
 * fully-formed mark under reduced-motion.
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

  if (reduce) {
    return (
      <div className={wrap} style={bg} role="status" aria-label="Loading">
        <svg viewBox="0 0 100 100" width={104} height={104} fill="none" aria-hidden style={{ filter: "drop-shadow(0 0 10px rgba(52,217,138,0.4))" }}>
          <path d={HEX} stroke="#34d98a" strokeWidth={4} strokeLinejoin="round" strokeLinecap="round" />
          <circle cx={50} cy={50} r={15} stroke="#34d98a" strokeWidth={4} />
          <path d={CROSS} stroke="#34d98a" strokeWidth={4} strokeLinecap="round" />
        </svg>
      </div>
    );
  }

  const S = 150;
  return (
    <div className={wrap} style={bg} role="status" aria-label="Loading">
      <div style={{ position: "relative", width: S, height: S, perspective: 950 }}>
        {/* ambient light behind the mark, breathing */}
        <motion.div
          aria-hidden
          style={{
            position: "absolute",
            inset: "-45%",
            borderRadius: "50%",
            background: "radial-gradient(circle, rgba(52,217,138,0.30) 0%, rgba(26,138,80,0.10) 40%, transparent 68%)",
            filter: "blur(16px)",
          }}
          animate={{ opacity: [0.45, 0.85, 0.45], scale: [0.92, 1.08, 0.92] }}
          transition={{ duration: 2.8, ease: "easeInOut", repeat: Infinity }}
        />
        {/* grounded contact shadow */}
        <motion.div
          aria-hidden
          style={{
            position: "absolute",
            left: "50%",
            bottom: -18,
            width: 96,
            height: 18,
            translateX: "-50%",
            borderRadius: "50%",
            background: "rgba(0,0,0,0.55)",
            filter: "blur(10px)",
          }}
          animate={{ scaleX: [1, 0.82, 1], opacity: [0.55, 0.35, 0.55] }}
          transition={{ duration: 5.6, ease: "easeInOut", repeat: Infinity }}
        />
        {/* 3D stage: slow physical tilt so the planes parallax */}
        <motion.div
          style={{ position: "absolute", inset: 0, transformStyle: "preserve-3d" }}
          initial={{ rotateY: -22, rotateX: 12 }}
          animate={{ rotateY: [-16, 16, -16], rotateX: [9, -6, 9] }}
          transition={{ duration: 5.6, ease: "easeInOut", repeat: Infinity }}
        >
          {/* back plane: hexagon outline draws in */}
          <svg
            viewBox="0 0 100 100"
            width={S}
            height={S}
            fill="none"
            style={{ position: "absolute", inset: 0, filter: "drop-shadow(0 0 9px rgba(52,217,138,0.6))" }}
          >
            <motion.path
              d={HEX}
              stroke="#34d98a"
              strokeWidth={4}
              strokeLinejoin="round"
              strokeLinecap="round"
              initial={{ pathLength: 0, opacity: 0 }}
              animate={{ pathLength: 1, opacity: 1 }}
              transition={{ duration: 1.3, ease: EASE }}
            />
          </svg>
          {/* forward plane: circle + cross spring in, lifted in Z for depth */}
          <svg
            viewBox="0 0 100 100"
            width={S}
            height={S}
            fill="none"
            style={{ position: "absolute", inset: 0, transform: "translateZ(26px)", filter: "drop-shadow(0 0 7px rgba(52,217,138,0.55))" }}
          >
            <motion.g
              style={{ transformBox: "fill-box", transformOrigin: "center" }}
              initial={{ scale: 0, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              transition={{ delay: 0.85, type: "spring", stiffness: 220, damping: 11 }}
            >
              <circle cx={50} cy={50} r={15} stroke="#34d98a" strokeWidth={4} />
              <motion.path
                d={CROSS}
                stroke="#eafff3"
                strokeWidth={4}
                strokeLinecap="round"
                initial={{ pathLength: 0 }}
                animate={{ pathLength: 1 }}
                transition={{ delay: 1.15, duration: 0.5, ease: EASE }}
              />
            </motion.g>
          </svg>
        </motion.div>
      </div>
    </div>
  );
}
