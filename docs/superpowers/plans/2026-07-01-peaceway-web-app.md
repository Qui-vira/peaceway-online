# Peaceway Online — Web App Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert Peaceway Online from a Telegram-only pharmacy bot into a full web ordering platform, reusing all existing backend services and database models, while never breaking the live landing page.

**Architecture:** The existing FastAPI backend (on Railway) handles all business logic — we add a new `/api/*` router layer on top of the existing services. The Next.js frontend (on Vercel) calls this REST API. Customer identity is session-based (phone number + OTP or anonymous UUID). All Telegram bot features continue working in parallel — the web is an additional channel, not a replacement.

**Tech Stack:** Python 3.12 / FastAPI / SQLAlchemy 2 async / aiogram 3 / PostgreSQL (backend, Railway) — Next.js 14 / React 18 / Tailwind CSS / Framer Motion (frontend, Vercel) — Supabase Storage or Cloudinary for web-uploaded files (prescriptions, payment proofs)

---

## SECTION 1 — FULL FEATURE INVENTORY (FROM CODEBASE INSPECTION)

### 1A. Customer Telegram Bot Features (all complete in code)

| # | Feature | File(s) | Tables Touched | External Service |
|---|---------|---------|----------------|-----------------|
| C01 | Welcome / Main Menu | `bot/customer/menu.py` | `customers` | — |
| C02 | Product Catalog Browse | `bot/customer/catalog.py` | `products`, `product_aliases`, `product_pricing` | — |
| C03 | Product Search (fuzzy) | `bot/customer/catalog.py` | `products`, `product_aliases` | — |
| C04 | Shopping Cart (FSM in-memory) | `bot/customer/cart.py` | none (FSM state) | — |
| C05 | Checkout + Delivery Area | `bot/customer/checkout.py` | `orders`, `order_items`, `delivery_zones` | — |
| C06 | Bank Transfer Proof Upload | `bot/customer/payment.py` | `payments` | Telegram file_id |
| C07 | Flutterwave Payment | `bot/customer/payment.py`, `services/payments/flutterwave.py` | `payments`, `payment_webhook_events` | Flutterwave API |
| C08 | Crypto Payment | `bot/customer/crypto.py`, `services/payments/crypto.py` | `crypto_payments` | Manual / blockchain |
| C09 | Prescription Upload | `bot/customer/prescription.py` | `prescriptions` | Telegram file_id |
| C10 | Ask the Pharmacist | `bot/customer/support.py` | `pharmacist_questions`, `pharmacist_messages` | — |
| C11 | Product Availability Request | `bot/customer/product_request.py` | `product_requests`, `product_request_messages`, `product_request_status_events` | — |
| C12 | Order Tracking | `bot/customer/track.py` | `orders`, `order_items`, `rider_assignments`, `tracking_links` | — |
| C13 | Product Request Tracking | `bot/customer/track_requests.py` | `product_requests`, `product_request_messages` | — |
| C14 | Customer Profile + Email Prefs | `bot/customer/profile.py` | `customers`, `customer_preferences` | — |
| C15 | Email Capture Gate (soft) | `bot/customer/email_gate.py` | `customers`, `customer_contact_events` | — |
| C16 | 24h Post-Delivery Follow-up | `bot/customer/followup.py` | `customers`, `customer_messages` | SMTP (optional) |
| C17 | Delivery Areas View | `bot/customer/menu.py` | `delivery_zones` | — |

### 1B. Staff / Admin Telegram Bot Features (all complete in code)

| # | Feature | File(s) | Roles Required |
|---|---------|---------|----------------|
| S01 | /admin Staff Panel + Menu | `bot/staff/panel.py` | Any role |
| S02 | Order Status Management | `bot/staff/orders.py`, `orders_admin.py` | Support, Packaging, Dispatcher |
| S03 | Payment Proof Review | `bot/staff/payments_admin.py` | Finance |
| S04 | Prescription Review | `bot/staff/prescriptions.py` | Lead Pharmacist, Pharmacist Admin |
| S05 | Pharmacist Inbox (Q&A) | `bot/staff/pharmacist.py` | Lead Pharmacist, Pharmacist Admin |
| S06 | Product Request CRM | `bot/staff/requests.py` | Support |
| S07 | Product Management (price/stock) | `bot/staff/products.py` | Lead Pharmacist |
| S08 | CSV Product Import | `bot/staff/products_csv.py` | Lead Pharmacist |
| S09 | Barcode + OCR Scan-to-Update | `bot/staff/scan.py` | Lead Pharmacist |
| S10 | RBAC Staff Management | `bot/staff/admins.py` | System Owner |
| S11 | Customer CRM | `bot/staff/customers.py` | Support |
| S12 | Delivery Booking | `bot/staff/delivery.py` | Dispatcher |
| S13 | Crypto Payment Review | `bot/staff/crypto.py` | Finance |

### 1C. Database Tables (30+ complete)

**Customer & Orders:**
- `customers` — master customer record (13 cols)
- `customer_contact_events` — email change audit (8 cols)
- `customer_preferences` — notification opt-ins (7 cols)
- `customer_messages` — admin-to-customer messages (12 cols)
- `customer_notes` — internal staff notes (5 cols)
- `orders` — master order record (24 cols)
- `order_items` — line items (9 cols)
- `order_status_history` — status change audit (7 cols)

**Products & Catalog:**
- `products` — product master, imported from PharmaOS (13 cols)
- `product_aliases` — drug name variants for fuzzy search (5 cols)
- `product_pricing` — Peaceway's own cost/selling/stock (10 cols)
- `price_history` — price change audit (9 cols)
- `product_identifiers` — barcode/SKU mappings (8 cols)
- `product_scan_attempts` — scan audit (10 cols)

