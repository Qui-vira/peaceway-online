"use client";

import { useEffect, useState } from "react";
import { motion, useReducedMotion } from "framer-motion";
import { siteConfig } from "@/lib/constants";

const HEADLINE_LINES = ["YOUR LAGOS", "PHARMACY", "IS NOW ONLINE"];
const HEADLINE = HEADLINE_LINES.join("\n");
const HEADLINE_LABEL = "Your Lagos pharmacy is now online";
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
      {/* Was "Check Product Availability" → /request, which walls a stranger
          behind a registration form before showing them anything. The
          catalogue is 250 real products, ranks at 0.9 in our own sitemap, and
          had no link from this page at all - the only two internal doors were
          /app and /request. Browse first, ask second: /request is still one tap
          away from the app home and the footer. */}
      <motion.a className="bg2" href="/shop" {...hover}>
        Browse Medicines
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
        <p className="hs">Genuine medicines, pharmacist guidance, and delivery across Lagos.</p>
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
        Genuine medicines, pharmacist guidance, and delivery across Lagos.
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
