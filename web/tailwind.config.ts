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
