"use client";

import { useEffect } from "react";

/* Foreground reveal: fade + slight upward slide, staggered within a group.
   Only elements BELOW the fold at setup time are tagged, so nothing visible
   (hero included) is ever hidden - if JS fails, the page stays fully static
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

/* Mobile landing carousel dots: one per slide, tracks swipe position.
   Navigation, not decoration - runs even under prefers-reduced-motion. */
function setupCarouselDots(reducedMotion: boolean): (() => void) | undefined {
  if (!window.matchMedia("(max-width: 800px)").matches) return undefined;
  const track = document.getElementById("lmain");
  if (!track || !document.getElementById("s1")) return undefined;

  const slides = Array.from(track.children).filter(
    (child): child is HTMLElement =>
      child instanceof HTMLElement &&
      (child.classList.contains("scene") || child.matches("footer.ft"))
  );
  if (slides.length < 2) return undefined;

  const dotsContainers = Array.from(document.querySelectorAll<HTMLElement>(".pw-dots"));
  const existingDots =
    dotsContainers.find((candidate) => candidate.parentElement === track) ??
    dotsContainers[0];
  dotsContainers.forEach((candidate) => {
    if (candidate !== existingDots) candidate.remove();
  });
  const dots = existingDots ?? document.createElement("div");
  dots.className = "pw-dots";
  if (dots.querySelectorAll(".pw-dot").length !== slides.length) {
    dots.textContent = "";
    slides.forEach((_, i) => {
      const b = document.createElement("button");
      b.type = "button";
      b.className = "pw-dot" + (i === 0 ? " is-active" : "");
      b.setAttribute("aria-label", `Go to section ${i + 1}`);
      dots.appendChild(b);
    });
  }

  const buttons = Array.from(dots.querySelectorAll<HTMLButtonElement>(".pw-dot"));
  const removeClickListeners = buttons.map((b, i) => {
    const onClick = (): void => {
      track.scrollTo({
        left: i * track.clientWidth,
        behavior: reducedMotion ? "auto" : "smooth",
      });
    };
    b.addEventListener("click", onClick);
    return () => b.removeEventListener("click", onClick);
  });
  if (dots.parentElement !== track) track.prepend(dots);

  let raf = 0;
  const update = (): void => {
    raf = 0;
    const active = Math.round(track.scrollLeft / Math.max(1, track.clientWidth));
    buttons.forEach((b, i) => b.classList.toggle("is-active", i === active));
  };
  const onScroll = (): void => {
    if (!raf) raf = window.requestAnimationFrame(update);
  };
  track.addEventListener("scroll", onScroll, { passive: true });

  return () => {
    track.removeEventListener("scroll", onScroll);
    removeClickListeners.forEach((remove) => remove());
    if (raf) window.cancelAnimationFrame(raf);
    if (!existingDots) dots.remove();
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
    const finePointerQuery = window.matchMedia("(hover: hover) and (pointer: fine)");

    const cleanups: Array<() => void> = [];

    // Carousel dots are navigation - they run even under reduced motion, and
    // re-mount when the viewport crosses the mobile breakpoint (rotation,
    // resize, or emulation applying after hydration).
    const carouselMq = window.matchMedia("(max-width: 800px)");
    let dotsCleanup = setupCarouselDots(reduceMotionQuery.matches);
    const onCarouselMqChange = (): void => {
      dotsCleanup?.();
      dotsCleanup = setupCarouselDots(reduceMotionQuery.matches);
    };
    carouselMq.addEventListener("change", onCarouselMqChange);
    cleanups.push(() => {
      carouselMq.removeEventListener("change", onCarouselMqChange);
      dotsCleanup?.();
    });

    if (!reduceMotionQuery.matches) {
      const revealCleanup = setupReveals();
      if (revealCleanup) cleanups.push(revealCleanup);

      // Desktop-only scroll depth: parallax section numbers + step highlight.
      const parallaxCleanup = setupParallax();
      if (parallaxCleanup) cleanups.push(parallaxCleanup);
      const stepCleanup = setupStepHighlight();
      if (stepCleanup) cleanups.push(stepCleanup);

      // Custom cursor only makes sense with a mouse
      if (finePointerQuery.matches && !carouselMq.matches) {
        const cursorCleanup = setupCursor();
        if (cursorCleanup) cleanups.push(cursorCleanup);
      }
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
