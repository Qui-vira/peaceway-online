"use client";

import {
  AnimatePresence,
  motion,
  useReducedMotion,
  type Variants,
  type Transition,
} from "framer-motion";
import {
  useEffect,
  useRef,
  useState,
  type CSSProperties,
  type ReactNode,
} from "react";

const EASE = [0.22, 0.61, 0.36, 1] as const;
const VIEWPORT = { once: true, margin: "-12% 0px -12% 0px" } as const;

/* ---------------------------------------------------------------------------
   Entrance effects for a whole block: fade / slide / scale / blur / clip.
--------------------------------------------------------------------------- */
export type BlockEffect =
  | "fade-in"
  | "fade-up"
  | "fade-down"
  | "slide-left"
  | "slide-right"
  | "slide-up"
  | "slide-down"
  | "blur"
  | "scale-up"
  | "scale-down"
  | "clip";

const BLOCK: Record<BlockEffect, Variants> = {
  "fade-in": { hidden: { opacity: 0 }, show: { opacity: 1 } },
  "fade-up": { hidden: { opacity: 0, y: 26 }, show: { opacity: 1, y: 0 } },
  "fade-down": { hidden: { opacity: 0, y: -26 }, show: { opacity: 1, y: 0 } },
  "slide-left": { hidden: { opacity: 0, x: -64 }, show: { opacity: 1, x: 0 } },
  "slide-right": { hidden: { opacity: 0, x: 64 }, show: { opacity: 1, x: 0 } },
  "slide-up": { hidden: { opacity: 0, y: 70 }, show: { opacity: 1, y: 0 } },
  "slide-down": { hidden: { opacity: 0, y: -70 }, show: { opacity: 1, y: 0 } },
  "blur": { hidden: { opacity: 0, filter: "blur(14px)" }, show: { opacity: 1, filter: "blur(0px)" } },
  "scale-up": { hidden: { opacity: 0, scale: 0.82 }, show: { opacity: 1, scale: 1 } },
  "scale-down": { hidden: { opacity: 0, scale: 1.18 }, show: { opacity: 1, scale: 1 } },
  "clip": { hidden: { clipPath: "inset(0 0 100% 0)", y: 14 }, show: { clipPath: "inset(0 0 0% 0)", y: 0 } },
};

type FXProps = {
  children: ReactNode;
  effect?: BlockEffect;
  className?: string;
  delay?: number;
  duration?: number;
  as?: "div" | "span" | "h2" | "h3" | "p";
  style?: CSSProperties;
};

/** Scroll-triggered block entrance. Static under reduced-motion. */
export function TextFX({
  children,
  effect = "fade-up",
  className,
  delay = 0,
  duration = 0.7,
  as = "div",
  style,
}: FXProps): JSX.Element {
  const reduce = useReducedMotion();
  const Comp = motion[as];
  if (reduce) {
    const Plain = as;
    return (
      <Plain className={className} style={style}>
        {children}
      </Plain>
    );
  }
  return (
    <Comp
      className={className}
      style={style}
      variants={BLOCK[effect]}
      initial="hidden"
      whileInView="show"
      viewport={VIEWPORT}
      transition={{ duration, ease: EASE, delay }}
    >
      {children}
    </Comp>
  );
}

/* ---------------------------------------------------------------------------
   Split reveals: letters / words / lines, plus typewriter and character-flip.
--------------------------------------------------------------------------- */
export type SplitEffect =
  | "letters"
  | "words"
  | "lines"
  | "typewriter"
  | "flip"
  | "mask-words";

const UNIT: Record<SplitEffect, Variants> = {
  letters: { hidden: { opacity: 0, y: 14 }, show: { opacity: 1, y: 0 } },
  words: { hidden: { opacity: 0, y: 22, filter: "blur(6px)" }, show: { opacity: 1, y: 0, filter: "blur(0px)" } },
  lines: { hidden: { opacity: 0, y: 30 }, show: { opacity: 1, y: 0 } },
  typewriter: { hidden: { opacity: 0 }, show: { opacity: 1 } },
  flip: { hidden: { opacity: 0, rotateX: -85 }, show: { opacity: 1, rotateX: 0 } },
  "mask-words": { hidden: { y: "110%" }, show: { y: "0%" } },
};

