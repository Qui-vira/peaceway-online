"use client";

import { useCallback, useEffect, useRef, useState } from "react";

/**
 * App-open loader.
 *
 * Plays the commissioned Peaceway logo animation full-screen, once, then
 * resolves into the app.
 *
 * The important structural decision: this renders on the SERVER. It is in the
 * SSR HTML, so it is painted in the very first frame the browser produces, on
 * top of a page that has already rendered behind it. An earlier version mounted
 * only from an effect, which meant the app appeared first and the loader dropped
 * on top of it a moment later - visible in a screen recording as a flash of the
 * real page before the brand moment, which is exactly backwards.
 *
 * That choice costs something, and it is paid for explicitly:
 *
 *   - No JS at all? A CSS-only backstop animation fades the overlay out and
 *     makes it non-interactive. `.js-ready` cancels that the instant React takes
 *     over, so the two never fight. The overlay can never strand a visitor.
 *   - Returning visitor in the same session? A blocking inline script in <head>
 *     (see app/layout.tsx) reads sessionStorage and adds `pw-loader-skip` to
 *     <html> BEFORE first paint, so they never see a frame of it. That has to be
 *     pre-paint and pre-React, which is why it is a raw script tag and not this
 *     component's job.
 *   - Hydration? Server and client both render the overlay unconditionally, so
 *     the markup matches. Nothing in the first render depends on client state.
 *
 * The user is never trapped. Five independent exits: the video ending, a hard
 * cap, a stall watchdog, a tap or Escape, and the CSS backstop if scripting is
 * gone entirely.
 */

/**
 * When the loader runs. One edit to change it.
 *
 *   "every-app-open"           every full page load. THE DEFAULT.
 *   "first-visit-per-session"  once per tab session; later loads skip it.
 *
 * Neither replays on client-side route changes: this lives in the root layout,
 * which survives navigation and simply never re-mounts. So "every app open"
 * already means what it sounds like - opening or reloading the app, not tapping
 * around inside it.
 *
 * Why the default is not the per-session gate, despite that being the tighter
 * behaviour: a gate that hides the loader for the rest of the session cannot be
 * distinguished, by the person looking at it, from the loader being broken. It
 * hid itself twice during this build and read as "the animation is gone" both
 * times. A brand moment you cannot reliably see is worse than one you see a
 * little too often, and the native app this was modelled on plays on every
 * launch too.
 *
 * The one real cost: crossing between the marketing site and the app is a full
 * document load, so it plays again. If that becomes annoying in real use, flip
 * this to the session gate - the machinery is all still here and tested.
 */
const LOADER_SCOPE: "every-app-open" | "first-visit-per-session" =
  "every-app-open";

/** Must match the key read by the inline script in app/layout.tsx. */
const SESSION_KEY = "pw-loader-seen";

/** Encoded length of the video, trimmed from 7.04s (2.17s of it was a static hold). */
const LOADER_VIDEO_MS = 5000;

/** Hard ceiling. 1s of headroom over the video, then a firm stop. */
const LOADER_CAP_MS = 6000;

/** If playback has not advanced for this long, treat it as stalled and leave. */
const STALL_TIMEOUT_MS = 1500;

/** The final fade. Short: it is dead time on top of the animation. */
const FADE_MS = 240;

/** The logo's travel to its resting position. Matches --pw-loader-handoff. */
const HANDOFF_MS = 480;

/**
 * Where the finished lockup sits inside the delivered video, as fractions of the
 * frame. The source was 1920x1080 using only the middle 50% of its width; the
 * shipped video is cropped to 1080x990 around the content's true extent across
 * the whole 5s. Measured on that cropped frame.
 */
const LOCKUP = { x0: 0.0556, x1: 0.9481, y0: 0.0657, y1: 0.7091 };

/** Fallback intrinsic size, used before the video reports its own. */
const LOADER_INTRINSIC = { w: 1080, h: 990 };

/** The app's own header logo: the destination of the handoff, when one exists. */
const APP_LOGO_SELECTOR = 'img.nlogo, img[alt="Peaceway Pharmacy"]';

const MARK_SRC = "/branding/loader/peaceway-loader-mark.webp";

type Phase = "playing" | "handoff" | "leaving" | "idle";

