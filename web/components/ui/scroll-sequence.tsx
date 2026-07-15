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
const ASSET_VER = "5";

/** Mobile autoplay loads every Nth frame to keep the payload light. */
const MOBILE_STEP = 2;

/**
 * Scroll-linked image sequence on a canvas (the Apple product-page technique).
 *
 * - Desktop: GSAP ScrollTrigger scrubs the whole sequence across the pinned
 *   hero as you scroll (assemble -> explode).
 * - Mobile: the landing is a horizontal scroll-snap carousel, so there's no
 *   vertical scroll to scrub. Instead the sequence AUTOPLAYS a gentle
 *   assemble -> explode -> reassemble loop, paused unless the hero slide is on
 *   screen. Frames are subsampled to keep the mobile payload small.
 * - reduced-motion / save-data: a single static assembled frame, no animation.
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
    const staticMode = reduce || saveData; // respect motion/data prefs -> static frame
    const mobileAuto = mobile && !staticMode; // no vertical scroll on mobile -> autoplay
    const dir = mobile || saveData ? "mobile" : "desktop";

    const scene = document.getElementById(sceneId);
    let count = 0;
    let displayed = 0;
    const images: Array<HTMLImageElement | undefined> = [];
    let disposed = false;
    let trigger: ScrollTrigger | undefined;
    let tl: gsap.core.Timeline | undefined;
    let io: IntersectionObserver | undefined;

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

    // ── Static: single assembled frame (reduced-motion / save-data) ──────────
    if (staticMode) {
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

    // ── Preload frames (subsampled on mobile), then animate ──────────────────
    setSignage(1);
    fetch("/sequence/manifest.json")
      .then((r) => r.json())
      .then((m: Manifest) => {
        if (disposed || !scene) return;
        const step = mobileAuto ? MOBILE_STEP : 1;
        const indices: number[] = [];
        for (let i = 0; i < m.count; i += step) indices.push(i);
        if (indices[indices.length - 1] !== m.count - 1) indices.push(m.count - 1);
        count = indices.length;
        images.length = count;
        indices.forEach((orig, k) => {
          const img = new Image();
          img.decoding = "async";
          img.onload = () => {
            if (k === 0) draw(0);
          };
          img.src = frameSrc(orig);
          images[k] = img;
        });
        resize();

        if (mobileAuto) {
          // Autoplay a gentle assemble -> explode -> reassemble loop; paused
          // unless the hero slide is on screen (saves battery when swiped away).
          const st = { p: 0 };
          const render = (): void => {
            displayed = st.p * (count - 1);
            draw(displayed);
            setSignage(1 - st.p / SIGNAGE_FADE);
          };
          tl = gsap.timeline({ repeat: -1, paused: true });
          tl.to(st, { p: 1, duration: 2.8, ease: "power1.inOut", onUpdate: render })
            .to(st, { p: 1, duration: 1.1, onUpdate: render }) // hold exploded
            .to(st, { p: 0, duration: 2.2, ease: "power1.inOut", onUpdate: render })
            .to(st, { p: 0, duration: 1.0, onUpdate: render }); // hold assembled

          io = new IntersectionObserver(
            (entries) => {
              for (const e of entries) {
                if (e.isIntersecting) tl?.play();
                else tl?.pause();
              }
            },
            { threshold: 0.35 }
          );
          io.observe(scene);
        } else {
          // Desktop: scrub the whole sequence across the scene's pinned range
          // (scene is ~190vh with a position:sticky child).
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
        }
      })
      .catch(() => {
        /* no manifest = leave the dark fallback (.sv-fb) showing */
      });

    window.addEventListener("resize", resize);
    return () => {
      disposed = true;
      trigger?.kill();
      tl?.kill();
      io?.disconnect();
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
