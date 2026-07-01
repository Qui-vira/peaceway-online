# STATUS.md — Peaceway Online

Last updated: 2026-07-01

---

## Overall progress

| Phase | Description | Status |
|---|---|---|
| Bot backend | Telegram bot (all customer + staff features) | ✅ Complete |
| Phase 1 | Marketing website (Next.js from design handoff) | 🔴 Not started |
| Phase 2 | Real CTA links (WhatsApp, Facebook, PCN) | ⏳ Waiting on user |
| Phase 3 | Web customer features | 🔴 Not started |
| Phase 4 | Influencer & campaign tracking | 🔴 Not started |
| Phase 5 | Android TWA documentation | 🔴 Not started |

---

## Backend (Railway)

- FastAPI + aiogram webhook server: deployed on Railway
- PostgreSQL: provisioned on Railway
- Alembic migrations: up to date (latest: `c07f1fcf6833_add_rbac_admin_tables.py`)
- Bot features: all 5 phases complete (order engine, logistics, crypto, CRM, scan-to-update, payments admin, orders admin)

---

## Frontend (Vercel)

- `web/` directory: **does not exist yet**
- Vercel project: **not linked yet**
- Domain: peacewayonline.com.ng — **not pointed to Vercel yet**

---

## Design handoff

- Location: `peaceway-online-pharmacy-website/project/Peaceway Online v2.dc.html`
- Status: ✅ Complete and ready to implement
- Videos: ✅ All 9 section videos present in `uploads/`
- Logo: ✅ Present (`pasted-1782918307538-0.png`)
- Pharmacy photo: ✅ Present (`pharmacy_photos-1782916474882.jpg`)

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

## Git log (recent)

```
db2b90b feat: Orders Admin and Payments Review for staff panel
b43597c feat: Phase 5 - Scan-to-Update (barcode + OCR, human-confirmed)
2ec323f feat: Phase 4 - Customer CRM for admin staff
f77bf34 feat: Phase 3 - Product-Request CRM with full lifecycle management
504e714 feat: Phase 2 — core email capture (soft mode)
```

---

## Key file locations

| File | Purpose |
|---|---|
| `app/main.py` | FastAPI + aiogram app entry |
| `app/bot/customer/` | All customer-facing bot handlers |
| `app/bot/staff/` | All staff bot handlers |
| `app/models/` | SQLAlchemy models |
| `app/services/` | Business logic layer |
| `app/core/config.py` | Pydantic settings (reads .env) |
| `.env.example` | All required environment variables |
| `peaceway-online-pharmacy-website/project/Peaceway Online v2.dc.html` | Primary design file |
| `CODEX_HANDOFF.md` | Full project context for Codex |
| `AGENTS.md` | Agent instructions and architecture decisions |
| `TODO.md` | Implementation checklist |

---

## Architecture decision: monorepo

The Next.js frontend lives in `web/` inside this repo.  
- Railway deploys the Python backend from repo root  
- Vercel deploys only the `web/` subfolder  
- One git history, two deployment targets

Railway and Vercel both support subfolder/root configuration independently.