**Payments:**
- `payments` — payment record (10 cols) — method: BANK_TRANSFER, FLUTTERWAVE, CRYPTO
- `payment_webhook_events` — Flutterwave webhook audit (7 cols)
- `crypto_payments` — crypto off-ramp tracking (11 cols)

**Operational:**
- `pharmacist_questions` — Q&A master (8 cols)
- `pharmacist_messages` — Q&A thread (6 cols)
- `prescriptions` — uploaded Rx (11 cols) — stores Telegram file_id **[WEB BLOCKER: see Phase 0]**
- `product_requests` — availability CRM lead (16 cols)
- `product_request_messages` — thread messages (7 cols)
- `product_request_status_events` — status timeline (6 cols)
- `fee_settings` — global fee config singleton (9 cols)
- `delivery_zones` — Lagos zones + fees (6 cols)

**Logistics:**
- `logistics_providers` — provider registry (6 cols)
- `delivery_orders` — provider delivery records (11 cols)
- `delivery_quotes` — quote history (6 cols)
- `rider_assignments` — rider info (6 cols)
- `tracking_links` — GPS URLs (4 cols)
- `delivery_tracking_events` — live tracking (7 cols)
- `delivery_webhook_events` — webhook audit (6 cols)

**RBAC & Admin:**
- `roles` — role master (4 cols)
- `permissions` — permission catalog (4 cols)
- `role_permissions` — mapping (4 cols)
- `admin_users` — staff records (8 cols)
- `admin_role_assignments` — role assignments (5 cols)
- `admin_activity_logs` — audit trail (30 cols)
- `audit_logs` — generic audit (9 cols)
- `staff` — legacy (being replaced by RBAC)

### 1D. Current FastAPI HTTP Routes

**Only 4 routes exist — none are public REST API:**

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/health` | GET | Health check |
| `/webhook/telegram` | POST | Telegram bot updates |
| `/webhook/flutterwave` | POST | Payment confirmation |
| `/webhook/logistics/{provider_key}` | POST | Delivery tracking |

**No public REST API exists. No CORS configured. No customer auth.**

### 1E. Critical Web Blockers Found

1. **File storage uses Telegram file_ids** — `prescriptions.file_id` and `payments.proof_file_id` are Telegram file IDs. Web users cannot submit Telegram file IDs. Web uploads need cloud storage (S3, Supabase Storage, or Cloudinary) and a new `web_file_url` column alongside the existing `file_id`.

2. **No REST API** — 100% of business logic is in Telegram bot handlers. Every web feature needs a new FastAPI router.

3. **No customer auth** — Customers are identified by Telegram ID. Web needs phone-based session (OTP or UUID cookie).

4. **No CORS** — Railway backend blocks cross-origin requests from Vercel by default.

5. **Cart is FSM in-memory** — Resets on bot restart. Web cart needs database-backed cart (new table or `order_items` with status `DRAFT`).

---

## SECTION 2 — REUSE MAP

| Bot Feature | Reuse Status | Notes |
|-------------|-------------|-------|
| C01 Welcome/Menu | Needs frontend only | No backend needed; web has own navigation |
| C02 Product Catalog | Needs API wrapper | `services/catalog.py` exists; wrap in `GET /api/products` |
| C03 Product Search | Needs API wrapper | `services/catalog.py` search; wrap in `GET /api/products?q=` |
| C04 Cart | Needs new backend endpoint | FSM cart doesn't translate; need DB-backed draft cart |
| C05 Checkout + Delivery | Needs API wrapper | `services/orders.create_order()` exists; wrap in `POST /api/orders` |
| C06 Bank Transfer Proof | Needs new backend + migration | File storage: add `web_file_url` column; upload endpoint needed |
| C07 Flutterwave | Can reuse directly | Webhook already works; just need `POST /api/payments/flutterwave/link` |
| C08 Crypto | Needs API wrapper | Wallet display + tx hash submit; wrap existing service |
| C09 Prescription Upload | Needs new backend + migration | File storage: add `web_file_url` column; upload endpoint needed |
| C10 Ask Pharmacist | Needs API wrapper | `services/pharmacist_inbox.py` exists; wrap in `POST /api/pharmacist/ask` |
| C11 Product Request | Needs API wrapper | `services/product_requests.py` exists; wrap in `POST /api/requests` |
| C12 Order Tracking | Needs API wrapper | Order query by code/phone; wrap in `GET /api/track/{code}` |
| C13 Request Tracking | Needs API wrapper | Request query; wrap in `GET /api/requests/{id}` |
| C14 Customer Profile | Needs API wrapper | `services/customers.py` exists; wrap in `GET/PATCH /api/me` |
| C15 Email Capture | Needs API wrapper | Already in service; trigger from profile or checkout |
| C16 24h Follow-up | Can reuse directly | APScheduler already runs; no web change needed |
| C17 Delivery Areas | Needs API wrapper | `GET /api/zones` from `delivery_zones` table |
| S01-S13 Staff features | Should not be added yet (Phase 7) | Build staff web panel after customer features are stable |

---

## SECTION 3 — PHASED IMPLEMENTATION PLAN

---

### PHASE 0 — Backend / API Readiness
**Goal:** Make the FastAPI backend safe to call from the web. No customer features yet.
**Risk:** High (touches core backend) — do this first, carefully.
**Estimated effort:** 2–3 days

**Files to create/modify:**
- Create: `app/api/__init__.py`
- Create: `app/api/deps.py` — shared FastAPI dependencies (session, optional auth)
- Create: `app/api/v1/__init__.py`
- Create: `app/api/v1/router.py` — aggregate all sub-routers
- Modify: `app/main.py` — mount `/api/v1` router, add CORS middleware
- Modify: `app/core/config.py` — add `ALLOWED_ORIGINS`, `WEB_SECRET`, `FILE_STORAGE_PROVIDER` settings
- Create: `app/services/file_storage.py` — abstraction over Supabase/S3 storage
- Create: `alembic/versions/xxxx_add_web_file_url_columns.py` — migration for web file columns

**Step-by-step tasks:**

- [ ] **0.1 — Add CORS to main.py**
  In `app/main.py`, after `app = FastAPI(...)`, add:
  ```python
  from fastapi.middleware.cors import CORSMiddleware
  from app.core.config import settings

  app.add_middleware(
      CORSMiddleware,
      allow_origins=settings.ALLOWED_ORIGINS,  # ["https://peacewayonline.com", "http://localhost:3000"]
      allow_credentials=True,
      allow_methods=["GET", "POST", "PATCH", "DELETE"],
      allow_headers=["*"],
  )
  ```
  Add to `app/core/config.py`:
  ```python
  ALLOWED_ORIGINS: list[str] = ["https://peacewayonline.com", "http://localhost:3000"]
  WEB_SECRET: str = ""  # Random 32-char secret for session signing
  ```

- [ ] **0.2 — Create API skeleton**
  Create `app/api/__init__.py` (empty).
  Create `app/api/v1/__init__.py` (empty).
  Create `app/api/v1/router.py`:
  ```python
  from fastapi import APIRouter
  router = APIRouter()
  ```
  In `app/main.py` add:
  ```python
  from app.api.v1.router import router as api_router
  app.include_router(api_router, prefix="/api/v1")
  ```

- [ ] **0.3 — Add ALLOWED_ORIGINS to Railway env vars**
  On Railway dashboard, add:
  - `ALLOWED_ORIGINS=https://peacewayonline.com,http://localhost:3000`
  - `WEB_SECRET=<random 32-char string>`
  Verify with `GET /health` from browser.

