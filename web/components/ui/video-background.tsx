"use client";

import { forwardRef } from "react";

type VideoBackgroundProps = {
  src: string;
  poster?: string;
  className?: string;
  priority?: boolean;
  active?: boolean;
};

export const VideoBackground = forwardRef<HTMLVideoElement, VideoBackgroundProps>(function VideoBackground(
  { src, poster, className = "", priority = false, active = true },
  ref
): JSX.Element {
  const shouldLoad = active;

  return (
    <div className={`absolute inset-0 overflow-hidden ${className}`} aria-hidden="true">
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_50%_100%,rgba(15,103,60,0.16)_0%,rgba(9,10,7,1)_72%)]" />
      {poster ? (
        <div
          className="absolute inset-0 bg-cover bg-center opacity-100"
          style={{ backgroundImage: `url(${poster})` }}
        />
      ) : null}
      <video
        ref={ref}
        className="absolute inset-0 h-full w-full object-cover brightness-[0.48] contrast-110 saturate-[0.7]"
        autoPlay
        muted
        loop
        playsInline
        preload={priority && active ? "auto" : active ? "metadata" : "none"}
        poster={poster}
        disablePictureInPicture
      >
        {shouldLoad ? <source src={src} type="video/mp4" /> : null}
      </video>
      <div className="absolute inset-0 bg-[linear-gradient(to_bottom,rgba(7,8,6,0.72)_0%,rgba(7,8,6,0.35)_22%,rgba(7,8,6,0.18)_54%,rgba(7,8,6,0.92)_100%)]" />
      <div
        className="absolute inset-0 bg-[radial-gradient(circle_at_50%_50%,transparent_34%,rgba(7,8,6,0.72)_100%)] opacity-90"
      />
    </div>
  );
});
