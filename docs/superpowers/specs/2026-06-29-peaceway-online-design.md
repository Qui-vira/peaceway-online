# Peaceway Online — Telegram Pharmacy Ordering Bot — Design Spec

**Date:** 2026-06-29
**Status:** Approved (build started)
**Business:** Peaceway Pharmacy, Igando/Agodo Ikotun, Lagos, Nigeria
**Bot:** @Peacewayonline_bot

---

## 1. Goal

A 24/7 Telegram order engine + pharmacy operations system: ordering, customer support,
pharmacist questions, payment confirmation, delivery/logistics tracking, role-based staff
operations, and admin management. Production-grade, not a toy bot.

## 2. Locked decisions

- **Architecture:** Standalone project, its own PostgreSQL on Railway. PharmaOS is used
  **only** as an import source. Peaceway must run even if PharmaOS is down. No runtime
  dependency on PharmaOS.
- **Product data source:** PharmaOS Postgres at `localhost:5432/pharmaos`. Connect
  **read-only**, never modify it. Import is offline/on-demand with an idempotent `/resync`.
- **Payments:** Flutterwave (keys from PharmaOS `.env`) + manual bank transfer with proof
  upload. **No Paystack.** Crypto off-ramp is a future, optional, manual-settlement module.
- **Bank details & fees:** env/DB placeholders, all admin-editable from Telegram. Nothing
  hardcoded.
- **Admin access:** locked to numeric Telegram user IDs via role env vars. Alerts via
  Telegram DM + email. Private staff group optional (`STAFF_GROUP_CHAT_ID`). `/myid` helper.
  Staff must `/start` the bot before it can DM them.
- **Logistics:** official partner APIs only — no scraping, no reverse-engineering of private
  APIs. Provider interface; each provider disabled until valid API credentials exist. Manual
  dispatcher is the working fallback.
- **Sellable items (default):** import all ~8,583 products as searchable; curated priced +
  in-stock items are buyable; unpriced items show "Ask pharmacist for price & availability."
- **Rx safety (default):** heuristic auto-classification of likely-Rx items (injections,
  antibiotics, controlled-substance name list, etc.) → "pharmacist review required";
  pharmacist refines flags from Telegram. No diagnosis or dosage advice from the bot.

## 3. PharmaOS data reality (inspected 2026-06-29, read-only)

- `products`: **8,583** rows, all active. generic_name 100%, manufacturer 100%,
  nafdac_number ~100%, brand_name 93%, dosage_form 89%, strength 85%.
- `product_aliases`: 8,583 (1:1 normalized names — used for bot search).
- Categories: Drugs (7,102), Medical devices (1,092), Vaccines/Biologics (152),
  Herbals/Nutraceuticals (129), Veterinary (97), N/A (11).
- **Prices/stock: only 6 rows** in `inventory` (test data). → Peaceway sets its own prices/stock.
- **Prescription flags: none** (`requires_prescription = 0` for all). → classification needed.

## 4. Stack

- **aiogram 3.x** (async, inline keyboards + FSM).
- **FastAPI** in webhook mode hosting the Telegram webhook + Flutterwave + logistics webhooks;
  one Railway web service; `/health` check.
- **SQLAlchemy 2.0 async + asyncpg**, **Alembic** migrations.
- **APScheduler** (Postgres jobstore) for 24h follow-up + delivery polling.
- `structlog` structured logging. All secrets via env.

## 5. Phasing

- **P1 — Order Engine:** catalog import + resync, customer browse/search/cart/checkout,
  delivery address + zone + fee, pricing engine, Flutterwave + manual bank proof, staff
  alerts (DM + email), role-based admin/staff panels, order statuses + history, 24h follow-up,
  manual rider assignment + manual delivery status.
- **P2 — Logistics API:** provider interface (Manual/Kwik/Fez/Gokada/Custom, official APIs
  only, disabled until credentialed), quotes, booking, webhooks, GPS→Telegram map/live
  location, "Track My Order".
- **P3 — Crypto off-ramp:** optional wallet/network/token, tx-hash collection, off-ramp fee,
  admin Naira-settlement confirmation. Legally cautious, manual.

The **full schema is created up front**; code lands phase by phase.

## 6. Project structure

```
peaceway-online/
├── app/
│   ├── bot/{customer,staff,keyboards}   # aiogram handlers, FSM, inline/reply keyboards
│   ├── core/                            # config(env), db, logging, security(role gating)
│   ├── models/                          # SQLAlchemy models (all tables)
│   ├── services/                        # pricing, orders, alerts, catalog_sync,
│   │                                    #   payments/flutterwave, delivery/providers/*
│   ├── webhooks/                        # telegram, flutterwave, logistics
│   └── scheduler/                       # follow-ups, delivery polling
├── scripts/import_pharmaos.py  scripts/seed_zones.py
├── alembic/  tests/
├── .env.example  Procfile  railway.json  pyproject.toml  README.md
```

## 7. Database schema (Peaceway's own DB)

**Catalog/pricing:** `products` (name, generic_name, brand_name, dosage_form, strength,
manufacturer, nafdac_number, category, requires_prescription, controlled_substance,
requires_review, is_listed), `product_aliases`, `product_pricing` (cost_price, selling_price,
markup_pct, fixed_profit, stock_qty, is_in_stock).

**Customers/orders:** `customers` (telegram_id, name, phone, addresses), `orders` (status,
subtotal, delivery_fee, payment_fee, offramp_fee, handling_fee, total, payment_method,
assigned_staff_id), `order_items`, `order_status_history`.

**Pricing config:** `fee_settings` (payment_fee_pct/flat, offramp_fee, handling_fee, toggles
bank/flutterwave/crypto), `delivery_zones` (area, fee, eta_minutes, is_active).