type SplitProps = {
  text: string;
  effect?: SplitEffect;
  className?: string;
  as?: "h1" | "h2" | "h3" | "p" | "span";
  delay?: number;
  stagger?: number;
  style?: CSSProperties;
};

/** Split a headline into letters/words/lines and stagger them into view. */
export function SplitText({
  text,
  effect = "words",
  className,
  as = "h2",
  delay = 0,
  stagger,
  style,
}: SplitProps): JSX.Element {
  const reduce = useReducedMotion();
  const Comp = motion[as];
  const perUnit = stagger ?? (effect === "letters" || effect === "typewriter" ? 0.03 : effect === "lines" ? 0.12 : 0.06);

  if (reduce) {
    const Plain = as;
    return (
      <Plain className={className} style={style}>
        {text}
      </Plain>
    );
  }

  const container: Variants = {
    hidden: {},
    show: { transition: { staggerChildren: perUnit, delayChildren: delay } },
  };
  const unitVariant = UNIT[effect];
  const dur = effect === "typewriter" ? 0.01 : effect === "flip" ? 0.5 : 0.6;
  const unitTransition: Transition = { duration: dur, ease: EASE };

  const units =
    effect === "lines"
      ? text.split("\n")
      : effect === "words" || effect === "mask-words"
      ? text.split(" ")
      : text.split("");

  return (
    <Comp
      className={className}
      style={{ ...style, perspective: effect === "flip" ? "700px" : undefined }}
      variants={container}
      initial="hidden"
      whileInView="show"
      viewport={VIEWPORT}
      aria-label={text}
    >
      {units.map((u, i) => {
        const content = effect === "letters" || effect === "typewriter" || effect === "flip" ? (u === " " ? " " : u) : u;
        // `lines` are blocks, so they need no inter-word margin.
        const spacing = effect === "words" || effect === "mask-words" ? "0.28em" : undefined;
        if (effect === "mask-words") {
          return (
            <span key={i} aria-hidden style={{ display: "inline-block", overflow: "hidden", marginRight: spacing, verticalAlign: "top" }}>
              <motion.span style={{ display: "inline-block" }} variants={unitVariant} transition={unitTransition}>
                {content}
              </motion.span>
            </span>
          );
        }
        return (
          <motion.span
            key={i}
            aria-hidden
            variants={unitVariant}
            transition={unitTransition}
            style={{
              /* A line is its own row. It used to be an inline-block that only
                 landed on a new row because the units together overflowed the
                 container - which also meant `white-space: pre` was needed to
                 hold each line together, and that made a line unbreakable. On a
                 phone a 576px line then sat in a 312px column and was simply
                 clipped at the edge. As a block it owns its row by construction
                 and wraps within itself when the column is narrow. */
              display: effect === "lines" ? "block" : "inline-block",
              marginRight: spacing,
              transformOrigin: effect === "flip" ? "50% 100%" : undefined,
              willChange: "transform, opacity",
              backfaceVisibility: "hidden",
            }}
          >
            {content}
          </motion.span>
        );
      })}
    </Comp>
  );
}

