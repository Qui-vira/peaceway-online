"use client";

import { useEffect, useRef } from "react";

type Manifest = { count: number; width: number; height: number };

/** Scroll fraction over which the pharmacy signage fades out as the building explodes. */
const SIGNAGE_FADE = 0.18;

/**
 * Scroll-linked image sequence on a canvas (the Apple product-page technique).
 * The building frames are matted onto transparency, so the canvas draws them
 * straight over the dark hero. Scroll position within the host scene maps to
 * frame index; a lerp smooths the scrub. Under reduced-motion, mobile, or
 * save-data we skip the preload and paint a single static frame.
 *
 * A signage layer (the pharmacy branding the render dropped) sits in the same
 * contain-fit box as the canvas so it aligns to the assembled building, and
 * fades out over the first ~18% of scroll as the building comes apart.
 */
export function ScrollSequence({ sceneId = "s1" }: { sceneId?: string }): JSX.Element {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const signageRef = useRef<HTMLImageElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const mobile = window.matchMedia("(max-width: 800px)").matches;
    const saveData = Boolean(
      (navigator as unknown as { connection?: { saveData?: boolean } }).connection?.saveData
    );
    const lightMode = reduce || mobile || saveData;
    const dir = mobile || saveData ? "mobile" : "desktop";

    let count = 0;
    const images: Array<HTMLImageElement | undefined> = [];
    let current = 0; // displayed frame (float, lerped toward target)
    let target = 0;
    let raf = 0;
    let disposed = false;

    const scene = document.getElementById(sceneId);
    const frameSrc = (i: number): string =>
      `/sequence/${dir}/frame_${String(i + 1).padStart(4, "0")}.webp`;

    // Signage overlay (aligns via matching object-fit: contain in CSS).
    const signage = signageRef.current;
    if (signage) signage.src = `/branding/signage-${dir}.webp`;
    const setSignage = (o: number): void => {
      if (signage) signage.style.opacity = String(Math.max(0, Math.min(1, o)));
    };

    const draw = (fidx: number): void => {
      const i = Math.max(0, Math.min(count - 1, Math.round(fidx)));
      const img = images[i];
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      if (!img || !img.complete || img.naturalWidth === 0) return;
      const cw = canvas.width;
      const ch = canvas.height;
      const s = Math.min(cw / img.naturalWidth, ch / img.naturalHeight);
      const w = img.naturalWidth * s;
      const h = img.naturalHeight * s;
      ctx.drawImage(img, (cw - w) / 2, (ch - h) / 2, w, h);
    };

    const resize = (): void => {
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      const rect = canvas.getBoundingClientRect();
      canvas.width = Math.max(1, Math.round(rect.width * dpr));
      canvas.height = Math.max(1, Math.round(rect.height * dpr));
      draw(current);
    };

    const progress = (): number => {
      if (!scene) return 0;
      const rect = scene.getBoundingClientRect();
      const total = rect.height - window.innerHeight;
      if (total <= 0) return 0;
      return Math.max(0, Math.min(1, -rect.top / total));
    };

    // rAF ticker: read scroll position each frame (robust — does not rely on
    // `scroll` events, which some layouts/engines don't emit for programmatic
    // or container scrolls). Runs only while the hero scene is on screen.
    let lastDrawn = -1;
    let lastSig = -1;
    const frame = (): void => {
      raf = window.requestAnimationFrame(frame);
      if (count < 2) return;
      const p = progress();
      target = p * (count - 1);
      current += (target - current) * 0.2;
      if (Math.abs(target - current) < 0.05) current = target;
      const fi = Math.round(current);
      if (fi !== lastDrawn) {
        draw(current);
        lastDrawn = fi;
      }
      const o = Math.max(0, Math.min(1, 1 - p / SIGNAGE_FADE));
      if (Math.abs(o - lastSig) > 0.01) {
        setSignage(o);
        lastSig = o;
      }
    };
    const startLoop = (): void => {
      if (!raf) raf = window.requestAnimationFrame(frame);
    };
    const stopLoop = (): void => {
      if (raf) {
        window.cancelAnimationFrame(raf);
        raf = 0;
      }
    };

    // ── Light mode: one static frame + signage at rest, no preloading ───────
    if (lightMode) {
      count = 1;
      setSignage(1);
      const img = new Image();
      img.decoding = "async";
      img.onload = () => {
        if (disposed) return;
        images[0] = img;
        resize();
      };
      img.src = frameSrc(0);
      resize();
      window.addEventListener("resize", resize);
      return () => {
        disposed = true;
        window.removeEventListener("resize", resize);
      };
    }

    // ── Full mode: load manifest, preload all frames, scrub to scroll ───────
    setSignage(1);
    fetch("/sequence/manifest.json")
      .then((r) => r.json())
      .then((m: Manifest) => {
        if (disposed) return;
        count = m.count;
        images.length = count;
        for (let i = 0; i < count; i++) {
          const img = new Image();
          img.decoding = "async";
          img.onload = () => {
            if (i === 0) draw(current);
          };
          img.src = frameSrc(i);
          images[i] = img;
        }
        resize();
      })
      .catch(() => {
        /* no manifest = leave the dark fallback (.sv-fb) showing */
      });

    // Run the ticker only while the hero scene is on screen (battery-friendly).
    const io = new IntersectionObserver(
      ([entry]) => (entry.isIntersecting ? startLoop() : stopLoop()),
      { threshold: 0 }
    );
    if (scene) io.observe(scene);
    else startLoop();
    window.addEventListener("resize", resize);
    resize();

    return () => {
      disposed = true;
      io.disconnect();
      stopLoop();
      window.removeEventListener("resize", resize);
    };
  }, [sceneId]);

  return (
    <div className="pw-seq" aria-hidden="true">
      <canvas ref={canvasRef} className="pw-seq-canvas" />
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img ref={signageRef} className="pw-seq-signage" alt="" aria-hidden="true" />
    </div>
  );
}
