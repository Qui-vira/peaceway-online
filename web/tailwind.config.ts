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
      // The codebase reaches for /12 in 31 places (bg-emerald-500/12 icon chips,
      // border-white/12, the nav's active pill). 12 is not in Tailwind's default
      // opacity scale (0,5,10,20,25,...), so every one of those utilities was
      // silently dropped at build and painted nothing - the icon tint squares
      // behind the dashboard icons have never existed. Adding the step is a
      // one-line fix that honours what the author wrote, rather than rewriting
      // 31 call sites to /10.
      opacity: {
        12: "0.12"
      },
      fontFamily: {
        display: ["var(--font-syne)", "sans-serif"],
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
