"use client";

import { useEffect } from "react";

/* Foreground reveal: fade + slight upward slide, staggered within a group.
   Only elements BELOW the fold at setup time are tagged, so nothing visible
   (hero included) is ever hidden — if JS fails, the page stays fully static
   and fully visible. */
const REVEAL_SECTIONS = "#s2, #s3, #s4, #s5, #s6, #s7, #s8, #s9, footer.ft";
const REVEAL_TARGETS = [
  ".stag",
  ".shead",
  ".ssub",
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
  const groupCounts = new Map<Element, number>();
  const tagged: HTMLElement[] = [];

  sections.forEach((section) => {
    section.querySelectorAll<HTMLElement>(REVEAL_TARGETS).forEach((el) => {
      if (el.getBoundingClientRect().top <= viewportBottom) return; // already visible — leave static
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

function setupCursor(): (() => void) | undefined {
  const root = document.documentElement;
  const dot = document.createElement("div");
  const ring = document.createElement("div");

  dot.className = "pw-cursor pw-cursor-dot";
  ring.className = "pw-cursor pw-cursor-ring";

  document.body.append(dot, ring);
  root.classList.add("has-custom-cursor");

  const hoverSelector = [
    "a",
    "button",
    "[role='button']",
    "[data-cursor-hover='true']",
    ".bp",
    ".bg2",
    ".ncta",
    ".nl",
    ".fl",
    ".tgcard",
    ".ctcard",
    ".pc",
    ".gc",
    ".ctitem",
    ".fsi"
  ].join(", ");

  let pointerX = window.innerWidth / 2;
  let pointerY = window.innerHeight / 2;
  let ringX = pointerX;
  let ringY = pointerY;
  let visible = false;
  let hovering = false;
  let rafId = 0;

  const applyState = (): void => {
    dot.classList.toggle("is-visible", visible);
    ring.classList.toggle("is-visible", visible);
    dot.classList.toggle("is-hover", hovering);
    ring.classList.toggle("is-hover", hovering);
    root.classList.toggle("cursor-hover", hovering);
  };

  const updateHoverState = (): void => {
    const element = document.elementFromPoint(pointerX, pointerY) as HTMLElement | null;
    const nextHover = Boolean(element?.closest(hoverSelector));

    if (nextHover !== hovering) {
      hovering = nextHover;
      applyState();
    }
  };

  const tick = (): void => {
    ringX += (pointerX - ringX) * 0.14;
    ringY += (pointerY - ringY) * 0.14;

    updateHoverState();

    const dotScale = hovering ? 0.92 : 1;
    const ringScale = hovering ? 1.24 : 1;

    dot.style.transform = `translate3d(${pointerX}px, ${pointerY}px, 0) translate(-50%, -50%) scale(${dotScale})`;
    ring.style.transform = `translate3d(${ringX}px, ${ringY}px, 0) translate(-50%, -50%) scale(${ringScale})`;

    if (Math.abs(pointerX - ringX) > 0.1 || Math.abs(pointerY - ringY) > 0.1) {
      rafId = window.requestAnimationFrame(tick);
      return;
    }

    rafId = 0;
  };

  const start = (): void => {
    if (!rafId) {
      rafId = window.requestAnimationFrame(tick);
    }
  };

  const onMove = (event: PointerEvent): void => {
    pointerX = event.clientX;
    pointerY = event.clientY;
    visible = true;
    applyState();
    start();
  };

  const onLeave = (): void => {
    visible = false;
    hovering = false;
    applyState();
  };

  const onDown = (): void => {
    root.classList.add("cursor-pressed");
  };

  const onUp = (): void => {
    root.classList.remove("cursor-pressed");
  };

  window.addEventListener("pointermove", onMove, { passive: true });
  window.addEventListener("pointerleave", onLeave);
  window.addEventListener("blur", onLeave);
  window.addEventListener("pointerdown", onDown);
  window.addEventListener("pointerup", onUp);

  return () => {
    window.removeEventListener("pointermove", onMove);
    window.removeEventListener("pointerleave", onLeave);
    window.removeEventListener("blur", onLeave);
    window.removeEventListener("pointerdown", onDown);
    window.removeEventListener("pointerup", onUp);

    if (rafId) {
      window.cancelAnimationFrame(rafId);
    }

    dot.remove();
    ring.remove();
    root.classList.remove("has-custom-cursor", "cursor-hover", "cursor-pressed");
  };
}

export function MotionEffects(): JSX.Element | null {
  useEffect(() => {
    if (typeof window === "undefined") {
      return;
    }

    const reduceMotionQuery = window.matchMedia("(prefers-reduced-motion: reduce)");
    const finePointerQuery = window.matchMedia("(hover: hover) and (pointer: fine)");

    if (reduceMotionQuery.matches) {
      return; // no reveals, no cursor — everything stays static and visible
    }

    const cleanups: Array<() => void> = [];

    const revealCleanup = setupReveals();
    if (revealCleanup) cleanups.push(revealCleanup);

    // Custom cursor only makes sense with a mouse
    if (finePointerQuery.matches) {
      const cursorCleanup = setupCursor();
      if (cursorCleanup) cleanups.push(cursorCleanup);
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