- [ ] **0.4 — Add web file URL columns (migration)**
  Create `alembic/versions/xxxx_add_web_file_url_columns.py`:
  ```python
  def upgrade():
      op.add_column('prescriptions', sa.Column('web_file_url', sa.String, nullable=True))
      op.add_column('payments', sa.Column('web_proof_url', sa.String, nullable=True))
  ```
  Run `alembic upgrade head` on Railway.

- [ ] **0.5 — Add file storage service**
  Create `app/services/file_storage.py`:
  ```python
  import httpx
  from app.core.config import settings

  async def upload_file(file_bytes: bytes, filename: str, folder: str) -> str:
      """Upload to Supabase Storage. Returns public URL."""
      # Uses SUPABASE_URL + SUPABASE_SERVICE_KEY from settings
      # Returns public URL string
      ...
  ```
  Add to `.env.example`:
  ```
  SUPABASE_URL=
  SUPABASE_SERVICE_KEY=
  SUPABASE_STORAGE_BUCKET=peaceway-uploads
  ```

- [ ] **0.6 — Add Vercel env vars**
  On Vercel dashboard for `peaceway-online`, add:
  ```
  NEXT_PUBLIC_API_URL=https://<railway-app>.up.railway.app/api/v1
  ```
  In `web/lib/api.ts` (create):
  ```typescript
  export const API_BASE = process.env.NEXT_PUBLIC_API_URL!;
  ```

- [ ] **0.7 — Verify end-to-end connectivity**
  From Next.js dev server, fetch `${API_BASE}/health` and confirm 200 response (no CORS error). This is the gate check before Phase 1.

---

### PHASE 1 — Customer Identity & Lead Capture
**Goal:** Create a minimal web customer identity: name, phone, email, delivery area. Save a `customers` record. This is the foundation every other feature depends on.
**Risk:** Low — no payment, no Rx, no uploads.
**Business value:** Highest — captures leads from every page visit.

**Files to create:**
- Create: `app/api/v1/customers.py` — `POST /api/v1/customers`, `GET /api/v1/me`, `PATCH /api/v1/me`
- Create: `app/api/v1/zones.py` — `GET /api/v1/zones`
- Create: `web/app/start/page.tsx` — single-page lead form
- Create: `web/lib/api/customers.ts` — API client functions

**Key design decision on auth:**
Web customers are identified by phone number. On first visit, they enter name + phone → backend creates/fetches customer → returns a signed session token (JWT or UUID stored in httpOnly cookie). No SMS OTP required in Phase 1 (add later in Phase 2). The web session token maps to `customers.id`.

- [ ] **1.1 — Add session token to customers table**
  ```python
  # alembic/versions/xxxx_add_web_session_token.py
  op.add_column('customers', sa.Column('web_session_token', sa.String, nullable=True))
  op.create_index('ix_customers_web_session_token', 'customers', ['web_session_token'], unique=True)
  ```

- [ ] **1.2 — Create customer API endpoints**
  Create `app/api/v1/customers.py`:
  ```python
  from fastapi import APIRouter, Depends, HTTPException, Response
  from pydantic import BaseModel
  from app.core.db import get_db
  from app.services.customers import get_or_create_customer
  import secrets, jwt
  from app.core.config import settings

  router = APIRouter(prefix="/customers", tags=["customers"])

  class CustomerCreate(BaseModel):
      full_name: str
      phone: str
      email: str | None = None
      delivery_area: str | None = None

  @router.post("/")
  async def create_customer(body: CustomerCreate, response: Response, db=Depends(get_db)):
      customer = await get_or_create_customer(db, phone=body.phone, full_name=body.full_name)
      if body.email:
          customer.email = body.email
      token = secrets.token_urlsafe(32)
      customer.web_session_token = token
      await db.commit()
      response.set_cookie("pw_session", token, httponly=True, samesite="lax", secure=True, max_age=2592000)
      return {"id": str(customer.id), "full_name": customer.full_name, "phone": customer.phone}

  @router.get("/me")
  async def get_me(customer=Depends(get_current_customer)):
      return customer
  ```

