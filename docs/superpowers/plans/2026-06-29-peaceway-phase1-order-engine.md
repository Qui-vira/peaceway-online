# Peaceway Online — Phase 1 (Order Engine) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a working Telegram order engine for Peaceway Pharmacy — browse/search a catalog imported from PharmaOS, cart + checkout with delivery zones, profit-protected pricing, Flutterwave + manual bank-proof payments, role-based staff operations with DM+email alerts, full order status tracking, and a 24h follow-up — all on its own PostgreSQL, deployable to Railway.

**Architecture:** Standalone aiogram 3 bot run in webhook mode inside a FastAPI app (single Railway web service). SQLAlchemy 2.0 async + asyncpg, Alembic migrations, APScheduler for follow-ups. PharmaOS is read-only import source only — no runtime dependency. Manual rider assignment + manual delivery status in P1; logistics provider interface stubbed (ManualProvider) for P2.

**Tech Stack:** Python 3.12+, aiogram 3.x, FastAPI, SQLAlchemy 2.0 (async), asyncpg, Alembic, APScheduler, structlog, httpx (Flutterwave), aiosmtplib (email), pytest + pytest-asyncio.

---

## File Structure

```
peaceway-online/
├── app/
│   ├── __init__.py
│   ├── main.py                     # FastAPI app, webhook wiring, lifespan, /health
│   ├── core/
│   │   ├── config.py               # pydantic-settings; all env vars; role-ID parsing
│   │   ├── db.py                    # async engine, session factory, get_session
│   │   ├── logging.py               # structlog config
│   │   └── security.py              # role resolution from telegram_id, require_role
│   ├── models/
│   │   ├── base.py                  # Base, TimestampMixin
│   │   ├── catalog.py               # Product, ProductAlias, ProductPricing
│   │   ├── orders.py                # Customer, Order, OrderItem, OrderStatusHistory, enums
│   │   ├── payments.py              # Payment, PaymentWebhookEvent
│   │   ├── ops.py                   # Staff, FeeSetting, DeliveryZone, PharmacistQuestion, Prescription, AuditLog
│   │   └── logistics.py             # logistics tables (created now, used P2)
│   ├── services/
│   │   ├── pricing.py               # quote_order(): profit-protected totals
│   │   ├── catalog.py               # search, get_product, listing rules
│   │   ├── orders.py                # create/transition orders, status history
│   │   ├── alerts.py                # send_staff_alert (Telegram DM + email fallback)
│   │   ├── email.py                 # aiosmtplib sender
│   │   ├── rx_classifier.py         # heuristic Rx classification
│   │   └── payments/flutterwave.py  # init payment, verify webhook signature
│   ├── bot/
│   │   ├── dispatcher.py            # Bot, Dispatcher, router registration
│   │   ├── keyboards/customer.py    # inline/reply keyboards
│   │   ├── keyboards/staff.py
│   │   ├── customer/menu.py         # /start, welcome, main menu
│   │   ├── customer/catalog.py      # search, browse, product card
│   │   ├── customer/cart.py         # cart FSM, qty
│   │   ├── customer/checkout.py     # delivery details FSM, totals, confirm
│   │   ├── customer/payment.py      # instructions, proof upload
│   │   ├── customer/support.py      # ask pharmacist, speak to human, delivery areas
│   │   ├── staff/panel.py           # role-gated admin menu, /myid
│   │   ├── staff/orders.py          # order actions (approve/reject/package/dispatch...)
│   │   └── staff/pricing_admin.py   # edit prices, fees, zones, stock
│   ├── webhooks/
│   │   ├── telegram.py              # POST /webhook/telegram
│   │   └── flutterwave.py           # POST /webhook/flutterwave
│   └── scheduler/jobs.py            # 24h follow-up
├── scripts/
│   ├── import_pharmaos.py           # read-only export + normalize + load
│   └── seed_zones.py                # Lagos zones + default fees
├── alembic/ (env.py, versions/)
├── tests/
├── .env.example  Procfile  railway.json  pyproject.toml  alembic.ini  README.md
```

---

## Milestone P1.0 — Scaffold & tooling

### Task 1: Project skeleton & dependencies
**Files:** Create `pyproject.toml`, `.env.example`, `.gitignore`, `app/__init__.py`, package `__init__.py` files.
- [ ] Create `pyproject.toml` with deps: aiogram>=3.13, fastapi, uvicorn[standard], sqlalchemy[asyncio]>=2.0, asyncpg, alembic, pydantic-settings, structlog, httpx, aiosmtplib, apscheduler, python-dotenv; dev: pytest, pytest-asyncio, aiosqlite.
- [ ] Create `.env.example` with every env var from spec §13 (empty values, role vars, SMTP, Flutterwave, PHARMAOS_DATABASE_URL, provider keys, WEBHOOK_BASE_URL).
- [ ] Create `.gitignore` (`.env`, `__pycache__`, `*.pyc`, `.venv`, `scripts/exports/`).
- [ ] Create empty `__init__.py` in every package dir.
- [ ] Run: `python -m venv .venv && .venv/Scripts/pip install -e ".[dev]"`. Expected: install succeeds.
- [ ] Commit: `chore: scaffold peaceway-online project`.

