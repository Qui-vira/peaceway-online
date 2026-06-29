# Peaceway Online

A 24/7 Telegram ordering + pharmacy-operations bot for **Peaceway Pharmacy**
(Igando/Agodo Ikotun, Lagos). Customers browse and order medicines; staff manage
payments, packaging, dispatch, and prescriptions — all from Telegram.

Bot: [@Peacewayonline_bot](https://t.me/Peacewayonline_bot)

## Stack
Python 3.11 · aiogram 3 · FastAPI (webhook mode) · SQLAlchemy 2 async · asyncpg ·
Alembic · APScheduler · Flutterwave + manual bank transfer · Railway + PostgreSQL.

## Architecture
Standalone service with its **own** PostgreSQL. PharmaOS is used only as a one-time
(or on-demand) **import source** — the bot never depends on PharmaOS at runtime.
See `docs/superpowers/specs/` and `docs/superpowers/plans/` for the full design.

## Local setup
```bash
py -3.11 -m venv .venv
./.venv/Scripts/pip install -e ".[dev]"
cp .env.example .env            # then fill in values
alembic upgrade head            # create schema
python scripts/import_pharmaos.py --commit   # import catalog from PharmaOS (read-only)
python scripts/seed_zones.py                 # Lagos delivery zones + fee settings
python scripts/seed_demo_listing.py          # (optional) price a few OTC items to test ordering
python -m app.run_polling        # run the bot locally (long-polling)
pytest -q                        # run tests
```

## Environment variables
See [`.env.example`](.env.example). Key groups:
- **Telegram:** `TELEGRAM_BOT_TOKEN`, `WEBHOOK_BASE_URL`
- **Databases:** `DATABASE_URL` (Peaceway), `PHARMAOS_DATABASE_URL` (import only)
- **Bank transfer:** `BANK_ACCOUNT_NAME`, `BANK_ACCOUNT_NUMBER`, `BANK_NAME`
- **Flutterwave:** `FLUTTERWAVE_SECRET_KEY`, `FLUTTERWAVE_PUBLIC_KEY`, `FLUTTERWAVE_WEBHOOK_HASH`
  (Flutterwave auto-disables until keys are set; manual bank transfer always works.)
- **Staff roles (numeric Telegram IDs, comma-separated):** `OWNER_TELEGRAM_IDS`,
  `PHARMACIST_TELEGRAM_IDS`, `PACKAGING_STAFF_TELEGRAM_IDS`, `DISPATCHER_TELEGRAM_IDS`,
  `SUPPORT_TELEGRAM_IDS`
- **Staff emails + SMTP:** `*_EMAILS`, `SMTP_*`
- **Optional:** `STAFF_GROUP_CHAT_ID`, logistics provider keys (Phase 2)

### Getting staff Telegram IDs
Each staff member must open the bot, press **/start**, then send **/myid** — the bot
replies with their numeric ID. Add those IDs to the role env vars. (Telegram cannot
DM a user who has never started the bot.)

## Deploy to Railway
1. Create a Railway project and add a **PostgreSQL** plugin (sets `DATABASE_URL`).
2. Add all env vars from `.env.example`.
3. Set `WEBHOOK_BASE_URL` to your Railway public URL (e.g. `https://<app>.up.railway.app`).
4. Deploy. The start command runs migrations then launches the webhook app:
   `alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT`.
5. Health check: `GET /health` → `{"status":"ok"}`.
6. Run the catalog import once (Railway shell or locally pointed at the Railway DB):
   `python scripts/import_pharmaos.py --commit && python scripts/seed_zones.py`.

## ⚠️ Security
The bot token was shared in plain text during setup. **Rotate it via @BotFather**
(`/revoke`) before launch and store the new token only in Railway env vars.

## Order lifecycle
`NEW → AWAITING_PAYMENT → PAYMENT_SUBMITTED → PAYMENT_APPROVED → PROCESSING →
DISPATCHED → DELIVERED` (+ `CANCELLED`, `REJECTED`). Prescription orders go through
pharmacist review (`PRESCRIPTION_REQUIRED → … → APPROVED_FOR_PAYMENT`) before payment.
OTC orders auto-advance to `PROCESSING` once payment is approved; prescription orders
never auto-dispatch.

## Pricing
Delivery, payment, off-ramp, and handling fees are always **added on top** of the
product price and never reduce product profit. All fees are admin-editable.

## Phases
- **Phase 1:** ordering, pricing, payments (bank proof), staff ops, alerts, follow-up. ✅
- **Phase 2:** logistics provider framework (Manual working; Kwik/Fez/Gokada/Custom
  credential-gated against their **official** APIs), "Track My Order", `/webhook/logistics`,
  GPS→Telegram map / tracking-link button. ✅
  - To enable a partner: add its API key env var, then implement the three methods in
    `app/services/delivery/providers/api.py` against the partner's official API docs, and
    re-run `python scripts/seed_providers.py`.
- **Phase 3:** payment-method chooser, Flutterwave (official Standard API + verified
  webhook, auto-disabled until keys set), optional crypto off-ramp with manual on-chain +
  Naira settlement confirmation. ✅
  - Crypto stays disabled until you set `enable_crypto` (admin) **and** `CRYPTO_WALLETS`.

### Extra seed/setup scripts
```bash
python scripts/seed_providers.py       # register logistics providers (manual enabled)
python scripts/seed_demo_listing.py    # price a few OTC items for testing
```