- [ ] **1.3 — Add auth dependency**
  Create `app/api/deps.py`:
  ```python
  from fastapi import Request, HTTPException, Depends
  from app.core.db import get_db
  from sqlalchemy import select
  from app.models.orders import Customer

  async def get_current_customer(request: Request, db=Depends(get_db)):
      token = request.cookies.get("pw_session")
      if not token:
          raise HTTPException(status_code=401, detail="Not authenticated")
      result = await db.execute(select(Customer).where(Customer.web_session_token == token))
      customer = result.scalar_one_or_none()
      if not customer:
          raise HTTPException(status_code=401, detail="Session expired")
      return customer

  async def get_optional_customer(request: Request, db=Depends(get_db)):
      token = request.cookies.get("pw_session")
      if not token:
          return None
      result = await db.execute(select(Customer).where(Customer.web_session_token == token))
      return result.scalar_one_or_none()
  ```

- [ ] **1.4 — Create zones endpoint**
  Create `app/api/v1/zones.py`:
  ```python
  from fastapi import APIRouter, Depends
  from app.core.db import get_db
  from app.models.logistics import DeliveryZone
  from sqlalchemy import select

  router = APIRouter(prefix="/zones", tags=["zones"])

  @router.get("/")
  async def list_zones(db=Depends(get_db)):
      result = await db.execute(select(DeliveryZone).where(DeliveryZone.is_active == True))
      zones = result.scalars().all()
      return [{"id": z.id, "name": z.name, "fee": z.fee, "eta_minutes": z.eta_minutes} for z in zones]
  ```

- [ ] **1.5 — Register routers**
  In `app/api/v1/router.py`:
  ```python
  from app.api.v1.customers import router as customers_router
  from app.api.v1.zones import router as zones_router
  router.include_router(customers_router)
  router.include_router(zones_router)
  ```

- [ ] **1.6 — Build web lead capture form**
  Create `web/app/start/page.tsx` — a minimal single-page form:
  - Fields: Full Name, Phone, Email (optional), Delivery Area (from `GET /api/v1/zones`)
  - Submit → `POST /api/v1/customers` → cookie set → redirect to `/`
  - No Telegram bot mention, no health claims, no fake testimonials
  - Add a "Get Started" CTA on landing page linking to `/start`

- [ ] **1.7 — Verify and commit**
  - Test: Submit form → customer created in DB → cookie returned → `GET /api/v1/me` returns customer
  - Test: Second submission with same phone returns existing customer (no duplicate)
  - Commit: `feat: add customer identity API and lead capture form`

---

### PHASE 2 — Product Request & Availability Check
**Goal:** Web users can request unavailable medicines. Feeds directly into existing `product_requests` CRM which staff already manages in Telegram.
**Risk:** Very low — no payments, no uploads, no Rx.
**Business value:** High — captures demand signals staff can action without any order.

**Files to create:**
- Create: `app/api/v1/requests.py` — `POST /api/v1/requests`, `GET /api/v1/requests/{id}`
- Create: `web/app/request/page.tsx` — product request form

- [ ] **2.1 — Create product requests endpoint**
  Create `app/api/v1/requests.py`:
  ```python
  from fastapi import APIRouter, Depends
  from pydantic import BaseModel
  from app.core.db import get_db
  from app.api.deps import get_optional_customer
  from app.services.product_requests import create_product_request

  router = APIRouter(prefix="/requests", tags=["requests"])

  class ProductRequestCreate(BaseModel):
      product_name: str
      strength: str | None = None
      form: str | None = None
      quantity: str | None = None
      delivery_area: str | None = None
      urgency: str = "WITHIN_24H"
      customer_phone: str
      customer_name: str | None = None
      note: str | None = None

  @router.post("/")
  async def create_request(body: ProductRequestCreate, db=Depends(get_db), customer=Depends(get_optional_customer)):
      req = await create_product_request(db, body.dict(), customer_id=customer.id if customer else None)
      return {"id": str(req.id), "status": req.status, "product_name": req.product_name}

  @router.get("/{request_id}")
  async def get_request(request_id: str, db=Depends(get_db)):
      # Returns status + visible message for customer
      ...
  ```

- [ ] **2.2 — Build web request form**
  Create `web/app/request/page.tsx`:
  - Fields: Product name, Strength, Form (select), Quantity, Urgency (select), Phone, Area (select from zones), Note (optional)
  - Submit → `POST /api/v1/requests` → show confirmation with request ID
  - No diagnosis claims, no "we'll find it" guarantees
  - Add CTA on landing page: "Can't find your medicine? Request it →"

- [ ] **2.3 — Staff Telegram alert**
  After creating request, alert existing staff via `services/alerts.py` (already built) — no new code needed, just call it from the API endpoint.

- [ ] **2.4 — Verify and commit**
  - Test: Submit request → created in DB → visible in Telegram staff panel under "Product Requests"
  - Test: Staff can update status → customer can check `/requests/{id}` via API
  - Commit: `feat: add product request web form and API`

---

### PHASE 3 — Ask the Pharmacist
**Goal:** Web users can send a question to the pharmacist. Feeds into existing `pharmacist_questions` table which staff manages in Telegram.
**Risk:** Very low — text only, no payments, no uploads.
**Safety note:** Must show disclaimer about not replacing medical advice.

**Files to create:**
- Create: `app/api/v1/pharmacist.py` — `POST /api/v1/pharmacist/ask`, `GET /api/v1/pharmacist/{id}`
- Create: `web/app/ask/page.tsx` — ask pharmacist form

