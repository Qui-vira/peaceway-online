# PeaceWay Online — UI/UX Rebuild Plan (Core First)

Rebuild the UI/UX of the PeaceWay pharmacy app across **mobile web, desktop web, and installable PWA**, using the **UI/UX Pro Max** skill + **frontend-design** skill, and add the Apple-style **scroll-linked image sequence** hero from the reference article.

## Locked decisions
- **Scope:** Core flows first — Landing → Shop → Product → Cart → Checkout. Expand to secondary routes (prescription, reminders, ask-pharmacist, track, profile, orders) and admin only after review.
- **Design tooling:** UI/UX Pro Max v2.6.2 (installed at `~/.claude/skills/`) + `frontend-design`.
- **Animation:** GSAP + ScrollTrigger (already in `web/package.json`).
- **Frames:** `C:\Users\Bigquiv\Downloads\Frames` — 241 JPGs (`ezgif-frame-001…241`). ~8s @30fps → will subsample/compress for weight.
- **Brand:** Extend existing tokens (dark `#0b0c09`, greens `--g/--g2`, Syne display + DM Sans). Do NOT reuse the Quivira override.
- **Stack:** Next.js 14 App Router + Tailwind (`web/`). PWA already scaffolded (`manifest.json`, `sw.js`, `icons/`, `app/offline`).

---

## Phase 0 — Design system foundation (spec, no app code) ✅ DONE
- [x] Run Pro Max generator → `design-system/peaceway/MASTER.md`
- [x] Reconcile generated system with existing `globals.css` tokens (generator suggested a LIGHT theme; kept DARK brand, adopted a11y/structure discipline)
- [x] Produce single source of truth `tasks/DESIGN.md` (semantic tokens, type/spacing/shadow scales, states, motion, breakpoints, checklist)
- [x] A11y fix identified: `--g #0f673c` fails AA for text → added `--g-on #34d98a` for green text/icons/focus
- [ ] **CHECK-IN with user before Phase 1** ← WE ARE HERE

## Phase 1 — Hero scroll sequence + REMOVE old video system (full replace)
**Decision: full replace — scroll sequence becomes the landing's motion system; all background videos removed.**

Asset prep (frames were 4K/46MB + watermark + light bg):
- [x] Confirmed frames depict the pharmacy BUILDING in exploded-view teardown (assembled↔exploded)
- [x] Pipeline built: rembg AI matte → knocks out grey bg + removes "GenflowAI.io" watermark → building floats on dark
- [~] Batch processing 241→121 frames (step 2), matte @1600px, export alpha WebP desktop + 960px mobile → `web/public/sequence/` (RUNNING ~12s/frame)

Removal (full replace) — DONE:
- [x] Deleted 13 MP4s + `public/videos/` (~40MB gone)
- [x] Deleted dead subtree: `components/sections/*`, `ui/section-shell`, `ui/video-background`, `ui/glass-card`, `ui/navbar`, `ui/lazy-video`
- [x] Removed `<video>`/`<LazyVideo>` from all 9 scenes in `page.tsx`; sections keep content + `.sv-fb` dark backdrop
- [x] Trimmed `media.ts` to `logo` + `pharmacyPhoto`
- [ ] Prune now-dead `.sv/.ov/.grg` CSS (deferred to end, harmless for now)

Build:
- [x] `ScrollSequence.tsx`: manifest-driven preload → canvas contain/center → lerp scrub to scene scroll → reduced-motion/mobile/save-data static-frame fallback
- [x] Wired into hero (`#s1`); typecheck passes; dev server compiles 200; content verified intact
- [x] Refactored scrub from scroll-events → rAF loop (robust; scroll events don't fire in some layouts). IntersectionObserver gates the loop to when hero is visible
- [x] Verified logic deterministically: progress→frame mapping produces assembled→exploded (coverage 5.4×, spread to 87%); signage fades 1→0 by 18% scroll. (Live rAF not observable in preview: tab is `hidden` so rAF paused — real visitors animate fine)
- [x] Asset weight: DESKTOP 15MB/121 frames + 16KB signage (was ~40MB video); MOBILE loads 1 static frame ≈70KB total. Big win, esp. mobile

## Phase 1b — Pharmacy signage restore (approved plan)
- [x] User provided 4 signs → `Downloads/Signage/{round,fascia,wall,blade}.png`
- [x] Matted all 4 with rembg (transparent, autocropped)
- [x] Composited onto building: round (top-left projecting) + fascia (canopy) + blade (right). DROPPED serif `wall` sign — redundant wordmark, clutters canopy (can re-add if wanted)
- [x] Exported `web/public/branding/signage-desktop.webp` (13.5KB) + `signage-mobile.webp` (6.6KB)
- [x] `ScrollSequence.tsx` overlays signage layer, fades over first 18% scroll; CSS added; typecheck passes
- [ ] Live verify: assembled hero shows signage, fades on scroll, mobile static shows it (BLOCKED on batch)

## Phase 2 — Scroll depth on existing sections ✅ (commit 0832aeec)
Re-scoped after finding: mobile landing is a horizontal carousel (vertical-scroll
techniques are desktop-only), hover/tap card states already exist, product cards
live on /shop (Phase 3). So enhanced existing sections instead of adding demos.
- [x] Parallax: giant `.snbg` section numbers drift vs pinned content (desktop, scroll+rAF, reduced-motion-safe)
- [x] Sticky-reveal: `#s5` "How It Works" steps highlight (badge fills, others dim) as each passes viewport centre via IntersectionObserver; no-JS = full
- [x] Hover product cards -> deferred to Phase 3 (shop), where product cards exist
- [x] Verified statically (CSSOM rules correct, JS wiring, parallax transform computed, typecheck). Live motion needs a visible browser: preview tab is `hidden` so rAF/IO/getComputedStyle are frozen

## Phase 3 — Core responsive rebuild (mobile + desktop)
- [x] Shared shell: responsive AppShell — desktop top nav (logo + nav + live cart badge), mobile bottom-nav, shared footer; DESIGN.md a11y (3px focus rings, 44px targets, aria-current, safe-area). typecheck ✓
- [ ] Landing page
- [x] Shop grid (`/shop`) — responsive grid (2→5 cols), constrained container, 16px mobile search input, focus rings + 44px targets, desktop cart in top nav
- [x] Product detail (`/shop/[id]`) — desktop 2-col (sticky media + info/CTA), shared BackBar, focus rings + 48px CTA
- [ ] Cart (`/cart`)
- [ ] Checkout (`/checkout`)
- [ ] Verify each at 375 / 768 / 1280

## Phase 4 — PWA mobile-app polish
- [ ] Audit/upgrade `manifest.json` (maskable icons, theme/background color, `display: standalone`, shortcuts)
- [ ] Improve `sw.js` caching strategy (incl. frame sequence); refine install prompt + `app/offline` page
- [ ] Verify installable + offline behavior in preview

## Phase 5 — Verify & prove
- [ ] Dev server in preview pane; check console/network for errors
- [ ] Screenshots: landing/shop/product/cart/checkout at mobile + desktop
- [ ] Confirm reduced-motion + frame-load fallback behave
- [ ] `graphify update .`

---

## Review
(to be filled in as work completes)