/* ---------------------------------------------------------------------------
   Rotating words: cycles a set of words in a fixed slot.
--------------------------------------------------------------------------- */
export function RotatingWords({
  words,
  className,
  interval = 2200,
}: {
  words: string[];
  className?: string;
  interval?: number;
}): JSX.Element {
  const reduce = useReducedMotion();
  const [i, setI] = useState(0);
  useEffect(() => {
    if (reduce) return;
    const id = window.setInterval(() => setI((v) => (v + 1) % words.length), interval);
    return () => window.clearInterval(id);
  }, [reduce, words.length, interval]);

  const longest = words.reduce((a, b) => (b.length > a.length ? b : a), "");
  if (reduce) return <span className={className}>{words[0]}</span>;
  return (
    <span style={{ position: "relative", display: "inline-block", verticalAlign: "bottom", textAlign: "center" }}>
      {/* invisible longest word reserves the slot width so nothing shifts */}
      <span aria-hidden style={{ visibility: "hidden" }} className={className}>
        {longest}
      </span>
      <AnimatePresence mode="wait" initial={false}>
        <motion.span
          key={words[i]}
          className={className}
          style={{ position: "absolute", left: 0, right: 0, display: "inline-block", whiteSpace: "nowrap", willChange: "transform, opacity" }}
          initial={{ y: "0.55em", opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          exit={{ y: "-0.55em", opacity: 0 }}
          transition={{ duration: 0.42, ease: EASE }}
        >
          {words[i]}
        </motion.span>
      </AnimatePresence>
    </span>
  );
}

/* ---------------------------------------------------------------------------
   Text scramble: characters shuffle then settle to the final text on view.
--------------------------------------------------------------------------- */
const GLYPHS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ#%&*+=/";
export function ScrambleText({ text, className }: { text: string; className?: string }): JSX.Element {
  const reduce = useReducedMotion();
  const ref = useRef<HTMLSpanElement>(null);
  const [display, setDisplay] = useState(reduce ? text : "");

  useEffect(() => {
    if (reduce) return;
    const el = ref.current;
    if (!el) return;
    let raf = 0;
    let started = false;
    const run = (): void => {
      let frame = 0;
      const total = 28;
      const tick = (): void => {
        const revealed = Math.floor((frame / total) * text.length);
        let out = "";
        for (let k = 0; k < text.length; k++) {
          out += k < revealed || text[k] === " " ? text[k] : GLYPHS[Math.floor(Math.random() * GLYPHS.length)];
        }
        setDisplay(out);
        frame++;
        if (frame <= total) raf = window.requestAnimationFrame(tick);
        else setDisplay(text);
      };
      tick();
    };
    const io = new IntersectionObserver((entries) => {
      entries.forEach((e) => {
        if (e.isIntersecting && !started) {
          started = true;
          run();
        }
      });
    }, { threshold: 0.4 });
    io.observe(el);
    return () => {
      io.disconnect();
      if (raf) window.cancelAnimationFrame(raf);
    };
  }, [text, reduce]);

  return (
    <span ref={ref} className={className} aria-label={text}>
      <span aria-hidden>{display || " "}</span>
    </span>
  );
}

/* ---------------------------------------------------------------------------
   Marquee: seamless horizontal scroll of its children.
--------------------------------------------------------------------------- */
export function Marquee({
  children,
  className,
  speed = 32,
  reverse = false,
}: {
  children: ReactNode;
  className?: string;
  speed?: number;
  reverse?: boolean;
}): JSX.Element {
  const reduce = useReducedMotion();
  if (reduce) {
    return <div className={className} style={{ overflow: "hidden", whiteSpace: "nowrap" }}>{children}</div>;
  }
  return (
    <div className={className} style={{ overflow: "hidden", display: "flex", maskImage: "linear-gradient(90deg, transparent, #000 8%, #000 92%, transparent)" }}>
      <motion.div
        style={{ display: "flex", flexShrink: 0, gap: "3rem", paddingRight: "3rem", whiteSpace: "nowrap" }}
        animate={{ x: reverse ? ["-50%", "0%"] : ["0%", "-50%"] }}
        transition={{ duration: speed, ease: "linear", repeat: Infinity }}
      >
        {children}
        {children}
      </motion.div>
    </div>
  );
}

/* ---------------------------------------------------------------------------
   Magnetic hover text: gently follows the cursor, springs back on leave.
--------------------------------------------------------------------------- */
export function MagneticText({
  children,
  className,
  strength = 0.35,
}: {
  children: ReactNode;
  className?: string;
  strength?: number;
}): JSX.Element {
  const reduce = useReducedMotion();
  const ref = useRef<HTMLSpanElement>(null);
  const [pos, setPos] = useState({ x: 0, y: 0 });
  if (reduce) return <span className={className}>{children}</span>;
  return (
    <motion.span
      ref={ref}
      className={className}
      style={{ display: "inline-block" }}
      animate={{ x: pos.x, y: pos.y }}
      transition={{ type: "spring", stiffness: 220, damping: 14 }}
      onPointerMove={(e) => {
        const el = ref.current;
        if (!el) return;
        const r = el.getBoundingClientRect();
        setPos({ x: (e.clientX - (r.left + r.width / 2)) * strength, y: (e.clientY - (r.top + r.height / 2)) * strength });
      }}
      onPointerLeave={() => setPos({ x: 0, y: 0 })}
    >
      {children}
    </motion.span>
  );
}