- [ ] **3.1 — Create pharmacist endpoint**
  Create `app/api/v1/pharmacist.py`:
  ```python
  from fastapi import APIRouter, Depends
  from pydantic import BaseModel
  from app.core.db import get_db
  from app.api.deps import get_optional_customer
  from app.services.pharmacist_inbox import create_question

  router = APIRouter(prefix="/pharmacist", tags=["pharmacist"])

  class AskQuestion(BaseModel):
      question: str
      customer_phone: str
      customer_name: str | None = None
      product_id: str | None = None

  @router.post("/ask")
  async def ask_pharmacist(body: AskQuestion, db=Depends(get_db), customer=Depends(get_optional_customer)):
      question = await create_question(db, body.dict(), customer_id=customer.id if customer else None)
      return {"id": str(question.id), "status": "received"}

  @router.get("/{question_id}")
  async def get_thread(question_id: str, db=Depends(get_db)):
      # Returns thread (question + any pharmacist reply) for customer polling
      ...
  ```

- [ ] **3.2 — Build ask form**
  Create `web/app/ask/page.tsx`:
  - Disclaimer text: "Our pharmacist will respond within 24 hours. This is not a diagnosis or prescription."
  - Fields: Question, Name (optional), Phone, Product (optional free-text)
  - Submit → confirmation with question ID for follow-up
  - Polling: `GET /api/v1/pharmacist/{id}` every 30s to show reply when available
  - Add "Ask our Pharmacist" CTA in landing hero and nav

- [ ] **3.3 — Verify and commit**
  - Test: Submit question → visible in Telegram pharmacist inbox → pharmacist replies → customer sees reply on web
  - Commit: `feat: add ask-pharmacist web form and API`

---

### PHASE 4 — Prescription Upload & Review
**Goal:** Web users can upload a prescription image/PDF. Staff reviews in Telegram exactly as before.
**Risk:** Medium — first web file upload. File storage must work before enabling.
**Prerequisite:** Phase 0 file storage service must be complete and tested.

**Files to create:**
- Create: `app/api/v1/prescriptions.py` — `POST /api/v1/prescriptions`
- Create: `web/app/prescription/page.tsx` — upload form

- [ ] **4.1 — Create prescription upload endpoint**
  Create `app/api/v1/prescriptions.py`:
  ```python
  from fastapi import APIRouter, Depends, UploadFile, File, Form
  from app.core.db import get_db
  from app.api.deps import get_optional_customer
  from app.services.file_storage import upload_file
  from app.models.ops import Prescription
  import uuid

  router = APIRouter(prefix="/prescriptions", tags=["prescriptions"])

  @router.post("/")
  async def upload_prescription(
      file: UploadFile = File(...),
      customer_phone: str = Form(...),
      customer_name: str = Form(None),
      order_id: str = Form(None),
      db=Depends(get_db),
      customer=Depends(get_optional_customer),
  ):
      contents = await file.read()
      if len(contents) > 10 * 1024 * 1024:  # 10MB limit
          raise HTTPException(status_code=413, detail="File too large")
      
      web_file_url = await upload_file(contents, file.filename, folder="prescriptions")
      
      prescription = Prescription(
          id=uuid.uuid4(),
          customer_id=customer.id if customer else None,
          file_id=None,  # Not from Telegram
          web_file_url=web_file_url,
          file_type="image" if file.content_type.startswith("image/") else "document",
          review_status="PENDING",
      )
      db.add(prescription)
      await db.commit()
      # Alert pharmacists via existing alerts service
      return {"id": str(prescription.id), "status": "pending_review"}
  ```

- [ ] **4.2 — Build prescription upload form**
  Create `web/app/prescription/page.tsx`:
  - Warning: "Upload a clear photo or PDF. Our pharmacist will review before any prescription medicine is dispensed."
  - File input (image/PDF only, max 10MB)
  - Phone + name fields
  - No "auto-approve" language anywhere
  - Add "Upload Prescription" link in nav

- [ ] **4.3 — Verify and commit**
  - Test: Upload file → stored in Supabase → URL saved in DB → visible in Telegram prescription review queue
  - Test: Pharmacist can approve/reject in Telegram
  - Commit: `feat: add prescription upload web form and API`

---

### PHASE 5 — Product Catalog, Search, Cart, and Checkout
**Goal:** The full ordering flow on web — browse, add to cart, checkout. No payment page yet (payment comes Phase 8).
**Risk:** Medium — most complex flow; DB-backed cart needed.
**Prerequisite:** Phases 0-4 must be complete.

**New DB table needed:**
```sql
-- web_carts (replaces FSM in-memory cart)
CREATE TABLE web_carts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id UUID REFERENCES customers(id) NULL,
    session_id VARCHAR(64) NULL,  -- anonymous cart
    items JSONB NOT NULL DEFAULT '[]',
    expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX ix_web_carts_customer_id ON web_carts(customer_id);
CREATE INDEX ix_web_carts_session_id ON web_carts(session_id);
```

**Files to create:**
- Migration: `xxxx_add_web_carts.py`
- Create: `app/api/v1/products.py` — `GET /api/v1/products`, `GET /api/v1/products/{id}`
- Create: `app/api/v1/cart.py` — `GET/POST/PATCH/DELETE /api/v1/cart`
- Create: `app/api/v1/orders.py` — `POST /api/v1/orders`, `GET /api/v1/orders/{code}`
- Create: `web/app/shop/page.tsx` — catalog + search
- Create: `web/app/shop/[id]/page.tsx` — product detail
- Create: `web/app/cart/page.tsx` — cart view
- Create: `web/app/checkout/page.tsx` — checkout form (no payment yet)

