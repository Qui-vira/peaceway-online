"use client";

import { useEffect, useState } from "react";
import { motion, useReducedMotion } from "framer-motion";
import { siteConfig } from "@/lib/constants";

/**
 * Was "YOUR LAGOS / PHARMACY / IS NOW ONLINE".
 *
 * Two problems with that line. It fixed the business to one city in the largest
 * type on the site, and "is now online" sells the channel - being on the
 * internet - when what is actually being sold is that a licensed pharmacist
 * stands behind the order. The channel is not the product.
 */
const HEADLINE_LINES = ["A LICENSED", "PHARMACY,", "ONLINE"];
const HEADLINE = HEADLINE_LINES.join("\n");
const HEADLINE_LABEL = "A licensed pharmacy, online";
const SUBHEAD =
  "Every order is reviewed by a registered pharmacist before it is dispensed.";
const TYPE_MS = 35; // per-character cadence
const EASE = [0.22, 0.61, 0.36, 1] as const;

/**
 * Fine-pointer test for hover motion. The stylesheet gates its hover states on
 * `(hover: hover) and (pointer: fine)`; Framer Motion's `whileHover` ignores
 * that and fires on touch, where a "hover" lift has no meaning. Touch devices
 * get their press feedback from `@media (hover: none)` in globals.css instead.
 */
function useFinePointer(): boolean {
  const [fine, setFine] = useState(false);
  useEffect(() => {
    const mq = window.matchMedia("(hover: hover) and (pointer: fine)");
    const sync = (): void => setFine(mq.matches);
    sync();
    mq.addEventListener("change", sync);
    return () => mq.removeEventListener("change", sync);
  }, []);
  return fine;
}

/**
 * Hero copy. The headline types in character by character; the subtext and CTAs
 * fade up after. Under reduced-motion everything is static and complete.
 *
 * The typewriter overlays an invisible full-text "ghost" that reserves the
 * headline's final three-line box, so the copy below never reflows as the
 * characters appear. The accessible name comes from the h1's aria-label (valid
 * on a heading) with the animated characters aria-hidden, so assistive tech
 * hears the finished line, not a stream of partial words.
 */
export function HeroContent(): JSX.Element {
  const reduce = useReducedMotion();
  const finePointer = useFinePointer();
  const [typed, setTyped] = useState("");

  useEffect(() => {
    if (reduce) return;
    setTyped("");
    let i = 0;
    const id = window.setInterval(() => {
      i += 1;
      setTyped(HEADLINE.slice(0, i));
      if (i >= HEADLINE.length) window.clearInterval(id);
    }, TYPE_MS);
    return () => window.clearInterval(id);
  }, [reduce]);

  // reduce short-circuits to the full line with no dependence on the effect, so
  // there is never a flash of empty headline for motion-averse users.
  const shown = reduce ? HEADLINE : typed;
  const typingDone = shown.length >= HEADLINE.length;

  const hover =
    reduce || !finePointer
      ? {}
      : {
          whileHover: { y: -2, scale: 1.015 },
          whileTap: { scale: 0.97 },
          transition: { type: "spring" as const, stiffness: 420, damping: 24 },
        };
  // Telegram used to be the primary action and the catalogue the secondary.
  // That ordering sold the channel ahead of the pharmacy, and sent a first-time
  // visitor off-site before they had seen a single product. The dispensary's own
  // catalogue leads now; Telegram remains one tap away for customers who already
  // order that way.
  const cta = (
    <>
      <motion.a className="bp" href="/shop" {...hover}>
        Browse Medicines
      </motion.a>
      <motion.a
        className="bg2"
        href={siteConfig.telegramBotUrl}
        target="_blank"
        rel="noreferrer noopener"
        {...hover}
      >
        Order on Telegram
      </motion.a>
    </>
  );

  const headline = (
    <h1 className="hh" aria-label={HEADLINE_LABEL}>
      <span className="hh-ghost" aria-hidden>
        {HEADLINE}
      </span>
      <span className="hh-type" aria-hidden>
        {shown}
        {!reduce && (
          <span className={`type-caret${typingDone ? " is-done" : ""}`} />
        )}
      </span>
    </h1>
  );

  if (reduce) {
    return (
      <div className="hcon">
        {headline}
        <p className="hs">{SUBHEAD}</p>
        <div className="ctg">{cta}</div>
      </div>
    );
  }

  return (
    <div className="hcon">
      {headline}

      <motion.p
        className="hs"
        initial={{ y: 18, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ duration: 0.3, ease: EASE, delay: 0.34 }}
      >
        {SUBHEAD}
      </motion.p>

      <motion.div
        className="ctg"
        initial={{ y: 18, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ duration: 0.3, ease: EASE, delay: 0.45 }}
      >
        {cta}
      </motion.div>
    </div>
  );
}
