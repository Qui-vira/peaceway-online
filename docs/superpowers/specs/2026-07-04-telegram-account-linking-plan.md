# Telegram Account Linking — Plan (No Code Yet)

**Goal:** Allow a logged-in website customer to connect their Telegram account to
their Peaceway web profile, so one customer profile works across the website and
the bot (order updates, request updates, pharmacist replies, reminders later).

**Method:** Official Telegram Login Widget on the normal website. Telegram Mini
App `initData` validation is planned for later, not built now.

**Status:** IMPLEMENTED 2026-07-04 (endpoint is `POST /api/v1/me/telegram-link`,
matching the existing `/me` convention). Remaining: BotFather `/setdomain` and
the later disconnect endpoint + Mini App `initData` support.

---

## Current-State Findings (inspected 2026-07-04)

- `customers.telegram_id` **already exists** — `app/models/orders.py:71`:
  `BigInteger, unique=True, index=True, nullable=True`, with the comment
  "web-only customers have no Telegram account." The unique constraint already
  prevents two customers sharing one Telegram account at the DB level.
- Web customer auth already works: `pw_session` httpOnly cookie →
  `CurrentCustomer` dependency (`app/api/deps.py`), server-side expiry.
- The PWA is a single page at `web/app/app/page.tsx`; it already fetches the
  customer profile via `getMe()` from `web/lib/api/customers.ts`.
- `get_settings().telegram_bot_token` is available server-side (already used by
  the admin OTP fallback in `app/api/v1/admin.py`).
- Bot-first customers already have Customer rows keyed by `telegram_id`, so a
  link attempt can collide with an existing bot-created profile → must be
  blocked, not merged (merging orders/messages/notes is a separate project).

**External prerequisite:** register the site domain with BotFather
(`/setdomain` → `peacewayonline.com`) or the Login Widget will not render.

---

## 1. Database Changes

One Alembic migration, `customers` table only:

| Column | Type | Notes |
|---|---|---|
| `telegram_username` | `String(64)`, nullable | display only, can go stale |
| `telegram_linked_at` | `DateTime(timezone=True)`, nullable | when the link was verified |

No change to `telegram_id` — it already has the right shape and constraints.
(`telegram_photo_url` is optional; skip it — YAGNI until the UI needs an avatar.)

## 2. Backend Endpoint

`POST /api/v1/profile/telegram-link` (router: `app/api/v1/`, service:
`app/services/web_customers.py` or a new `telegram_link.py`)

- **Auth:** `CurrentCustomer` (existing cookie session). 401 if not logged in.
- **Body:** the exact Login Widget payload — `id`, `first_name`, `last_name?`,
  `username?`, `photo_url?`, `auth_date`, `hash`.
- **Verification (server-side only):**
  1. Build the data-check-string: all fields except `hash`, sorted
     alphabetically, joined as `key=value` lines with `\n`.
  2. Key = `SHA256(bot_token)`; compute `HMAC-SHA256(data_check_string, key)`.
  3. Compare to `hash` with `hmac.compare_digest` (constant-time).
  4. Reject if `auth_date` is older than 5 minutes (replay protection).
- **Linking rules:**
  - Another customer row already owns this `telegram_id` → **409** with a clear
    message ("This Telegram account is already connected to another profile —
    contact support."). No silent merging.
  - Current customer already linked to a different `telegram_id` → 409; they
    must disconnect first (disconnect endpoint is a later task).
  - Success → set `telegram_id`, `telegram_username`, `telegram_linked_at`;
    return the updated profile.
- Later (not now): `DELETE /api/v1/profile/telegram-link` to disconnect.

## 3. Frontend

- A "Connect Telegram" card in the profile area of `web/app/app/page.tsx`
  (or a small extracted component `web/components/app/ConnectTelegram.tsx`).
- Embeds the official widget script
  (`data-telegram-login="Peacewayonline_bot"`, `data-onauth` callback) which
  hands the signed payload to JS; the callback POSTs it to the endpoint via the
  existing fetch helper (cookie included).
- States: not linked (show button) / linked (show `@username` + linked date) /
  error (409 message). `CustomerProfile` type gains `telegram_username`.
- Keep phone/email as the primary profile identity — Telegram is an add-on
  channel, not a replacement.

## 4. Security Checks

- Hash verification and `auth_date` freshness on the server; never trust the
  browser payload by itself.
- `hmac.compare_digest` for the hash comparison.
- DB unique constraint on `telegram_id` is the last line of defence against a
  race between two link attempts.
- Rate-limit the endpoint (same pattern as OTP endpoints) to stop hash-guessing.
- Log link/unlink events (reuse the `CustomerContactEvent` append-only pattern
  or `admin_activity_logs`-style audit) so support can untangle disputes.
- Future Mini App: validate `initData` server-side with the documented HMAC
  scheme; never read `initDataUnsafe`.

## 5. Safest Build Order

1. Migration: add `telegram_username`, `telegram_linked_at`.
2. Service function `verify_telegram_login(payload) -> telegram_user | None`
   with unit tests (valid hash, tampered hash, stale `auth_date`).
3. Endpoint with the linking rules + tests (success, 409 duplicate, 401).
4. BotFather `/setdomain`, then the frontend Connect card.
5. Manual E2E: link a real account, confirm the bot recognises the customer.
6. Later: disconnect endpoint, then Mini App `initData` support.
