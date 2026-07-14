"use client";

import { useEffect, useRef } from "react";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/dist/ScrollTrigger";

type Manifest = { count: number; width: number; height: number };

/** Scroll fraction over which the pharmacy signage fades as the building explodes. */
const SIGNAGE_FADE = 0.18;

/**
 * Bump when the frame assets change so browsers re-fetch instead of serving a
 * stale cached .webp (the paths are otherwise stable). v2 = watermark erased.
 */
const ASSET_VER = "4";

/**
 * Scroll-linked image sequence on a canvas (the Apple product-page technique),
 * driven by GSAP ScrollTrigger for reliable scrubbing. The building frames are
 * matted onto transparency and drawn over the dark hero; the CSS-sticky parent
 * keeps the canvas pinned while the sequence plays. A signage layer sits in the
 * same contain-fit box and fades out over the first ~18% of scroll.
 *
 * Under reduced-motion / mobile / save-data we skip preload + ScrollTrigger and
 * paint a single static assembled frame with the signage shown.
 */
export function ScrollSequence({ sceneId = "s1" }: { sceneId?: string }): JSX.Element {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const signageRef = useRef<HTMLImageElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    gsap.registerPlugin(ScrollTrigger);

    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const mobile = window.matchMedia("(max-width: 800px)").matches;
    const saveData = Boolean(
      (navigator as unknown as { connection?: { saveData?: boolean } }).connection?.saveData
    );
    const lightMode = reduce || mobile || saveData;
    const dir = mobile || saveData ? "mobile" : "desktop";

    const scene = document.getElementById(sceneId);
    let count = 0;
    let displayed = 0;
    const images: Array<HTMLImageElement | undefined> = [];
    let disposed = false;
    let trigger: ScrollTrigger | undefined;

    const frameSrc = (i: number): string =>
      `/sequence/${dir}/frame_${String(i + 1).padStart(4, "0")}.webp?v=${ASSET_VER}`;

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
      const s = Math.min(canvas.width / img.naturalWidth, canvas.height / img.naturalHeight);
      const w = img.naturalWidth * s;
      const h = img.naturalHeight * s;
      ctx.drawImage(img, (canvas.width - w) / 2, (canvas.height - h) / 2, w, h);
    };

    const resize = (): void => {
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      const rect = canvas.getBoundingClientRect();
      canvas.width = Math.max(1, Math.round(rect.width * dpr));
      canvas.height = Math.max(1, Math.round(rect.height * dpr));
      draw(displayed);
    };

    // ── Light mode: single static assembled frame + signage, no scrubbing ────
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

    // ── Full mode: preload frames, then scrub with GSAP ScrollTrigger ────────
    setSignage(1);
    fetch("/sequence/manifest.json")
      .then((r) => r.json())
      .then((m: Manifest) => {
        if (disposed || !scene) return;
        count = m.count;
        images.length = count;
        for (let i = 0; i < count; i++) {
          const img = new Image();
          img.decoding = "async";
          img.onload = () => {
            if (i === 0) draw(0);
          };
          img.src = frameSrc(i);
          images[i] = img;
        }
        resize();

        // Scrub the whole sequence across the scene's pinned range (scene is
        // ~190vh with a position:sticky child, so the pin lasts sceneH - vh).
        // The building lives in its own right-side zone (CSS), so the headline
        // stays put and readable while it assembles/explodes.
        trigger = ScrollTrigger.create({
          trigger: scene,
          start: "top top",
          end: () => "+=" + Math.max(1, scene.offsetHeight - window.innerHeight),
          scrub: 0.5,
          invalidateOnRefresh: true,
          onUpdate: (self) => {
            displayed = self.progress * (count - 1);
            draw(displayed);
            setSignage(1 - self.progress / SIGNAGE_FADE);
          },
        });
        ScrollTrigger.refresh();
      })
      .catch(() => {
        /* no manifest = leave the dark fallback (.sv-fb) showing */
      });

    window.addEventListener("resize", resize);
    return () => {
      disposed = true;
      trigger?.kill();
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