### Task 2: Config & logging
**Files:** Create `app/core/config.py`, `app/core/logging.py`; Test `tests/test_config.py`.
- [ ] Write `Settings(BaseSettings)` with fields for all env vars; helper `role_ids(role) -> set[int]` parsing comma-separated IDs; `flutterwave_enabled` etc. toggles.
- [ ] Test: setting `OWNER_TELEGRAM_IDS="111,222"` → `settings.owner_telegram_ids == {111,222}`. Run `pytest tests/test_config.py -v`, expect PASS.
- [ ] structlog config (JSON in prod, console in dev).
- [ ] Commit: `feat: config and logging`.

### Task 3: Async DB layer
**Files:** Create `app/core/db.py`, `app/models/base.py`.
- [ ] `db.py`: async engine from `DATABASE_URL` (coerce `postgresql://`→`postgresql+asyncpg://`), `async_session` factory, `get_session()` context manager.
- [ ] `base.py`: `Base(DeclarativeBase)`, `TimestampMixin` (`created_at`, `updated_at` server defaults).
- [ ] Commit: `feat: async db layer and model base`.

---

## Milestone P1.1 — Data models & migrations

### Task 4: Catalog models
**Files:** Create `app/models/catalog.py`; Test `tests/test_models_catalog.py`.
- [ ] `Product` (fields per spec §7), `ProductAlias` (product_id FK, alias_name, normalized_name idx), `ProductPricing` (product_id unique FK, cost_price, selling_price Numeric(12,2), markup_pct, fixed_profit, stock_qty, is_in_stock). `Product.is_listed` default False.
- [ ] Test (sqlite): create a product + pricing, query back, assert fields. Run pytest, expect PASS.
- [ ] Commit.

### Task 5: Orders models & enums
**Files:** Create `app/models/orders.py`.
- [ ] Enums `OrderStatus`, `RxStatus`, `DeliveryStatus`, `PaymentMethod` (spec §8).
- [ ] `Customer` (telegram_id unique, name, phone, addresses JSON), `Order` (status, rx_status, delivery_status, money columns Numeric(12,2): subtotal/delivery_fee/payment_fee/offramp_fee/handling_fee/total, payment_method, assigned_staff_id, delivery fields), `OrderItem` (order_id, product_id, qty, unit_price, line_total), `OrderStatusHistory`.
- [ ] Commit.

### Task 6: Payments, ops, logistics models
**Files:** Create `app/models/payments.py`, `app/models/ops.py`, `app/models/logistics.py`.
- [ ] `Payment`, `PaymentWebhookEvent`; `Staff` (telegram_id, role enum, email, is_active), `FeeSetting` (singleton row: payment_fee_pct, payment_fee_flat, offramp_fee, handling_fee, enable_bank, enable_flutterwave, enable_crypto), `DeliveryZone` (name, fee, eta_minutes, is_active), `PharmacistQuestion`, `Prescription`, `AuditLog`; logistics tables per spec §12 (created now).
- [ ] Commit.

### Task 7: Alembic init & first migration
**Files:** Create `alembic.ini`, `alembic/env.py` (async), generate `alembic/versions/0001_initial.py`.
- [ ] Configure async Alembic pointing at `Base.metadata`.
- [ ] Run `alembic revision --autogenerate -m "initial schema"`; review tables.
- [ ] Run `alembic upgrade head` against a local Postgres; expect all tables created.
- [ ] Commit: `feat: initial database schema + migration`.

---

## Milestone P1.2 — Catalog import from PharmaOS

### Task 8: Rx heuristic classifier
**Files:** Create `app/services/rx_classifier.py`; Test `tests/test_rx_classifier.py`.
- [ ] `classify(name, generic, dosage_form, category) -> (requires_prescription: bool, requires_review: bool)`. Rules: injections/`Injection`/`Powder for injection`/`Solution for injection` → review; controlled/antibiotic generic name list (e.g. amoxicillin, ciprofloxacin, tramadol, codeine, diazepam) → Rx+review; vaccines → review; simple analgesics/vitamins/ORS → OTC. Default for un-curated → review.
- [ ] Tests: amoxicillin→(True,True); paracetamol tablet→(False,False); any injection→(_,True). Run pytest, expect PASS.
- [ ] Commit.