- [ ] **5.1 — Product catalog API**
  Create `app/api/v1/products.py`:
  ```python
  @router.get("/")
  async def list_products(q: str = None, category: str = None, page: int = 1, db=Depends(get_db)):
      # Reuse services/catalog.py search function
      results = await search_products(db, query=q, category=category, page=page, page_size=20)
      return {
          "products": [
              {
                  "id": str(p.id),
                  "name": p.name,
                  "generic_name": p.generic_name,
                  "strength": p.strength,
                  "form": p.dosage_form,
                  "category": p.category,
                  "requires_prescription": p.requires_prescription,
                  "price": p.pricing.selling_price if p.pricing and p.pricing.is_in_stock else None,
                  "in_stock": p.pricing.is_in_stock if p.pricing else False,
                  "buyable": not p.requires_prescription and not p.requires_review and p.pricing and p.pricing.is_in_stock,
              }
              for p in results.items
          ],
          "total": results.total,
          "page": page,
      }
  ```

- [ ] **5.2 — Cart API**
  Cart items stored as JSONB: `[{product_id, name, qty, unit_price}]`
  Anonymous cart identified by `session_id` cookie (UUID, non-httpOnly).
  On login → merge anonymous cart with customer cart.

- [ ] **5.3 — Checkout / Order creation API**
  `POST /api/v1/orders` — accepts cart + delivery details → calls existing `services/orders.create_order()` → returns `{code, total, status}`.
  Rx items auto-trigger `rx_status=PRESCRIPTION_REQUIRED` (same as bot).
  Response tells frontend: "Your order is PW-XXXXX. You'll be asked to pay shortly."

- [ ] **5.4 — Build product pages**
  - `/shop` — search bar + grid of products (name, price, "Add to Cart" or "Requires Prescription" badge)
  - `/shop/[id]` — product detail (name, generic, strength, form, price, stock status)
  - `/cart` — cart summary with quantity controls + delivery area selector + subtotal
  - `/checkout` — delivery details form → confirms order → redirects to `/orders/{code}`

- [ ] **5.5 — Verify and commit**
  - Test: Search product → add to cart → checkout → order created in DB → visible in Telegram staff panel
  - Test: Rx product in cart → order status `PRESCRIPTION_REQUIRED` → prompts to upload prescription
  - Commit: `feat: add product catalog, cart, and checkout to web`

---

### PHASE 6 — Order & Request Tracking
**Goal:** Customer can check their order status via web using order code + phone. No account required.
**Risk:** Very low — read-only, no mutations.

**Files to create:**
- Extend: `app/api/v1/orders.py` — `GET /api/v1/orders/{code}` (public, auth by phone verification)
- Create: `web/app/track/page.tsx` — tracking lookup
- Create: `web/app/track/[code]/page.tsx` — order status page

- [ ] **6.1 — Public order tracking endpoint**
  ```python
  @router.get("/{code}")
  async def track_order(code: str, phone: str = Query(...), db=Depends(get_db)):
      order = await get_order_by_code(db, code)
      if not order or order.customer.phone != phone:
          raise HTTPException(404, "Order not found")
      return {
          "code": order.code,
          "status": order.status,
          "rx_status": order.rx_status,
          "delivery_status": order.delivery_status,
          "items": [...],
          "total": order.total,
          "delivery_address": order.delivery_address,
          "tracking_url": ...,
          "rider_name": ...,
          "rider_phone": ...,
      }
  ```

- [ ] **6.2 — Build tracking pages**
  - `/track` — Enter order code + phone number
  - `/track/[code]?phone=xxx` — Status display with progress bar, rider info if dispatched
  - Statuses shown: Awaiting Payment → Payment Under Review → Payment Approved → Being Packaged → Ready for Pickup → On the Way → Delivered

- [ ] **6.3 — Verify and commit**
  - Test: Create order in bot → track on web with code + phone → status shows correctly
  - Commit: `feat: add public order tracking page`

---

### PHASE 7 — Admin Web Dashboard
**Goal:** Staff can manage orders, product requests, pharmacist questions, and prescriptions from a web browser — no Telegram required.
**Risk:** High — protected routes, RBAC, must never expose customer data to wrong roles.
**Prerequisite:** Phases 1-6 must be complete and stable.

**Auth strategy for staff:**
Staff authenticate with email + password (or Telegram SSO). On first login, map to `admin_users` record. Issue JWT with role claims. Every protected endpoint checks permission via `app/core/rbac.py` matrix.

**Files to create:**
- Create: `app/api/v1/admin/auth.py` — `POST /api/v1/admin/login`
- Create: `app/api/v1/admin/orders.py` — staff order management
- Create: `app/api/v1/admin/customers.py` — CRM
- Create: `app/api/v1/admin/requests.py` — product request CRM
- Create: `app/api/v1/admin/pharmacist.py` — Q&A inbox
- Create: `app/api/v1/admin/prescriptions.py` — Rx review
- Create: `web/app/admin/` — protected staff panel pages

- [ ] **7.1 — Staff JWT auth**
  `POST /api/v1/admin/login` — body: `{email, password}` (or magic link sent to email)
  Lookup `admin_users.email` → validate → issue JWT with `{admin_id, roles[]}` → return as httpOnly cookie.

- [ ] **7.2 — RBAC middleware for admin routes**
  ```python
  def require_permission(perm: str):
      async def checker(admin=Depends(get_current_admin)):
          if perm not in admin.permissions:
              raise HTTPException(403, "Insufficient permissions")
          return admin
      return checker
  ```

