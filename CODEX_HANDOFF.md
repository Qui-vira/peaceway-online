# Peaceway Online — Codex Handoff

## Project Overview

**Business:** Peaceway Online — online extension of Peaceway Pharmacy  
**Location:** Igando/Agodo Ikotun, Lagos, Nigeria  
**Telegram bot:** @peacewayonline_bot  
**Domain:** peacewayonline.com.ng (deployment target: Vercel)  
**Repository:** `C:\Projects\peaceway-online`

---

## What Exists Today

### Backend (complete, do not break)
- **Stack:** Python 3.11 · FastAPI · aiogram 3.x · SQLAlchemy 2.0 async · asyncpg · Alembic · APScheduler
- **Deployed on:** Railway
- **Entry point:** `app/main.py` (FastAPI + aiogram webhook mode)
- **Bot polling fallback:** `app/run_polling.py`
- **Database:** PostgreSQL (async via asyncpg), migrations in `alembic/versions/`

### Frontend (does not exist yet)
- Zero HTML/CSS/JS files in the repo root
- The website must be built from scratch using the Claude Design handoff

---

## Design Handoff Location

```
peaceway-online-pharmacy-website/
  project/
    Peaceway Online v2.dc.html   ← PRIMARY DESIGN FILE (implement this)
    uploads/
      pasted-1782918307538-0.png   ← logo (white bg, use as navbar/footer logo)
      pharmacy_photos-1782916474882.jpg  ← pharmacy photo (used in S4 trust section)
      seedance_video-1782916391537.mp4   ← hero video
      video_s2-1782917180864.mp4
      video_s3-1782917190299.mp4
      video_s4-1782917256362.mp4
      video_s5-1782917270624.mp4
      video_s6-1782917279984.mp4
      video_s7-1782917286495.mp4
      video_s8-1782917293810.mp4
      video_s9-1782917301410.mp4
      video_extra-1782917308099.mp4
      seedance_2-*.mp4   ← additional hero/background variants
```

The `.dc.html` file contains the full layout, styles, copy, animations, and JavaScript logic. Read it completely before implementing.

---

## Telegram Bot Features (customer-facing)

Implemented in `app/bot/customer/`:

| Feature | File |
|---|---|
| Welcome / main menu | `menu.py` |
| Product catalog browse + search | `catalog.py` |
| Cart (add, remove, view, clear) | `cart.py`, `cart_store.py` |
| Checkout (name, phone, address, area, landmark, time, note) | `checkout.py` |
| Payment — manual bank transfer proof upload | `payment.py` |
| Payment — Flutterwave (card/online) | `payment.py` |
| Payment — Crypto (tx hash submission) | `crypto.py` |
| Prescription upload → pharmacist review | `prescription.py` |
| Ask the Pharmacist | `support.py` |
| Product availability request (CRM lead flow) | `product_request.py` |
| Order tracking | `track.py` |
| Track product requests | `track_requests.py` |
| Customer profile management | `profile.py` |
| Email capture gate | `email_gate.py` |
| 24h post-delivery follow-up | `followup.py` |
| Speak to support | `menu.py` |
| Delivery areas + fees viewer | `menu.py` |

Staff panel features in `app/bot/staff/`: orders admin, payments admin, products management, CSV import, customer CRM, product requests CRM, pharmacist inbox, prescription review, delivery management, RBAC admin panel, barcode + OCR scan-to-update.

---

## Database Models Summary

`app/models/`:
- `orders.py` — `Customer`, `Order`, `OrderItem`, `OrderStatus`, `RxStatus`, `DeliveryStatus`, `PaymentMethod`
- `catalog.py` — `Product`, `ProductAlias`, `ProductPricing`, `PriceHistory`, `ProductIdentifier`, `ProductScanAttempt`
- `logistics.py` — `DeliveryZone`, `RiderAssignment`, `TrackingLink`
- `payments.py` — `Payment`
- `ops.py` — `PharmacistMessage`, `ProductRequest`, `Prescription`
- `admin.py` — RBAC tables
- `crypto.py` — `CryptoPayment`

---

## Website Implementation Plan

### Phase 1 — Marketing website (implement now)
Implement `Peaceway Online v2.dc.html` as a real Next.js web app with:
- All 9 sections + footer faithfully reproduced
- Cinematic video backgrounds with autoplay + parallax
- Scroll-based reveals and section transitions
- PWA foundation (manifest, service worker, icons)
- Vercel-ready build

### Phase 2 — Real CTA links (after user provides final details)
- Replace placeholders: WhatsApp number, Facebook link, PCN number
- No code changes needed beyond updating constants

### Phase 3 — Web customer features
Mirror Telegram bot flows on the website:
- Customer order request
- Product availability check
- Ask pharmacist
- Prescription upload
- Contact capture (email, phone)
- Order status tracking

### Phase 4 — Influencer & campaign tracking
- Unique influencer links, UTM tracking, referral codes, promo codes
- Click/lead/conversion tracking
- Simple admin dashboard

### Phase 5 — Android Play Store path
- PWA must be production-ready first
- Trusted Web Activity (TWA) wrapper documentation
- No Play Store release in this phase

---

## Environment Variables (Python backend)

See `.env.example` for all keys. Key ones:
- `TELEGRAM_BOT_TOKEN` — aiogram bot
- `DATABASE_URL` — PostgreSQL (asyncpg)
- `WEBHOOK_BASE_URL` — Railway public URL
- `FLUTTERWAVE_SECRET_KEY` / `FLUTTERWAVE_PUBLIC_KEY`
- `BANK_ACCOUNTS` — pipe-separated bank details
- `OWNER_TELEGRAM_IDS`, `PHARMACIST_TELEGRAM_IDS`, etc.

The Next.js frontend needs **no backend env vars** for Phase 1 (purely static marketing site). Phase 3 will need a `NEXT_PUBLIC_API_URL` pointing to the Railway backend.

---

## Safety Rules (non-negotiable)

1. **Do not break existing bot files.** Never touch anything in `app/`, `alembic/`, `scripts/`, `tests/`, `Procfile`, `railway.json`, `nixpacks.toml`, `pyproject.toml`, `requirements.txt`, `runtime.txt`.
2. **Do not invent:** PCN number, license number, phone number, WhatsApp number, Facebook link, years of experience, customer reviews, medical claims, delivery guarantees.
3. **Do not build B2B, wholesale, bulk supply, or organization features.**
4. **Do not expose secrets.** No API keys in frontend code or committed `.env` files.
5. **Verify Vercel project** before any `vercel` CLI command — run `cat .vercel/project.json` first.
6. **B2C only** for all web features implemented now.
