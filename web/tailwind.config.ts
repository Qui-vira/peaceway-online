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
        r: "var(--r)"
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
