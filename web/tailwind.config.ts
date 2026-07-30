import type { Config } from "tailwindcss";

const config: Config = {
  future: {
    // hover: variants only apply on devices with a real pointer - prevents
    // sticky hover states on touch screens
    hoverOnlyWhenSupported: true
  },
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./lib/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        bgd: "var(--bgd)",
        bg: "var(--bg)",
        t: "var(--t)",
        m: "var(--m)",
        g: "var(--g)",
        g2: "var(--g2)",
        r: "var(--r)",
        // Harmonize the web-app accent (used everywhere as `emerald-*`) to the
        // Peaceway brand greens so the app matches the marketing landing.
        emerald: {
          100: "#d7f7e5",
          200: "#b7f3d0",
          300: "#74e2a6",
          400: "#34d98a",
          500: "#1aa35a",
          600: "#14803f",
          700: "#0f673c",
          800: "#0b4f2f",
          900: "#083b24"
        },
        // Same treatment as emerald, and for the same reason. Every error,
        // destructive action and alert in the product used stock Tailwind red -
        // 121 call sites - while the brand's own cross-red #a80b16 appeared in
        // exactly one file, `app/dispatch/page.tsx`, which nothing links to.
        //
        // The ramp is built around #a80b16 (hue 356) rather than replacing every
        // step with it: #a80b16 is a 35%-lightness red and fails badly as text
        // on #0b0c09. So the brand hex anchors 600, the fills sit at 500, and
        // the text steps stay light enough to pass AA on the dark base
        // (400 = #f26b76 -> 6.7:1). Call sites do not change; what they resolve
        // to does.
        red: {
          100: "#fde7e9",
          200: "#fbc9cd",
          300: "#f79aa2",
          400: "#f26b76",
          500: "#d4212f",
          600: "#a80b16",
          700: "#85101a",
          800: "#5f0d14",
          900: "#3d0a0e"
        }
      },
      // Tailwind's opacity scale runs in steps of 5 (0,5,10,15,...,100). Every
      // other step this codebase reaches for was silently dropped at build:
      // the utility never compiled, so it painted nothing.
      //
      // /8 is the worst of them, and it is why bright lines appeared across the
      // app. DESIGN.md defines Hairline as rgba(255,255,255,0.08) - "Borders and
      // dividers. Structure by implication." - which is `border-white/8`, used
      // in 71 places. It has never once rendered. Worse than invisible: `border-t`
      // still sets a 1px solid border, so the *colour* fell through to Tailwind
      // preflight's default of gray-200, painting a near-white rule across a
      // near-black page - under every back bar and above every footer.
      //
      // /3, /4 and /6 are dead the same way, mostly as faint card fills.
      //
      // Adding the steps honours what the author and DESIGN.md both already
      // specified, rather than rewriting 100+ call sites to approximations.
      opacity: {
        3: "0.03",
        4: "0.04",
        6: "0.06",
        8: "0.08",
        12: "0.12"
      },
      fontFamily: {
        syne: ["var(--font-syne)", "sans-serif"],
        sans: ["var(--font-dm-sans)", "sans-serif"]
      },
      boxShadow: {
        glow: "0 0 0 1px rgba(15,103,60,.25), 0 18px 60px rgba(0,0,0,.35)"
      }
    }
  },
  plugins: []
};

export default config;
