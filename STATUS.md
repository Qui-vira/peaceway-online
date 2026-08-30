# STATUS.md — Peaceway Online

Last updated: 2026-08-30

---

## Overall progress

| Phase | Description | Status |
|---|---|---|
| Bot backend | Telegram bot (all customer + staff features) | ✅ Complete |
| REST API | `app/api/v1/` — shared backend for the website | ✅ Built |
| Phase 1 | Marketing website (Next.js) | ✅ Built |
| Phase 3 | Web customer features (shop, cart, checkout, orders, Rx, etc.) | ✅ Built |
| Web auth | Telegram-bridge OTP + session auth, account linking | ✅ Built |
| Web admin | Admin panel (dispatch, partners, sourcing) | ✅ Built |
| Phase 2 | Real CTA links (WhatsApp, Facebook, PCN) | ⏳ Waiting on user |
| Phase 4 | Influencer & campaign tracking | 🟡 Partial (referral page exists) |
| Phase 5 | Android TWA documentation | 🔴 Not started |

---

## Backend (Railway)

- FastAPI + aiogram webhook server: deployed on Railway
- PostgreSQL: provisioned on Railway
- Alembic migrations: 21 migrations, up to date (latest RBAC/admin + web auth tables)
- Bot features: all phases complete (order engine, logistics, crypto, CRM,
  scan-to-update, payments admin, orders admin, RBAC, AI photo inventory intake)
- REST API (`app/api/v1/`): catalog · orders · customers · requests · prescriptions ·
  ask · track · reminders · zones · partner · admin · OTP auth · health

---

## Frontend (Vercel)

- `web/` directory: ✅ exists (Next.js 14 App Router + TypeScript)
- Marketing site: all 10 sections built as React components with video backgrounds
- Web customer app: shop · cart · checkout · orders · track · prescription ·
  ask-pharmacist · request(s) · profile · reminders · referral · offline (PWA)
- Web admin panel: dispatch · partners · sourcing
- Client API layer (`web/lib/api/`): ask · catalog · customers · orders · otp ·
  reminders · requests
- Vercel project: link/deploy status to confirm with user
- Domain: peacewayonline.com.ng — confirm DNS/Vercel pointing with user

---

## Recent work (latest commits)

- Web admin auth migrated from password gate to Telegram-bridge OTP + session auth
  (`web_admin_otps` / `web_admin_sessions` tables, `admin-auth.ts`, session dependency,
  SSR guards, concurrent-401 protection)
- Telegram to web account linking via the Telegram Login Widget
- Separate partner auth domain + partner portal; web design system; audit bug fixes
- CSV product import now creates new products, not just updates
- AI photo inventory intake: batch scan, review, safe commit (empty-commit guard)
- UI cleanup: hid staff/partner sign-in from customers; removed staff links from
  landing header; replaced em dashes with hyphens across bot and web

---

## Pending details from user (Phase 2)

These are placeholders in the design — do NOT invent them:

| Item | Status |
|---|---|
| WhatsApp number | ⏳ Not provided |
| Facebook page link | ⏳ Not provided |
| PCN registration number | ⏳ Not provided |
| Additional Telegram links | ✅ Bot: t.me/Peacewayonline_bot · Channel: t.me/peacewayonline |
| Instagram | ✅ @peacewayonline (link in design) |

---

## Key file locations

| File | Purpose |
|---|---|
| `app/main.py` | FastAPI + aiogram app entry |
| `app/api/v1/` | REST API used by the website |
| `app/bot/customer/` | All customer-facing bot handlers |
| `app/bot/staff/` | All staff bot handlers |
| `app/models/` | SQLAlchemy models |
| `app/services/` | Business logic layer |
| `app/core/config.py` | Pydantic settings (reads .env) |
| `app/core/rbac.py` | RBAC single source of truth (roles/permissions) |
| `web/app/` | Next.js pages (marketing, customer app, admin) |
| `web/components/sections/` | Marketing site section components |
| `web/lib/api/` | Typed client API layer |
| `.env.example` | All required environment variables |
| `Peaceway-Online-Project-Summary.docx` | Full project context (Word document) |
| `CODEX_HANDOFF.md` | Full project context for handoff |
| `AGENTS.md` | Agent instructions and architecture decisions |
| `TODO.md` | Implementation checklist |

---

## Architecture decision: monorepo

The Next.js frontend lives in `web/` inside this repo.
- Railway deploys the Python backend from repo root
- Vercel deploys only the `web/` subfolder
- One git history, two deployment targets
