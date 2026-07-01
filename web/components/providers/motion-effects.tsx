"use client";

import { useEffect } from "react";

export function MotionEffects(): JSX.Element | null {
  useEffect(() => {
    if (typeof window === "undefined") {
      return;
    }

    const reduceMotionQuery = window.matchMedia("(prefers-reduced-motion: reduce)");
    const finePointerQuery = window.matchMedia("(hover: hover) and (pointer: fine)");

    if (reduceMotionQuery.matches || !finePointerQuery.matches) {
      return;
    }

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

    const cleanup = (): void => {
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

    reduceMotionQuery.addEventListener("change", cleanup, { once: true });

    return cleanup;
  }, []);

  return null;
}