### Task 9: Import script (read-only PharmaOS → Peaceway)
**Files:** Create `scripts/import_pharmaos.py`.
- [ ] Connect to `PHARMAOS_DATABASE_URL` (default to the discovered local URL) **read-only**; `SELECT` products + aliases only; write `scripts/exports/products_<ts>.csv`.
- [ ] Normalize names (trim, collapse spaces), map categories → Peaceway categories, run `rx_classifier`, upsert into Peaceway `products`/`product_aliases` **matching on `nafdac_number`**; never touch `ProductPricing` for existing rows (idempotent `/resync`). Set `is_listed=False`, no price.
- [ ] Dry-run mode prints counts (found/new/updated/skipped) before writing; `--commit` to persist.
- [ ] Run dry-run; expect ~8,583 products reported. Commit.

### Task 10: Seed delivery zones + fee settings
**Files:** Create `scripts/seed_zones.py`.
- [ ] Insert zones: Igando, Lekki, Agodo, Ikotun, Egbeda, Isheri, Iyana Ipaja, Idimu, Egbe, Ejigbo, Other Lagos (default fees + eta editable later). Insert singleton `FeeSetting` (payment_fee defaults, toggles: bank+flutterwave on, crypto off).
- [ ] Run; expect 11 zones + 1 fee row. Commit.

---

## Milestone P1.3 — Pricing engine (TDD core)

### Task 11: Pricing service
**Files:** Create `app/services/pricing.py`; Test `tests/test_pricing.py`.
- [ ] `quote_order(items, zone, fee_settings, payment_method) -> Quote` where
  `subtotal = Σ selling_price*qty`, `delivery_fee = zone.fee`, `payment_fee = flat or pct*subtotal`, `offramp_fee = settings.offramp_fee if crypto else 0`, `handling_fee = settings.handling_fee`, `total = subtotal+delivery+payment+offramp+handling`. Fees additive — never reduce profit.
- [ ] Tests: (a) 2×₦1000 + zone ₦1500 + 1.5% payment fee → subtotal 2000, payment 30, total 3500; (b) crypto adds offramp; (c) profit = Σ(selling-cost)*qty unaffected by fees. Run pytest, expect PASS.
- [ ] Commit.

---

## Milestone P1.4 — Bot foundation & customer ordering

### Task 12: Bot/dispatcher + FastAPI webhook + /health
**Files:** Create `app/bot/dispatcher.py`, `app/webhooks/telegram.py`, `app/main.py`.
- [ ] Build `Bot`, `Dispatcher`, register routers. FastAPI lifespan sets Telegram webhook to `WEBHOOK_BASE_URL/webhook/telegram` (or polling fallback if unset for local dev). `/health` returns `{"status":"ok"}`.
- [ ] Run `uvicorn app.main:app` locally; curl `/health` → 200. Commit.

### Task 13: Welcome + main menu
**Files:** Create `app/bot/customer/menu.py`, `app/bot/keyboards/customer.py`.
- [ ] `/start`: upsert `Customer`, send exact welcome copy + 6 inline buttons (Order Medicine, Ask the Pharmacist, Check Delivery Areas, Popular Products, Speak to a Human, Track My Order). Back/Main-menu helpers.
- [ ] Manual check against bot; Commit.

### Task 14: Search & browse & product card
**Files:** Create `app/bot/customer/catalog.py`, `app/services/catalog.py`.
- [ ] `search(query)` uses `product_aliases.normalized_name ILIKE` + name; category browse; product card shows name, strength, price (or "Ask pharmacist for price & availability" if unlisted), stock badge, Rx badge. Buyable → Add to Cart; Rx → Upload Prescription/Ask Pharmacist/Cancel.
- [ ] Commit.

### Task 15: Cart & quantity (FSM)
**Files:** Create `app/bot/customer/cart.py`.
- [ ] Add to cart (state stored per user), set/confirm qty, view cart, remove item, proceed to checkout. Stock check on add.
- [ ] Commit.

### Task 16: Checkout — delivery details (FSM)
**Files:** Create `app/bot/customer/checkout.py`.
- [ ] Collect full name, phone, address, **zone picker (inline from DeliveryZone)**, landmark, preferred time, note. Then call `pricing.quote_order`, show itemized totals (subtotal, delivery, payment fee, total) + Confirm/Back/Cancel.
- [ ] Commit.

