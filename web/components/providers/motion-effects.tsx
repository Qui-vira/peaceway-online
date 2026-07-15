"use client";

import { useEffect } from "react";

/* Foreground reveal: fade + slight upward slide, staggered within a group.
   Only elements BELOW the fold at setup time are tagged, so nothing visible
   (hero included) is ever hidden - if JS fails, the page stays fully static
   and fully visible. */
const REVEAL_SECTIONS = "#s2, #s3, #s4, #s5, #s6, #s7, #s8, #s9, footer.ft";
// Section headings/taglines are now animated by Framer Motion (TextFX/SplitText),
// so the IntersectionObserver reveal only handles cards, list rows, and CTAs.
const REVEAL_TARGETS = [
  ".pc",
  ".gc",
  ".sstep",
  ".titem",
  ".tgcard",
  ".ctcard",
  ".ctitem",
  ".cb",
  ".con .bp",
  ".con .bg2",
  ".fg > div",
].join(", ");
const STAGGER_MS = 70;
const STAGGER_CAP_MS = 420;

function setupReveals(): (() => void) | undefined {
  const sections = document.querySelectorAll(REVEAL_SECTIONS);
  if (!sections.length) return undefined;

  const viewportBottom = window.innerHeight * 0.92;
  const viewportRight = window.innerWidth * 0.92;
  const groupCounts = new Map<Element, number>();
  const tagged: HTMLElement[] = [];

  sections.forEach((section) => {
    section.querySelectorAll<HTMLElement>(REVEAL_TARGETS).forEach((el) => {
      const rect = el.getBoundingClientRect();
      // Skip only what's on screen right now (below-the-fold vertically OR
      // off to the right in the mobile carousel gets tagged for reveal).
      if (rect.top <= viewportBottom && rect.left <= viewportRight) return;
      const parent = el.parentElement ?? section;
      const index = groupCounts.get(parent) ?? 0;
      groupCounts.set(parent, index + 1);
      el.classList.add("pw-reveal");
      el.style.transitionDelay = `${Math.min(index * STAGGER_MS, STAGGER_CAP_MS)}ms`;
      tagged.push(el);
    });
  });

  if (!tagged.length) return undefined;

  const timeouts = new Set<number>();
  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) return;
        const el = entry.target as HTMLElement;
        observer.unobserve(el);
        el.classList.add("pw-in");
        // Strip reveal classes after the transition so card hover
        // transitions return to their original stylesheet timing.
        const delay = parseFloat(el.style.transitionDelay) || 0;
        const id = window.setTimeout(() => {
          el.classList.remove("pw-reveal", "pw-in");
          el.style.transitionDelay = "";
          timeouts.delete(id);
        }, delay + 750);
        timeouts.add(id);
      });
    },
    { threshold: 0.1, rootMargin: "0px 0px -6% 0px" }
  );

  tagged.forEach((el) => observer.observe(el));

  return () => {
    observer.disconnect();
    timeouts.forEach((id) => window.clearTimeout(id));
    tagged.forEach((el) => {
      el.classList.remove("pw-reveal", "pw-in");
      el.style.transitionDelay = "";
    });
  };
}

/* Desktop parallax: the giant background section numbers (.snbg) drift against
   the pinned foreground content as each scene scrolls, adding depth (the
   article's "different speeds" parallax). Desktop only - mobile is a carousel;
   skipped under reduced-motion (both here and via the global .snbg transform
   reset). Scroll-driven + rAF-throttled, matching the carousel-dots pattern. */
function setupParallax(): (() => void) | undefined {
  if (window.matchMedia("(max-width: 800px)").matches) return undefined;
  const items: Array<{ el: HTMLElement; scene: HTMLElement; speed: number }> = [];
  document.querySelectorAll<HTMLElement>(".scene").forEach((scene) => {
    const num = scene.querySelector<HTMLElement>(".snbg");
    if (num) items.push({ el: num, scene, speed: 0.14 });
  });
  if (!items.length) return undefined;

  let raf = 0;
  const update = (): void => {
    raf = 0;
    const vh = window.innerHeight;
    for (const it of items) {
      const r = it.scene.getBoundingClientRect();
      if (r.bottom < 0 || r.top > vh) continue; // offscreen - skip
      const center = r.top + r.height / 2 - vh / 2;
      it.el.style.transform = `translate3d(0, ${(-center * it.speed).toFixed(1)}px, 0)`;
    }
  };
  const onScroll = (): void => {
    if (!raf) raf = window.requestAnimationFrame(update);
  };
  window.addEventListener("scroll", onScroll, { passive: true });
  window.addEventListener("resize", onScroll);
  update();

  return () => {
    window.removeEventListener("scroll", onScroll);
    window.removeEventListener("resize", onScroll);
    if (raf) window.cancelAnimationFrame(raf);
    items.forEach((it) => {
      it.el.style.transform = "";
    });
  };
}

/* Sticky-scroll reveal for "How It Works": each step highlights (number badge
   fills, siblings dim) as it passes the viewport centre - the article's
   feature-walkthrough effect. Desktop only. No JS = every step stays fully
   visible (the .pw-steplit dimming class is only added here). */
function setupStepHighlight(): (() => void) | undefined {
  if (window.matchMedia("(max-width: 800px)").matches) return undefined;
  const section = document.getElementById("s5");
  const steps = section
    ? Array.from(section.querySelectorAll<HTMLElement>(".sstep"))
    : [];
  if (!section || !steps.length) return undefined;

  section.classList.add("pw-steplit");
  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        entry.target.classList.toggle("is-active", entry.isIntersecting);
      });
    },
    { rootMargin: "-42% 0px -42% 0px" }
  );
  steps.forEach((step) => observer.observe(step));

  return () => {
    observer.disconnect();
    section.classList.remove("pw-steplit");
    steps.forEach((step) => step.classList.remove("is-active"));
  };
}

export function MotionEffects(): JSX.Element | null {
  useEffect(() => {
    if (typeof window === "undefined") {
      return;
    }

    const reduceMotionQuery = window.matchMedia("(prefers-reduced-motion: reduce)");

    const cleanups: Array<() => void> = [];

    // The mobile carousel is gone - phones scroll the scenes vertically like
    // desktop - so there are no slides to page between and no dots to build.

    if (!reduceMotionQuery.matches) {
      const revealCleanup = setupReveals();
      if (revealCleanup) cleanups.push(revealCleanup);

      // Desktop-only scroll depth: parallax section numbers + step highlight.
      const parallaxCleanup = setupParallax();
      if (parallaxCleanup) cleanups.push(parallaxCleanup);
      const stepCleanup = setupStepHighlight();
      if (stepCleanup) cleanups.push(stepCleanup);
    }

    const cleanup = (): void => {
      cleanups.forEach((fn) => fn());
      cleanups.length = 0;
    };

    reduceMotionQuery.addEventListener("change", cleanup, { once: true });

    return cleanup;
  }, []);

  return null;
}
