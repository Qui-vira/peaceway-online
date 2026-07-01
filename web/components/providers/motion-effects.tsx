"use client";

import { useEffect } from "react";

export function MotionEffects(): JSX.Element | null {
  useEffect(() => {
    if (typeof window === "undefined") {
      return;
    }

    const root = document.documentElement;
    const reduceMotionQuery = window.matchMedia("(prefers-reduced-motion: reduce)");
    const finePointerQuery = window.matchMedia("(hover: hover) and (pointer: fine)");

    const revealSelector = [
      ".htag",
      ".hh",
      ".hs",
      ".stag",
      ".shead",
      ".ssub",
      ".pc",
      ".gc",
      ".titem",
      ".sstep",
      ".tgcard",
      ".ctcard",
      ".cb",
      ".bp",
      ".bg2",
      ".ncta",
      ".phimg",
      ".ag .ab",
      ".fbd",
      ".fbs",
      ".fct",
      ".fl",
      ".fleg p"
    ].join(", ");

    const revealElements = Array.from(
      new Set(
        Array.from(document.querySelectorAll<HTMLElement>(revealSelector))
      )
    );
    const parallaxElements = Array.from(
      document.querySelectorAll<HTMLElement>(".snbg")
    );
    const tiltElements = Array.from(
      document.querySelectorAll<HTMLElement>(".pc, .gc, .tgcard, .ctcard")
    );
    const videos = Array.from(document.querySelectorAll<HTMLVideoElement>("video"));

    const cleanupFns: Array<() => void> = [];

    const applyReducedMotion = (): void => {
      root.classList.add("reduced-motion");
      root.classList.remove("motion-ready");
      videos.forEach((video) => {
        video.pause();
      });
    };

    if (reduceMotionQuery.matches) {
      applyReducedMotion();
      return undefined;
    }

    revealElements.forEach((element, index) => {
      element.dataset.motionReveal = "true";
      element.style.setProperty("--motion-delay", `${Math.min(index * 45, 320)}ms`);
    });

    parallaxElements.forEach((element) => {
      element.dataset.motionParallax = "true";
    });

    tiltElements.forEach((element) => {
      element.dataset.motionTilt = "true";
    });

    root.classList.add("motion-ready");

    const revealObserver = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          const target = entry.target as HTMLElement;

          if (entry.isIntersecting) {
            target.classList.add("is-visible");

            if (target.tagName === "VIDEO") {
              const video = target as HTMLVideoElement;
              void video.play().catch(() => {
                // Autoplay remains best effort.
              });
            }
            return;
          }

          if (target.tagName === "VIDEO") {
            const video = target as HTMLVideoElement;
            video.pause();
          }
        });
      },
      {
        threshold: 0.18,
        rootMargin: "0px 0px -10% 0px"
      }
    );

    revealElements.forEach((element) => revealObserver.observe(element));
    videos.forEach((video) => {
      video.muted = true;
      video.playsInline = true;
      video.loop = true;
      revealObserver.observe(video);
    });

    cleanupFns.push(() => revealObserver.disconnect());

    const updateParallax = (): void => {
      const viewportHeight = window.innerHeight;

      parallaxElements.forEach((element) => {
        const section = element.closest(".sticky");
        if (!section) {
          return;
        }

        const rect = section.getBoundingClientRect();
        const center = rect.top + rect.height / 2;
        const distance = (center - viewportHeight / 2) / (viewportHeight / 2);
        const offset = Math.max(-24, Math.min(24, -distance * 18));

        element.style.transform = `translate3d(0, ${offset}px, 0)`;
      });
    };

    let rafId = 0;
    const scheduleParallax = (): void => {
      if (rafId) {
        return;
      }

      rafId = window.requestAnimationFrame(() => {
        rafId = 0;
        updateParallax();
      });
    };

    window.addEventListener("scroll", scheduleParallax, { passive: true });
    window.addEventListener("resize", scheduleParallax);
    cleanupFns.push(() => {
      window.removeEventListener("scroll", scheduleParallax);
      window.removeEventListener("resize", scheduleParallax);
      if (rafId) {
        window.cancelAnimationFrame(rafId);
      }
    });

    updateParallax();

    if (finePointerQuery.matches) {
      const resetTilt = (element: HTMLElement): void => {
        element.style.transform = "";
      };

      tiltElements.forEach((element) => {
        const onMove = (event: PointerEvent): void => {
          const rect = element.getBoundingClientRect();
          const x = (event.clientX - rect.left) / rect.width - 0.5;
          const y = (event.clientY - rect.top) / rect.height - 0.5;
          const rotateY = Math.max(-8, Math.min(8, x * 12));
          const rotateX = Math.max(-8, Math.min(8, -y * 12));

          element.style.transform = `perspective(900px) rotateX(${rotateX}deg) rotateY(${rotateY}deg) translateY(-2px)`;
        };

        const onEnter = (): void => {
          element.dataset.motionHover = "true";
        };

        const onLeave = (): void => {
          delete element.dataset.motionHover;
          resetTilt(element);
        };

        element.addEventListener("pointerenter", onEnter);
        element.addEventListener("pointermove", onMove);
        element.addEventListener("pointerleave", onLeave);

        cleanupFns.push(() => {
          element.removeEventListener("pointerenter", onEnter);
          element.removeEventListener("pointermove", onMove);
          element.removeEventListener("pointerleave", onLeave);
          resetTilt(element);
        });
      });
    }

    const onMotionChange = (): void => {
      if (reduceMotionQuery.matches) {
        applyReducedMotion();
        return;
      }

      root.classList.remove("reduced-motion");
      root.classList.add("motion-ready");
      updateParallax();
    };

    reduceMotionQuery.addEventListener("change", onMotionChange);
    cleanupFns.push(() => {
      reduceMotionQuery.removeEventListener("change", onMotionChange);
    });

    return () => {
      cleanupFns.forEach((cleanup) => cleanup());
      root.classList.remove("motion-ready");
    };
  }, []);

  return null;
}
