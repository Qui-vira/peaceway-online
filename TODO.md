# TODO — Peaceway Online Website (Phase 1)

Current phase: **Phase 1 — Marketing website**  
Target: Vercel deployment of `web/` subfolder

---

## Setup

- [ ] Create `web/` directory with Next.js 14 App Router + TypeScript
- [ ] Install dependencies: `next`, `react`, `react-dom`, `typescript`, `tailwindcss`, `framer-motion`, `gsap`, `@gsap/react`
- [ ] Configure `tailwind.config.ts` with design tokens (colors, fonts, breakpoints)
- [ ] Configure `next.config.ts` (video headers, image domains)
- [ ] Add `web/vercel.json`
- [ ] Copy video assets to `web/public/videos/`
- [ ] Copy image/logo assets to `web/public/images/`

## Design tokens (from design handoff)

- [ ] Define CSS variables in `globals.css`: `--g: #0F673C`, `--g2: #1A8A50`, `--r: #A80B16`, `--bg: #191A17`, `--bgd: #0B0C09`, `--t: #DCDDDB`, `--m: #B1BDB0`
- [ ] Configure Syne font (700, 800) via `next/font/google`
- [ ] Configure DM Sans font (300, 400, 500, 600) via `next/font/google`

## Global UI components

- [ ] `CustomCursor` — green dot + ring, hover enlarge, desktop only
- [ ] `GrainOverlay` — `body::before` grain noise animation
- [ ] `ScrollProgressBar` — left-edge vertical bar
- [ ] `Navbar` — fixed, scrolled glass state, links, CTA button
- [ ] `VideoBackground` — reusable wrapper (poster, lazy play/pause, muted, playsInline)

## Section components

- [ ] `HeroSection` (S1) — GSAP ScrollTrigger video scrub, staggered text reveals
- [ ] `ProblemSection` (S2) — 3-column glass cards, tilt, red accent icons
- [ ] `ServicesSection` (S3) — 6-column glass cards, green accent icons, tilt
- [ ] `TrustSection` (S4) — 2-col layout, pharmacy photo, trust item list, PCN placeholder
- [ ] `HowItWorksSection` (S5) — 2-column 10-step grid, numbered circles
- [ ] `PharmacistSection` (S6) — 2-col layout, chat bubble mockup, CTA
- [ ] `DeliverySection` (S7) — area badges (primary/secondary), SVG map, animated ping
- [ ] `CommunitySection` (S8) — centered, 2 Telegram cards
- [ ] `ContactSection` (S9) — 2-col layout, contact card with icons
- [ ] `Footer` — 4-column grid, logo, social icons, legal disclaimer

## Motion and interaction

- [ ] Parallax depth on section number watermarks (`data-depth` in design → Framer Motion `useScroll`)
- [ ] Scroll reveal: Framer Motion `whileInView` on all `[data-r]` elements with stagger
- [ ] Card tilt: mouse-tracking 3D tilt on glass cards (Framer Motion `useMotionValue`)
- [ ] Hero GSAP ScrollTrigger video scrubbing (`currentTime` driven by scroll progress)
- [ ] IntersectionObserver play/pause for non-hero video backgrounds
- [ ] Scan line animation on scroll indicator
- [ ] Navbar background transition on scroll
- [ ] Reduced motion: `useReducedMotion()` hook — skip all animations, show static state

## PWA

- [ ] `web/public/manifest.json`
- [ ] `web/public/sw.js` (offline shell cache)
- [ ] Icons: `icon-192.png`, `icon-512.png` (generated from logo)
- [ ] Apple mobile web app meta tags in `<head>`
- [ ] `theme-color` meta tag

## SEO

- [ ] `metadata` export in `app/layout.tsx` (title, description, OG tags)
- [ ] `web/public/sitemap.xml`
- [ ] `web/public/robots.txt`
- [ ] Semantic HTML throughout

## Testing checklist before deploy

- [ ] Desktop Chrome: all sections render, videos autoplay, cursor works
- [ ] Mobile Safari (375px): videos play inline, custom cursor hidden, layout responsive
- [ ] Android Chrome (390px): PWA install prompt, videos autoplay muted
- [ ] `prefers-reduced-motion`: animations disabled, static fallbacks visible
- [ ] All external links open in new tab with `rel="noopener"`
- [ ] No console errors
- [ ] Lighthouse score: Performance ≥ 80, Accessibility ≥ 90

## Vercel deploy

- [ ] `vercel link` from `web/` directory (verify project name first)
- [ ] Set environment variables on Vercel dashboard (none needed for Phase 1)
- [ ] `vercel --prod` from `web/`
- [ ] Verify site loads at domain
- [ ] Verify video assets load (check network tab)

---

## Phase 2 (after user provides details)

- [ ] Replace WhatsApp placeholder with real number
- [ ] Replace Facebook placeholder with real link
- [ ] Replace PCN placeholder with real registration number
- [ ] Update Telegram channel link if changed

## Phase 3 (future — web customer features)

- [ ] Customer order request flow
- [ ] Product availability check
- [ ] Ask pharmacist form
- [ ] Prescription upload
- [ ] Contact/email capture
- [ ] Order status tracking
- [ ] Connect to Railway backend API

## Phase 4 (future — influencer tracking)

- [ ] Unique influencer links
- [ ] UTM parameter capture
- [ ] Referral/promo codes
- [ ] Conversion tracking
- [ ] Admin dashboard

## Phase 5 (future — Android Play Store)

- [ ] Verify PWA is production-ready
- [ ] Write TWA setup documentation
- [ ] Digital Asset Links file for TWA domain verification