**Payments:** `payments` (method, amount, proof_file_id, status, verified_by),
`payment_webhook_events`.

**Staff/safety:** `staff` (telegram_id, role, email), `pharmacist_questions`, `prescriptions`,
`audit_logs`.

**Delivery/logistics (created now, used P2):** `logistics_providers`, `delivery_quotes`,
`delivery_orders`, `delivery_tracking_events`, `rider_assignments`, `tracking_links`,
`delivery_webhook_events`.

Every important table has `created_at` / `updated_at`.

## 8. Order statuses

Core: `NEW → AWAITING_PAYMENT → PAYMENT_SUBMITTED → PAYMENT_APPROVED → PROCESSING →
DISPATCHED → DELIVERED`, plus `CANCELLED`, `REJECTED`.
Rx: `PRESCRIPTION_REQUIRED → PRESCRIPTION_UPLOADED → PHARMACIST_REVIEW →
APPROVED_FOR_PAYMENT / REJECTED_BY_PHARMACIST`.
Delivery sub-status: `PACKAGING → READY_FOR_DISPATCH → RIDER_ASSIGNED → PICKED_UP →
IN_TRANSIT → NEAR_CUSTOMER → DELIVERED / FAILED_DELIVERY / RETURNED_TO_PHARMACY`.
Every change writes `order_status_history`.

## 9. Pricing engine (profit-protected)

```
product_subtotal = selling_price × qty       # selling_price = cost + markup_pct OR cost + fixed_profit
delivery_fee     = zone.fee                   # on top
payment_fee      = order-level (% or flat)    # on top
offramp_fee      = crypto only (P3)           # on top
handling_fee     = optional                   # on top
customer_total   = subtotal + delivery + payment + offramp + handling
```

Fees are **never** deducted from product profit — they are additive lines the customer pays.
All fee values in `fee_settings` / `delivery_zones`, editable from the Telegram admin panel.

## 10. Customer flow

`/start` → welcome (exact copy below) → 6 buttons: Order Medicine, Ask the Pharmacist, Check
Delivery Areas, Popular Products, Speak to a Human, Track My Order.

Order path: search/browse → product card (price/stock/Rx badge) → qty → cart → checkout →
delivery details (name, phone, address, **zone picker**, landmark, preferred time, note) →
totals breakdown → confirm → payment instructions → upload proof → "awaiting approval" → live
status updates → 24h follow-up. Rx items: "requires pharmacist review" + Upload Prescription /
Ask Pharmacist / Cancel. Back / Cancel / Main-menu on every step.

Welcome copy:
> Welcome to Peaceway Online.
> Your licensed pharmacy in Igando is now online and delivering across Lagos.
> What do you need today?

## 11. Staff roles & alerts

Roles via env (`OWNER_TELEGRAM_IDS`, `PHARMACIST_TELEGRAM_IDS`, `PACKAGING_STAFF_TELEGRAM_IDS`,
`DISPATCHER_TELEGRAM_IDS`, `SUPPORT_TELEGRAM_IDS`). Each role sees only its buttons. Owner = all.
Pharmacist = Rx review. Packaging = paid orders. Dispatcher = ready-for-dispatch. Support =
customer help.

On each paid order: Telegram DM + email to the right role(s). DM-fail → still email; email-fail
→ still DM; both logged. `/myid` returns numeric ID; staff must `/start` first.
`STAFF_GROUP_CHAT_ID` optional.

Automation: OTC + payment approved → auto-`PROCESSING`; Rx → pharmacist review first; never
auto-dispatch Rx.

Staff action buttons: Approve Payment, Reject Payment, Start Packaging, Ready for Dispatch,
Assign Rider, Mark Dispatched, Mark Delivered, Cancel Order, Message Customer.

## 12. Delivery / logistics (official APIs only)

`LogisticsProvider` interface: `estimate_fee`, `create_delivery` (pickup, dropoff, customer
phone, package description), `get_status` / webhook (status, rider assignment, rider phone,
GPS if provided), `cancel`, `tracking_url`.

Providers: `ManualProvider` (P1 default) then `Kwik/Fez/Gokada/Custom` (P2, **official APIs
only**, each disabled until valid credentials in env). Display: GPS → Telegram map/live
location; tracking link only → "Track Order" button; no API → manual staff buttons.
Customers see only status/ETA/map/link/support — never private rider data.

## 13. Env vars

`TELEGRAM_BOT_TOKEN`, `DATABASE_URL`, `PHARMACY_NAME`, `BANK_ACCOUNT_NAME`,
`BANK_ACCOUNT_NUMBER`, `BANK_NAME`, `FLUTTERWAVE_SECRET_KEY`, `FLUTTERWAVE_PUBLIC_KEY`,
`FLUTTERWAVE_WEBHOOK_HASH`, role ID vars, role email vars, `SMTP_*`, `STAFF_GROUP_CHAT_ID`
(optional), `PHARMAOS_DATABASE_URL` (import only), provider API keys (`KWIK_API_KEY`, etc.),
`WEBHOOK_BASE_URL`.

## 14. Risks & safety

- No medical advice/diagnosis; Rx gated on pharmacist review; serious symptoms → "see a
  pharmacist / seek urgent care."
- Bot token was shared in plaintext → store only in Railway env and **rotate via @BotFather
  before launch** (owner action).
- Read-only PharmaOS access; idempotent re-sync (match on `nafdac_number`) never overwrites
  admin-set prices/stock.
- Crypto kept manual/optional — no illegal auto settlement; no assumption of instant bank
  settlement without a licensed provider.
- Logistics: official APIs only — no scraping or private-API reverse-engineering.