### Task 17: Order creation + status
**Files:** Create `app/services/orders.py`.
- [ ] `create_order(...)` persists Order+items+initial status (NEW→AWAITING_PAYMENT for OTC; PRESCRIPTION_REQUIRED if cart has Rx items). `transition(order, new_status, by)` writes `OrderStatusHistory`. Reserve stock.
- [ ] Tests `tests/test_orders.py`: OTC order → AWAITING_PAYMENT; Rx item → PRESCRIPTION_REQUIRED. Commit.

---

## Milestone P1.5 — Payments

### Task 18: Manual bank transfer + proof upload
**Files:** Create `app/bot/customer/payment.py`, `app/models` already have Payment.
- [ ] Show bank details from env (`BANK_*`). Customer uploads photo → store Telegram `file_id` in `Payment` (status PENDING), set order PAYMENT_SUBMITTED, fire staff alert.
- [ ] Commit.

### Task 19: Flutterwave init + webhook
**Files:** Create `app/services/payments/flutterwave.py`, `app/webhooks/flutterwave.py`.
- [ ] `init_payment(order)` → httpx call to Flutterwave standard, returns payment link (only if `enable_flutterwave`). Webhook verifies `verif-hash` against `FLUTTERWAVE_WEBHOOK_HASH`, stores `PaymentWebhookEvent`, on `successful` → order PAYMENT_APPROVED + alerts.
- [ ] Test signature verification with a sample payload. Commit.

---

## Milestone P1.6 — Staff ops, roles, alerts

### Task 20: Role security
**Files:** `app/core/security.py`; Test `tests/test_security.py`.
- [ ] `resolve_role(telegram_id) -> Role|None` from env sets (Owner/Pharmacist/Packaging/Dispatcher/Support). `require_role(*roles)` guard for handlers.
- [ ] Tests: owner id → OWNER; unknown id → None. Commit.

### Task 21: Email + alert service
**Files:** Create `app/services/email.py`, `app/services/alerts.py`; Test `tests/test_alerts.py`.
- [ ] `email.send(to, subject, body)` via aiosmtplib. `send_staff_alert(order, audience)` → Telegram DM to each role id + email; DM-fail → still email, email-fail → still DM, both logged. Audience routing: Owner=all, Pharmacist=Rx, Packaging=paid, Dispatcher=ready, Support=help.
- [ ] Tests with mocked bot/SMTP: DM raises → email still called. Commit.

### Task 22: Staff panel + /myid + order actions
**Files:** Create `app/bot/staff/panel.py`, `app/bot/staff/orders.py`.
- [ ] `/myid` returns numeric id (all users). Staff menu shows only role-permitted buttons. Order action buttons (Approve/Reject Payment, Start Packaging, Ready for Dispatch, Assign Rider [manual], Mark Dispatched, Mark Delivered, Cancel, Message Customer) each transition status, write AuditLog, notify customer. Automation: OTC + PAYMENT_APPROVED → auto PROCESSING; Rx never auto-dispatch.
- [ ] Commit.

### Task 23: Pricing/fees/stock admin + prescriptions
**Files:** Create `app/bot/staff/pricing_admin.py`.
- [ ] Owner: update selling_price/markup/fixed_profit, set stock, edit zone fees, edit payment/handling fee, toggle payment methods, mark product OTC/Rx. Pharmacist: review prescriptions/Rx orders → APPROVED_FOR_PAYMENT / REJECTED_BY_PHARMACIST. All write AuditLog.
- [ ] Commit.

---

## Milestone P1.7 — Scheduler & deploy

### Task 24: 24h follow-up
**Files:** Create `app/scheduler/jobs.py`; wire into `main.py` lifespan.
- [ ] On DELIVERED, schedule APScheduler job (+24h) sending follow-up copy + buttons (Everything is okay / I need help / Speak to a pharmacist). Persist jobstore in Postgres so restarts survive.
- [ ] Commit.

### Task 25: Railway deploy artifacts + README
**Files:** Create `Procfile`, `railway.json`, finalize `README.md`.
- [ ] `Procfile`: `web: alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT`. `railway.json` build/start. README: env setup, `import_pharmaos.py`, `seed_zones.py`, webhook setup, **rotate bot token via @BotFather** note.
- [ ] Commit: `feat: railway deployment artifacts`.

---

## Self-Review notes

- Spec §3 gaps (no prices/Rx) handled by Task 8/9 (classifier + unlisted import) and Task 14 ("ask pharmacist" card).
- Spec §9 pricing fully covered by Task 11 with profit-invariance test.
- Spec §11 roles/alerts covered by Tasks 20–22; DM↔email fallback in Task 21.
- Spec §12 logistics: tables created Task 6, ManualProvider behavior in Task 22 (Assign Rider manual); full provider APIs deferred to P2 by design.
- All money columns Numeric(12,2); status changes always via `orders.transition` (Task 17).
