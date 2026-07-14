/**
 * Scroll-linked hero audio engine (singleton).
 *
 * Synthesises the building's assemble/explode sound with the Web Audio API:
 * a filtered-noise "whoosh" whose loudness + brightness track scroll velocity,
 * plus a low rumble that swells through the middle of the explosion. Off by
 * default and only started on an explicit user gesture (browser autoplay
 * policy + good manners). ScrollSequence feeds it progress/velocity each frame.
 */
type WebkitWindow = Window & { webkitAudioContext?: typeof AudioContext };

class HeroSound {
  private ctx: AudioContext | null = null;
  private master: GainNode | null = null;
  private noiseGain: GainNode | null = null;
  private filter: BiquadFilterNode | null = null;
  private rumbleGain: GainNode | null = null;
  private started = false;
  private enabled = false;
  private listeners = new Set<(on: boolean) => void>();

  isEnabled(): boolean {
    return this.enabled;
  }

  /** Read the persisted preference (call on mount). Never auto-enables audio. */
  hydrate(): boolean {
    try {
      this.enabled = window.localStorage.getItem("pw-hero-sound") === "1";
    } catch {
      this.enabled = false;
    }
    return this.enabled;
  }

  subscribe(fn: (on: boolean) => void): () => void {
    this.listeners.add(fn);
    return () => this.listeners.delete(fn);
  }

  /** If enabled from a prior session, unlock + start audio on the first gesture. */
  arm(): void {
    if (!this.enabled || this.started || typeof window === "undefined") return;
    const go = (): void => {
      this.start();
      if (this.ctx && this.master) this.master.gain.setTargetAtTime(0.85, this.ctx.currentTime, 0.06);
      window.removeEventListener("pointerdown", go);
      window.removeEventListener("keydown", go);
    };
    window.addEventListener("pointerdown", go, { once: true });
    window.addEventListener("keydown", go, { once: true });
  }

  /** Must be called from a user gesture (click) to satisfy autoplay policy. */
  toggle(): boolean {
    this.enabled = !this.enabled;
    if (this.enabled) this.start();
    if (this.ctx && this.master) {
      this.master.gain.setTargetAtTime(this.enabled ? 0.85 : 0, this.ctx.currentTime, 0.06);
    }
    try {
      window.localStorage.setItem("pw-hero-sound", this.enabled ? "1" : "0");
    } catch {
      /* ignore */
    }
    this.listeners.forEach((fn) => fn(this.enabled));
    return this.enabled;
  }

  private start(): void {
    if (this.started) {
      void this.ctx?.resume();
      return;
    }
    const Ctx = window.AudioContext || (window as WebkitWindow).webkitAudioContext;
    if (!Ctx) return;
    const ctx = new Ctx();

    // looping white-noise source for the whoosh
    const buffer = ctx.createBuffer(1, ctx.sampleRate * 2, ctx.sampleRate);
    const data = buffer.getChannelData(0);
    for (let i = 0; i < data.length; i++) data[i] = Math.random() * 2 - 1;
    const noise = ctx.createBufferSource();
    noise.buffer = buffer;
    noise.loop = true;

    const filter = ctx.createBiquadFilter();
    filter.type = "lowpass";
    filter.frequency.value = 320;
    filter.Q.value = 0.8;

    const noiseGain = ctx.createGain();
    noiseGain.gain.value = 0;

    const rumble = ctx.createOscillator();
    rumble.type = "sine";
    rumble.frequency.value = 46;
    const rumbleGain = ctx.createGain();
    rumbleGain.gain.value = 0;

    const master = ctx.createGain();
    master.gain.value = 0;

    noise.connect(filter).connect(noiseGain).connect(master);
    rumble.connect(rumbleGain).connect(master);
    master.connect(ctx.destination);
    noise.start();
    rumble.start();

    this.ctx = ctx;
    this.filter = filter;
    this.noiseGain = noiseGain;
    this.rumbleGain = rumbleGain;
    this.master = master;
    this.started = true;
  }

  /**
   * Drive the sound from the scroll. progress 0..1 across the explosion,
   * velocity = |Δprogress| since the last frame.
   */
  update(progress: number, velocity: number): void {
    if (!this.enabled || !this.ctx || !this.noiseGain || !this.filter || !this.rumbleGain) return;
    const t = this.ctx.currentTime;
    const v = Math.min(1, velocity * 55);
    // whoosh: louder + brighter the faster you scrub
    this.noiseGain.gain.setTargetAtTime(v * 0.5, t, 0.05);
    this.filter.frequency.setTargetAtTime(280 + v * 2400, t, 0.05);
    // rumble: bell curve through the middle of the explosion, boosted by motion
    const bell = Math.sin(Math.max(0, Math.min(1, progress)) * Math.PI);
    this.rumbleGain.gain.setTargetAtTime(bell * (0.12 + v * 0.4), t, 0.09);
  }
}

export const heroSound = new HeroSound();
