"use client";

import { useEffect, useRef } from "react";
import { heroActions, sectionCopy } from "@/lib/constants";
import { media } from "@/lib/media";
import { VideoBackground } from "@/components/ui/video-background";
import { usePrefersReducedMotion } from "@/lib/motion";

export function HeroSection(): JSX.Element {
  const shouldReduceMotion = usePrefersReducedMotion();
  const sectionRef = useRef<HTMLElement | null>(null);
  const videoRef = useRef<HTMLVideoElement | null>(null);

  useEffect(() => {
    const video = videoRef.current;
    if (!video) {
      return;
    }

    const onLoadedMetadata = () => {
      if (shouldReduceMotion) {
        video.pause();
        video.currentTime = 0;
        return;
      }

      void video.play().catch(() => undefined);
    };

    const onCanPlay = () => {
      if (!shouldReduceMotion) {
        void video.play().catch(() => undefined);
      }
    };

    video.addEventListener("loadedmetadata", onLoadedMetadata);
    video.addEventListener("canplay", onCanPlay);

    return () => {
      video.removeEventListener("loadedmetadata", onLoadedMetadata);
      video.removeEventListener("canplay", onCanPlay);
    };
  }, [shouldReduceMotion]);

  return (
    <section ref={sectionRef} id="hero" className="relative overflow-hidden">
      <div className="relative min-h-[190vh] overflow-hidden">
        <VideoBackground ref={videoRef} src={media.heroVideo} poster={media.heroPoster} priority active={!shouldReduceMotion} />
        <div className="absolute inset-0 bg-[linear-gradient(to_bottom,rgba(7,8,6,0.74)_0%,rgba(7,8,6,0.42)_22%,rgba(7,8,6,0.2)_58%,rgba(7,8,6,0.9)_100%)]" />
        <div className="mx-auto flex h-screen max-w-[1240px] flex-col justify-center px-5 pt-[88px] pb-6 md:px-14">
          <div className="relative z-10">
            <p
              className="mb-[20px] text-[12px] font-semibold uppercase tracking-[0.2em] text-[#4ADE80]"
              style={{ textShadow: "0 0 20px rgba(15,103,60,.5)" }}
            >
              {sectionCopy.hero.eyebrow}
            </p>
            <h1
              className="section-title mb-[22px] max-w-[760px] bg-gradient-to-b from-[#DCDDDB] via-[#A5C8B3] to-[#5A9E70] bg-clip-text text-[clamp(38px,11vw,64px)] font-extrabold uppercase leading-[0.96] tracking-[-0.028em] text-transparent md:text-[clamp(36px,5.5vw,76px)]"
            >
              {sectionCopy.hero.title}
            </h1>
            <p
              className="mb-[38px] max-w-[460px] text-[clamp(15px,1.5vw,19px)] leading-[1.75] text-[#B1BDB0]"
            >
              {sectionCopy.hero.description}
            </p>
            <div className="flex flex-wrap gap-4">
              {heroActions.map((action) => (
                <a
                  key={action.label}
                  href={action.href}
                  target="_blank"
                  rel="noreferrer noopener"
                  data-hoverable="true"
                  className={
                    action.variant === "primary"
                      ? "inline-flex items-center justify-center rounded-[32px] bg-g px-8 py-3.5 text-[14px] font-semibold uppercase tracking-[0.06em] text-white transition hover:bg-g2"
                      : "inline-flex items-center justify-center rounded-[32px] border border-[#DCDDDB]/35 px-8 py-3.5 text-[14px] uppercase tracking-[0.06em] text-[#DCDDDB] transition hover:border-[#DCDDDB] hover:bg-[#DCDDDB]/10"
                  }
                >
                  {action.label}
                </a>
              ))}
            </div>
          </div>
        </div>
        <div className="absolute bottom-9 left-5 z-20 md:left-14">
          <div className="flex items-center gap-3">
            <div className="relative h-[1px] w-11 overflow-hidden bg-[rgba(15,103,60,.35)]">
              <div className="absolute inset-0 animate-[scanLine_2.5s_ease-in-out_infinite] bg-g" />
            </div>
            <span className="text-[9.5px] uppercase tracking-[0.2em] text-[rgba(177,189,176,.38)]">
              Scroll to reveal
            </span>
          </div>
        </div>
      </div>
    </section>
  );
}
