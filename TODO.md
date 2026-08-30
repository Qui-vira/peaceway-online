# TODO — Peaceway Online

Last updated: 2026-08-30

Phases 1 and 3 (marketing website + web customer app) are **built**. This file now
tracks what remains: deploy verification, the Phase 2 placeholder swaps, and future
work (influencer tracking, Android TWA).

---

## Phase 1 — Marketing website ✅ DONE

- [x] `web/` — Next.js 14 App Router + TypeScript
- [x] Design tokens, fonts (Syne / DM Sans), Tailwind config
- [x] Global UI (cursor, grain, scroll progress, navbar, video backgrounds)
- [x] All 10 sections (hero, problem, services, trust, how-it-works, pharmacist,
      delivery, community, contact, footer)
- [x] Motion / scroll reveals / parallax / reduced-motion
- [x] PWA foundation (manifest, service worker, offline shell, icons)
- [x] SEO metadata

## Phase 3 — Web customer features ✅ DONE

- [x] Shop + product detail, cart, checkout
- [x] Orders list + order detail, order tracking
- [x] Prescription upload, ask-pharmacist, product request(s)
- [x] Customer profile, reminders (list / new / detail)
- [x] Telegram-bridge OTP auth + session handling, account linking
- [x] Connected to Railway backend via `web/lib/api/` typed clients

## Web admin ✅ DONE

- [x] Admin panel: dispatch, partners, sourcing
- [x] Telegram-bridge OTP + session auth (replaced password gate)
- [x] Partner auth domain + partner portal

---

## Deploy / verification (open)

- [ ] Confirm Vercel project is linked and `web/` deploys cleanly (`vercel --prod`)
- [ ] Verify site loads at peacewayonline.com.ng (DNS pointed to Vercel)
- [ ] Verify video/image assets load in production (network tab)
- [ ] Lighthouse pass: Performance ≥ 80, Accessibility ≥ 90
- [ ] Cross-device smoke test: desktop Chrome, mobile Safari (375px),
      Android Chrome (390px), `prefers-reduced-motion`
- [ ] Confirm all external links open in new tab with `rel="noopener"`, no console errors

---

## Phase 2 — Real CTA links (waiting on user)

Do NOT invent these — swap placeholders only once the user provides them:

- [ ] Replace WhatsApp placeholder with real number
- [ ] Replace Facebook placeholder with real link
- [ ] Replace PCN placeholder with real registration number
- [ ] Update Telegram channel link if changed

---

## Phase 4 — Influencer & campaign tracking (partial)

- [x] Referral page (`web/app/referral/`)
- [ ] Unique influencer links
- [ ] UTM parameter capture
- [ ] Referral / promo codes
- [ ] Click / lead / conversion tracking
- [ ] Admin dashboard for campaign metrics

## Phase 5 — Android Play Store (not started)

- [ ] Verify PWA is production-ready
- [ ] Write TWA setup documentation
- [ ] Digital Asset Links file for TWA domain verification