export function AppLoader(): JSX.Element | null {
  // Starts "playing" on both server and client so the overlay is in the first
  // painted frame. See the note above about why this is not effect-mounted.
  const [phase, setPhase] = useState<Phase>("playing");
  const [jsReady, setJsReady] = useState(false);
  const [failed, setFailed] = useState(false);
  const [travel, setTravel] = useState<string | null>(null);

  const travelRef = useRef<string | null>(null);
  const markRect = useRef<{
    left: number;
    top: number;
    width: number;
    height: number;
  } | null>(null);
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const timers = useRef<number[]>([]);
  const lastTime = useRef(0);

  const clearTimers = useCallback(() => {
    timers.current.forEach((t) => window.clearTimeout(t));
    timers.current = [];
  }, []);

  /** Straight out. Skips, stalls, failures, reduced motion, and the cap. */
  const dismiss = useCallback(() => {
    clearTimers();
    setPhase((p) => (p === "idle" ? p : "leaving"));
    timers.current.push(window.setTimeout(() => setPhase("idle"), FADE_MS));
  }, [clearTimers]);

  /**
   * The graceful exit, when the animation actually finishes.
   *
   * Carries the lockup from where the video drew it to where the app's own
   * header logo sits. Everything is measured at runtime, so it is right at any
   * viewport. Routes without a header logo have nothing to hand off to, so they
   * take the plain fade rather than being given an invented destination.
   */
  const handoff = useCallback(() => {
    clearTimers();

    const media = videoRef.current;
    const target = document.querySelector(APP_LOGO_SELECTOR);
    const prefersReduced = window.matchMedia(
      "(prefers-reduced-motion: reduce)"
    ).matches;

    if (!media || !target || prefersReduced) {
      setPhase("handoff");
      timers.current.push(window.setTimeout(() => dismiss(), 160));
      return;
    }

    const box = media.getBoundingClientRect();
    const dest = target.getBoundingClientRect();

    // Solve the contain-fit, then locate the lockup inside it. Intrinsic size is
    // read off the element: it was once hard-coded to the pre-crop 1920x1080 and
    // silently produced a mark 61% of its correct height.
    const natW = media.videoWidth || LOADER_INTRINSIC.w;
    const natH = media.videoHeight || LOADER_INTRINSIC.h;
    const fit = Math.min(box.width / natW, box.height / natH);
    const contentW = natW * fit;
    const contentH = natH * fit;
    const contentX = box.x + (box.width - contentW) / 2;
    const contentY = box.y + (box.height - contentH) / 2;

    const lockW = (LOCKUP.x1 - LOCKUP.x0) * contentW;
    const lockH = (LOCKUP.y1 - LOCKUP.y0) * contentH;
    const lockCx = contentX + ((LOCKUP.x0 + LOCKUP.x1) / 2) * contentW;
    const lockCy = contentY + ((LOCKUP.y0 + LOCKUP.y1) / 2) * contentH;

    markRect.current = {
      left: lockCx - lockW / 2,
      top: lockCy - lockH / 2,
      width: lockW,
      height: lockH,
    };

    const s = dest.width / lockW;
    travelRef.current =
      `translate(${(dest.x + dest.width / 2 - lockCx).toFixed(1)}px, ` +
      `${(dest.y + dest.height / 2 - lockCy).toFixed(1)}px) scale(${s.toFixed(4)})`;

    setTravel(null);
    setPhase("handoff");
    timers.current.push(window.setTimeout(() => dismiss(), HANDOFF_MS));
  }, [clearTimers, dismiss]);

  // Take over from the CSS backstop, honour the session gate, arm the cap.
  useEffect(() => {
    setJsReady(true);

    let seen = false;
    try {
      seen = window.sessionStorage.getItem(SESSION_KEY) === "1";
      window.sessionStorage.setItem(SESSION_KEY, "1");
    } catch {
      // Storage blocked. Showing the loader more often than intended is a
      // nuisance; failing to show the app is a bug. Fall through and play.
    }

    if (LOADER_SCOPE === "first-visit-per-session" && seen) {
      // The inline script has already hidden it pre-paint; drop it entirely.
      setPhase("idle");
      return;
    }

    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      timers.current.push(window.setTimeout(() => dismiss(), 320));
      return;
    }

    // Decode the handoff cut-out now, while the video plays, so the swap at the
    // end is instant. Undecoded, the travel could start on an unpainted image
    // and read as the logo simply vanishing.
    const pre = new window.Image();
    pre.src = MARK_SRC;
    if (typeof pre.decode === "function") pre.decode().catch(() => {});

    timers.current.push(window.setTimeout(() => dismiss(), LOADER_CAP_MS));
    return clearTimers;
  }, [dismiss, clearTimers]);

  // Apply the travel one frame after the cut-out mounts, so there is a starting
  // value to animate away from.
  useEffect(() => {
    if (phase !== "handoff" || !travelRef.current || travel) return;
    const id = requestAnimationFrame(() => setTravel(travelRef.current));
    return () => cancelAnimationFrame(id);
  }, [phase, travel]);

  const armStallWatchdog = useCallback(() => {
    timers.current.push(
      window.setTimeout(() => {
        const v = videoRef.current;
        if (!v) return;
        if (v.currentTime <= lastTime.current + 0.01 && !v.ended) dismiss();
      }, STALL_TIMEOUT_MS)
    );
  }, [dismiss]);

  useEffect(() => {
    if (phase === "idle") return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") dismiss();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [phase, dismiss]);

  // Lock scroll only while the overlay is up.
  useEffect(() => {
    if (phase === "idle") return;
    const previous = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = previous;
    };
  }, [phase]);

  useEffect(() => clearTimers, [clearTimers]);

  if (phase === "idle") return null;

  const travelling =
    (phase === "handoff" || phase === "leaving") &&
    travelRef.current !== null &&
    markRect.current !== null;

  return (
    <div
      className={[
        "pw-loader",
        jsReady ? "js-ready" : "",
        phase === "handoff" || phase === "leaving" ? "is-handoff" : "",
        phase === "leaving" ? "is-leaving" : "",
      ]
        .filter(Boolean)
        .join(" ")}
      role="status"
      aria-label="Peaceway Pharmacy"
      onClick={dismiss}
    >
      {/* Rendered on the server, so it is in the first painted frame. `poster` is
          the finished lockup, so a decode failure leaves a logo on screen rather
          than a blank rectangle. */}
      {!failed && !travelling ? (
        <video
          ref={videoRef}
          className="pw-loader-media"
          /* All three are needed together: without `muted` autoplay is refused,
             and without `playsInline` iOS Safari takes the video fullscreen
             instead of playing it in place. The source has no audio track. */
          autoPlay
          muted
          playsInline
          preload="auto"
          poster="/branding/loader/peaceway-loader-poster.webp"
          aria-hidden="true"
          onEnded={handoff}
          onError={() => setFailed(true)}
          onTimeUpdate={() => {
            const v = videoRef.current;
            if (!v) return;
            lastTime.current = v.currentTime;
            armStallWatchdog();
          }}
        >
          <source src="/branding/loader/peaceway-loader.webm" type="video/webm" />
          <source src="/branding/loader/peaceway-loader.mp4" type="video/mp4" />
        </video>
      ) : null}

      {/* The never-blank path: a decode failure lands on the finished lockup. */}
      {failed && !travelling ? (
        /* eslint-disable-next-line @next/next/no-img-element */
        <img
          className="pw-loader-media"
          src="/branding/loader/peaceway-loader-poster.webp"
          alt=""
          aria-hidden="true"
        />
      ) : null}

      {/* The transparent cut-out, laid exactly over the lockup's last drawn
          position so the swap is imperceptible, then travelling to the app's own
          logo. `leaving` is in the condition on purpose: without it React falls
          back to the <video> branch the moment the fade starts, remounting the
          video and snapping the logo to full size at the worst instant. */}
      {travelling ? (
        /* eslint-disable-next-line @next/next/no-img-element */
        <img
          className="pw-loader-mark is-travelling"
          src={MARK_SRC}
          alt=""
          aria-hidden="true"
          style={{
            left: `${markRect.current!.left}px`,
            top: `${markRect.current!.top}px`,
            width: `${markRect.current!.width}px`,
            height: `${markRect.current!.height}px`,
            transform: travel ?? "none",
          }}
        />
      ) : null}
    </div>
  );
}

export { LOADER_SCOPE, LOADER_CAP_MS, LOADER_VIDEO_MS, SESSION_KEY };
