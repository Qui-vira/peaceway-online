"use client";

import { motion, useReducedMotion, type Variants } from "framer-motion";
import { siteConfig } from "@/lib/constants";

const TAG = "Peaceway Online · Igando, Lagos, Nigeria";
const HEADLINE = ["YOUR LAGOS", "PHARMACY", "IS NOW ONLINE"];
const EASE = [0.22, 0.61, 0.36, 1] as const;

/**
 * Animated hero copy (Framer Motion): the tagline types in character by
 * character, the headline wipes up (clip-path, so the gradient text stays
 * intact), then the subtext and CTAs fade up. Static under reduced-motion.
 */
export function HeroContent(): JSX.Element {
  const reduce = useReducedMotion();

  const hover = reduce
    ? {}
    : {
        whileHover: { y: -2, scale: 1.015 },
        whileTap: { scale: 0.97 },
        transition: { type: "spring" as const, stiffness: 420, damping: 24 },
      };
  const cta = (
    <>
      <motion.a
        className="bp"
        href={siteConfig.telegramBotUrl}
        target="_blank"
        rel="noreferrer noopener"
        {...hover}
      >
        Order on Telegram
      </motion.a>
      <motion.a className="bg2" href="/request" {...hover}>
        Check Product Availability
      </motion.a>
    </>
  );

  if (reduce) {
    return (
      <div className="hcon">
        <div className="htag">{TAG}</div>
        <h1 className="hh">
          YOUR LAGOS
          <br />
          PHARMACY
          <br />
          IS NOW ONLINE
        </h1>
        <p className="hs">Genuine medicines, pharmacist guidance, and delivery across Lagos.</p>
        <div className="ctg">{cta}</div>
      </div>
    );
  }

  const tagWrap: Variants = {
    hidden: {},
    show: { transition: { staggerChildren: 0.026, delayChildren: 0.2 } },
  };
  const tagChar: Variants = {
    hidden: { opacity: 0 },
    show: { opacity: 1, transition: { duration: 0.01 } },
  };

  return (
    <div className="hcon">
      <motion.div
        className="htag"
        variants={tagWrap}
        initial="hidden"
        animate="show"
        aria-label={TAG}
      >
        {TAG.split("").map((c, i) => (
          <motion.span key={i} variants={tagChar} aria-hidden>
            {c === " " ? " " : c}
          </motion.span>
        ))}
        <span className="type-caret" aria-hidden />
      </motion.div>

      {/* The wipe is an overflow mask + translate, not an animated clip-path.
          clip-path interpolation is the least reliable way to do this, and a
          line that fails to animate stays clipped to nothing - i.e. an
          invisible headline. A transform is the same animation the subtext and
          CTAs below already use, so it fails the same way they do: never. */}
      <h1 className="hh" aria-label="Your Lagos pharmacy is now online">
        {HEADLINE.map((line, i) => (
          <span key={line} className="hh-mask" aria-hidden>
            <motion.span
              className="hh-line"
              initial={{ y: "110%" }}
              animate={{ y: "0%" }}
              transition={{ duration: 0.8, ease: EASE, delay: 1.05 + i * 0.13 }}
            >
              {line}
            </motion.span>
          </span>
        ))}
      </h1>

      <motion.p
        className="hs"
        initial={{ y: 18, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ duration: 0.6, ease: EASE, delay: 1.55 }}
      >
        Genuine medicines, pharmacist guidance, and delivery across Lagos.
      </motion.p>

      <motion.div
        className="ctg"
        initial={{ y: 18, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ duration: 0.6, ease: EASE, delay: 1.72 }}
      >
        {cta}
      </motion.div>
    </div>
  );
}
