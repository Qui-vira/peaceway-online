"use client";

import { useEffect, useState } from "react";
import { Volume2, VolumeX } from "lucide-react";
import { heroSound } from "@/lib/hero-sound";

/** Opt-in toggle for the scroll-linked hero sound (off by default). */
export function HeroSoundToggle(): JSX.Element {
  const [on, setOn] = useState(false);

  useEffect(() => {
    setOn(heroSound.hydrate());
    heroSound.arm();
    return heroSound.subscribe(setOn);
  }, []);

  return (
    <button
      type="button"
      onClick={() => heroSound.toggle()}
      aria-pressed={on}
      aria-label={on ? "Mute hero sound" : "Enable hero sound"}
      className={`pw-sound-toggle${on ? " is-on" : ""}`}
    >
      {on ? <Volume2 size={14} strokeWidth={2} /> : <VolumeX size={14} strokeWidth={2} />}
      <span>{on ? "Sound on" : "Sound"}</span>
    </button>
  );
}
