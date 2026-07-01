# AGENTS.md — Codex Agent Instructions

## Who you are working for

You are implementing the Peaceway Online website for a Lagos pharmacy (Peaceway Pharmacy, Igando/Agodo Ikotun). The business already has a working Telegram bot backend. You are building the public-facing website on top of it.

---

## Primary task

**Build the Next.js marketing website from the Claude Design handoff.**

The complete design is in:
```
peaceway-online-pharmacy-website/project/Peaceway Online v2.dc.html
```

Read that file completely before writing any code.

---

## Repository structure

```
C:\Projects\peaceway-online\
  app/                     ← Python backend (DO NOT TOUCH)
  alembic/                 ← DB migrations (DO NOT TOUCH)
  scripts/                 ← seed/import scripts (DO NOT TOUCH)
  tests/                   ← Python tests (DO NOT TOUCH)
  web/                     ← Next.js frontend (CREATE THIS)
  peaceway-online-pharmacy-website/  ← design handoff + video assets
  CODEX_HANDOFF.md         ← full project context
  TODO.md                  ← implementation checklist
  STATUS.md                ← current status tracker
```

---

## Tech stack for the website

- **Framework:** Next.js 14+ (App Router)
- **Language:** TypeScript
- **Styling:** Tailwind CSS
- **Animation:** Framer Motion + GSAP ScrollTrigger (GSAP only for pinned scroll/video scrubbing)
- **Fonts:** Syne (700, 800) + DM Sans (300, 400, 500, 600) via `next/font/google`
- **Deploy target:** Vercel (`web/` subfolder, separate Vercel project from Railway backend)

---

## Website sections to implement (9 sections + footer)

| ID | Section | Video |
|---|---|---|
| S1 | Hero Reveal | `seedance_video-1782916391537.mp4` |
| S2 | The Problem | `video_s2-1782917180864.mp4` |
| S3 | Services (What We Do) | `video_s3-1782917190299.mp4` |
| S4 | Why Trust Peaceway | `video_s4-1782917256362.mp4` |
| S5 | How Ordering Works | `video_s5-1782917270624.mp4` |
| S6 | Ask the Pharmacist | `video_s6-1782917279984.mp4` |
| S7 | Delivery Areas | `video_s7-1782917286495.mp4` |
| S8 | Community | `video_s8-1782917293810.mp4` |
| S9 | Contact | `video_s9-1782917301410.mp4` |
| — | Footer | — |

---

## Video and motion requirements

### Hero section
- First frame should show the dark/building reveal state
- Autoplay muted, but prefer scroll-scrubbing (scroll forward = video plays forward, scroll back = video plays back)
- Text/logo/headline/CTA appear at planned story beats as user scrolls
- When scroll stops, keep subtle ambient motion (glow, parallax, soft loop)
- Do not use the video autoplay loop for the hero scrub — use GSAP ScrollTrigger with `currentTime` scrubbing

### All other sections
- Muted autoplay loop video backgrounds
- Lazy load below-the-fold videos (`loading="lazy"` + IntersectionObserver play/pause)
- Poster image fallback while video loads
- Content reveals: Framer Motion `whileInView` with stagger

### Motion rules
- Parallax: depth layers move at different scroll speeds (section number watermark, glow overlay)
- Card tilt: mouse-tracking 3D tilt on `.gc` glass cards (Framer Motion `useMotionValue`)
- Custom cursor: green dot + ring, enlarges on hover (desktop only)
- Scroll progress bar: left edge, fills as user scrolls through the page
- Grain noise overlay: CSS animation on `body::before`
- Reduced motion: respect `prefers-reduced-motion` — skip all animations, show static frames

---

## PWA requirements

Create in `web/public/`:
- `manifest.json` with name, short_name, icons, theme_color `#0B0C09`, background_color `#0B0C09`, display `standalone`, start_url `/`
- `sw.js` — minimal service worker for offline shell caching
- Icons at 192×192 and 512×512 (generate from logo)

Add to `<head>`:
- `<meta name="apple-mobile-web-app-capable" content="yes">`
- `<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">`
- `<link rel="apple-touch-icon" href="/icons/icon-192.png">`
- `<meta name="theme-color" content="#0B0C09">`

---

## SEO requirements

- Title: `Peaceway Online | Lagos Pharmacy — Order Medicine on Telegram`
- Description: `Genuine medicines, pharmacist guidance, and delivery across Lagos. Order through Telegram from Peaceway Pharmacy, Igando.`
- Open Graph tags with pharmacy photo
- `sitemap.xml` and `robots.txt`
- Semantic HTML: `<nav>`, `<main>`, `<section>`, `<footer>`, proper heading hierarchy

---

## Mobile requirements

- Mobile-first Tailwind breakpoints
- Remove custom cursor on mobile (`@media (max-width: 800px)`)
- Navbar links hidden on mobile (hamburger or just CTA button)
- Grid layouts collapse to single column
- Videos use `playsInline` and `muted` attributes (required for iOS autoplay)
- Tap targets minimum 44×44px
- Test at 375px (iPhone SE) and 390px (iPhone 14)

---

## Asset paths

All video and image assets live in:
```
peaceway-online-pharmacy-website/project/uploads/
```

Copy them to `web/public/videos/` and `web/public/images/` during setup.

---

## Deployment

The `web/` subfolder deploys to Vercel as its own project.

Vercel config in `web/vercel.json`:
```json
{
  "buildCommand": "next build",
  "outputDirectory": ".next",
  "framework": "nextjs"
}
```

**Before running any `vercel` CLI command:** run `cat web/.vercel/project.json` to verify the project name. Never assume.

---

## What NOT to do

- Do not touch `app/`, `alembic/`, `scripts/`, `tests/`, `Procfile`, `railway.json`, `nixpacks.toml`
- Do not invent PCN number, phone, WhatsApp, Facebook link, reviews, or medical claims
- Do not build B2B or wholesale features
- Do not add backend API routes in Phase 1 (static marketing site only)
- Do not commit `.env` files with real secrets
- Do not use `pages/` router — use App Router only
- Do not use `export default function Page()` without TypeScript types