- [ ] **7.3 — Order management API**
  Mirror Telegram staff order actions as HTTP endpoints:
  - `GET /api/v1/admin/orders?status=PAYMENT_SUBMITTED` (Finance)
  - `POST /api/v1/admin/orders/{id}/approve-payment` (Finance)
  - `POST /api/v1/admin/orders/{id}/start-packaging` (Packaging)
  - `POST /api/v1/admin/orders/{id}/mark-dispatched` (Dispatcher)
  - `POST /api/v1/admin/orders/{id}/mark-delivered` (Dispatcher)
  All call existing service functions + log to `admin_activity_logs`.

- [ ] **7.4 — Build admin dashboard pages**
  Protected by JWT cookie check:
  - `/admin` — role-based dashboard (shows only what the role can see)
  - `/admin/orders` — order queue with status filters
  - `/admin/payments` — payment proof review (Finance only)
  - `/admin/prescriptions` — Rx review queue (Pharmacist only)
  - `/admin/questions` — pharmacist inbox
  - `/admin/requests` — product request CRM
  - `/admin/customers` — customer search (Support)

- [ ] **7.5 — Verify and commit**
  - Test: Finance staff logs in → sees only payment queue → approve payment → order status updates → customer sees update in tracking
  - Test: Pharmacist logs in → sees only Rx queue and Q&A inbox
  - Commit: `feat: add role-based admin web dashboard`

---

### PHASE 8 — Payments (after safe review)
**Goal:** Enable web payment flows after verifying bank details, Flutterwave config, and crypto wallets are all set in Railway env.
**Risk:** High — money involved. Do NOT enable in production until all env vars verified and checkout flow is tested.

**Payment methods to implement (in order of safety):**

#### 8A — Bank Transfer Proof Upload (safest)
- Web upload form (uses Phase 0 file storage)
- Customer uploads screenshot → saved to `payments.web_proof_url`
- Staff reviews in Telegram or web admin → approves
- `POST /api/v1/orders/{code}/payment/bank-transfer` — multipart upload

#### 8B — Flutterwave (only if FLUTTERWAVE_SECRET_KEY set)
- `POST /api/v1/orders/{code}/payment/flutterwave` — returns payment link
- Customer completes on Flutterwave page
- Webhook already handles auto-confirmation
- Add Flutterwave redirect URL: `${NEXT_PUBLIC_API_URL}/payment-complete?code={code}`

#### 8C — Crypto (only if CRYPTO_WALLETS set)
- `GET /api/v1/orders/{code}/payment/crypto` — returns available wallets + amounts
- `POST /api/v1/orders/{code}/payment/crypto/submit` — customer submits tx hash
- Staff reviews in Telegram/web admin → two-step confirm

- [ ] **8.1 — Bank transfer upload endpoint**
- [ ] **8.2 — Flutterwave link endpoint**
- [ ] **8.3 — Crypto submit endpoint**
- [ ] **8.4 — Payment status page** (`/orders/{code}/payment`)
- [ ] **8.5 — Verify all Railway env vars before enabling each method**
- [ ] **8.6 — Test with real small transaction (₦100 test) before going live**
- [ ] **Commit per method, deploy, verify, then enable next**

---

### PHASE 9 — Follow-up & Notifications
**Goal:** Customers get email confirmations and follow-ups. Staff get alerts. All via existing SMTP service.
**Risk:** Low — additive only.

- [ ] **9.1 — Order confirmation email** — trigger from `POST /api/v1/orders` (if customer has email)
- [ ] **9.2 — Payment confirmation email** — trigger from payment approval webhook
- [ ] **9.3 — Pharmacist reply email** — trigger when pharmacist answers question
- [ ] **9.4 — Delivery update email** — trigger from logistics webhook
- [ ] **9.5 — Staff alert emails** — trigger for new orders, pending payments, new Rx
- [ ] **9.6 — Customer follow-up** — existing APScheduler job already handles 24h follow-up

All use existing `app/services/email.py` — no new SMTP code needed, just call it from new places.

---

### PHASE 10 — Influencer & Referral Tracking
**Goal:** Unique referral links for influencers. UTM tracking. Lead attribution. Commission rules. Dashboard later.
**Risk:** Low — additive only, no payment automation.

**New DB tables needed:**
```sql
CREATE TABLE referral_campaigns (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    influencer_name VARCHAR NOT NULL,
    slug VARCHAR UNIQUE NOT NULL,  -- e.g., "drngozi"
    utm_source VARCHAR,
    promo_code VARCHAR UNIQUE,
    discount_pct NUMERIC(5,2) DEFAULT 0,
    commission_pct NUMERIC(5,2) DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE referral_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    campaign_id UUID REFERENCES referral_campaigns(id),
    event_type VARCHAR NOT NULL,  -- 'click', 'lead', 'order'
    customer_id UUID REFERENCES customers(id) NULL,
    order_id UUID REFERENCES orders(id) NULL,
    ip_hash VARCHAR,  -- hashed for privacy
    referrer VARCHAR,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE orders ADD COLUMN campaign_id UUID REFERENCES referral_campaigns(id) NULL;
ALTER TABLE customers ADD COLUMN referred_by_campaign_id UUID REFERENCES referral_campaigns(id) NULL;
```

- [ ] **10.1 — Referral link middleware** — `/?ref=drngozi` → logs `referral_events.click` → sets `ref` cookie (30 day)
- [ ] **10.2 — Apply referral to customer** — on customer creation, check `ref` cookie → link to campaign
- [ ] **10.3 — Apply promo code at checkout** — validate code → apply discount → store `campaign_id` on order
- [ ] **10.4 — Track conversions** — on order creation, log `referral_events.order` if customer has campaign
- [ ] **10.5 — Influencer report API** — `GET /api/v1/admin/campaigns/{id}/report` (admin only)
- [ ] **10.6 — Admin campaign dashboard** — `/admin/campaigns` — clicks, leads, orders, commission owed

---

## SECTION 4 — RISKS & BLOCKERS

| # | Risk | Severity | Mitigation |
|---|------|----------|------------|
| R01 | **File storage gap** — prescriptions + payment proofs use Telegram file_ids; web can't use those | **HIGH** | Phase 0 adds `web_file_url` columns + Supabase Storage service before any upload feature |
| R02 | **No REST API exists** — 100% of logic is in Telegram handlers | **HIGH** | All phases build the API layer; never duplicate logic — call existing services |
| R03 | **No customer auth** — customers identified by Telegram ID only | **HIGH** | Phase 1 adds phone-based session token; Phase 2 can add OTP verification |
| R04 | **No CORS** — Railway blocks Vercel by default | **HIGH** | Phase 0.1 is CORS setup; gate checked before Phase 1 |
| R05 | **Cart is in-memory FSM** — bot cart resets on restart | **MEDIUM** | Phase 5 adds `web_carts` table; Telegram bot uses its own FSM, web uses DB |
| R06 | **Payment risk** — live payment with wrong env vars = broken checkout | **HIGH** | Phase 8 explicitly checks all env vars; test with small transaction first |
| R07 | **Rx compliance risk** — web must not imply automatic prescription approval | **HIGH** | Disclaimer text on every Rx-related page; no auto-approval language; pharmacist review required |
| R08 | **Vercel ↔ Railway connectivity** — env var `NEXT_PUBLIC_API_URL` must be set | **MEDIUM** | Phase 0.6 sets this; verify with health check before Phase 1 |
| R09 | **Deployment risk** — wrong Vercel project deployed | **HIGH** | Always run `cat web/.vercel/project.json` before any Vercel deploy |
| R10 | **Domain not pointed** — peacewayonline.com not yet on Vercel | **MEDIUM** | Phase 0 completes domain setup; landing page must not break during transition |
| R11 | **Missing env vars on Railway** — SMTP, Supabase, etc. not yet set | **MEDIUM** | Each phase lists required env vars; don't enable features before vars are set |
| R12 | **Medical/compliance wording** — web must not make treatment claims | **MEDIUM** | Review every page before shipping; no "cure", "treat", "diagnose" language |
| R13 | **OCR/scan not fully integrated** — `services/ocr/` has stubs | **LOW** | Not needed for web; skip until staff requests it |
| R14 | **Logistics API keys not set** — only manual rider assignment works | **LOW** | Manual delivery is fine; Phase 2 adds partner APIs only when needed |

---

## SECTION 5 — SAFEST FIRST FEATURE (RECOMMENDATION)

**Recommended: Phase 2 — Product Availability Request form**

Reasoning:
- ✅ Reuses `services/product_requests.py` exactly as-is
- ✅ No file uploads needed
- ✅ No payment involved
- ✅ No auth required (phone number as identifier)
- ✅ Staff can action immediately in existing Telegram panel (nothing changes for them)
- ✅ Zero risk of breaking the landing page (new page at `/request`)
- ✅ Highest business value: captures demand for medicines Peaceway doesn't yet stock

**But Phase 0 (CORS + API skeleton) must be done first.** That is a ~2 hour task, not a feature.

If Phase 0 is already done, then Phase 2 is the safest first feature. If Phase 0 is not done, then Phase 0 is the first task.

---

## SECTION 6 — ENVIRONMENT VARIABLE CHECKLIST (before each phase)

| Phase | Required Env Vars (Railway) | Required Env Vars (Vercel) |
|-------|---------------------------|---------------------------|
| Phase 0 | `ALLOWED_ORIGINS`, `WEB_SECRET` | `NEXT_PUBLIC_API_URL` |
| Phase 1 | (same as 0) | (same as 0) |
| Phase 2 | (same as 0) | (same as 0) |
| Phase 3 | (same as 0) | (same as 0) |
| Phase 4 | `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`, `SUPABASE_STORAGE_BUCKET` | (same as 0) |
| Phase 5 | (same as 4) | (same as 0) |
| Phase 6 | (same as 0) | (same as 0) |
| Phase 7 | (same as 0) | (same as 0) |
| Phase 8A | `BANK_ACCOUNTS` (verify) | (same as 0) |
| Phase 8B | `FLUTTERWAVE_SECRET_KEY`, `FLUTTERWAVE_PUBLIC_KEY`, `FLUTTERWAVE_WEBHOOK_HASH` | `NEXT_PUBLIC_FLUTTERWAVE_PUBLIC_KEY` |
| Phase 8C | `CRYPTO_WALLETS` | (same as 0) |
| Phase 9 | `SMTP_HOST`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_FROM_EMAIL` | (same as 0) |
| Phase 10 | (same as 0) | (same as 0) |

---

## SECTION 7 — DECISION LOG (not to be changed without user approval)

| Decision | Rationale |
|----------|-----------|
| Telegram bot stays unchanged | Web is additional channel; existing bot users must not be disrupted |
| Phone-based customer identity | Matches existing customer records; no new user table needed |
| Existing services reused directly | Single source of truth; no logic duplication |
| Supabase Storage for web uploads | Avoids Telegram file_id dependency; free tier adequate for launch |
| No OTP in Phase 1 | Reduces friction for lead capture; add OTP in Phase 1.5 if fraud is observed |
| B2B / wholesale excluded | Per explicit user instruction |
| No medical claims | Per explicit user instruction + pharmacy compliance |
| Payments last (Phase 8) | De-risk: validate full checkout flow before enabling money movement |
| Staff web dashboard after customer features | Can't admin what doesn't exist yet |

---

*Plan created: 2026-07-01*
*Based on: full inspection of C:\Projects\peaceway-online as of 2026-07-01*
*Inspection agent: Explore subagent, 67 tool uses, 99,691 tokens*
