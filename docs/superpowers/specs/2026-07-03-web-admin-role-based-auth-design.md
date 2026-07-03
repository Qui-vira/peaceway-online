# Web Admin Role-Based Auth — Design Spec
**Date:** 2026-07-03  
**Status:** Approved

## Problem
The web admin panel at `/admin` uses a single shared `ADMIN_WEB_PASSWORD`. There are no individual identities, no roles, and no way to show staff only the sections relevant to their job.

## Goal
Replace the shared password with Telegram-bridge OTP auth. Each web admin logs in by proving they control their Telegram account. Once in, they see only the tabs and data their role permits.

---

## Data Model

### New table: `web_admin_otps`
| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `telegram_id` | bigint | matches `admin_users.telegram_id` |
| `code_hash` | varchar(64) | sha256 of 6-digit code |
| `expires_at` | timestamptz | now + 5 min |
| `used` | boolean | default false |
| `created_at` | timestamptz | |

### New table: `web_admin_sessions`
| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | token sent to client |
| `admin_id` | UUID FK → `admin_users.id` | CASCADE delete |
| `created_at` | timestamptz | |
| `expires_at` | timestamptz | now + 8 hours |
| `last_used_at` | timestamptz | updated on each request |

No changes to existing tables.

---

## Auth Flow

### Step 1 — Request OTP
`POST /admin/request-otp` `{ telegram_id: number }`
- Checks `admin_users` row exists and status is `ACTIVE`
- Generates random 6-digit code, stores `sha256(code)` in `web_admin_otps` (5 min TTL, invalidates any previous unused OTP for same telegram_id)
- Bot sends: *"Your Peaceway web login code: XXXXXX (expires in 5 minutes)"*
- Returns `{ ok: true }` — no info about whether the ID exists (security)

### Step 2 — Verify OTP
`POST /admin/verify-otp` `{ telegram_id: number, code: string }`
- Looks up latest unused, unexpired OTP for telegram_id
- Compares `sha256(code)` — returns 401 on mismatch
- Marks OTP `used`, creates `web_admin_sessions` row (8h TTL)
- Returns `{ token: "<uuid>" }`

### Session validation
`GET /admin/me` — reads `X-Admin-Session` header, looks up session (not expired), returns:
```json
{ "full_name": "...", "telegram_id": 123, "roles": ["packaging"], "permissions": ["see_paid_orders", ...] }
```
Updates `last_used_at` on each call.

### Logout
`DELETE /admin/session` — deletes the session row.

### Page-load guard
On mount, if `pw_admin_session_token` is in `sessionStorage`, call `GET /admin/me`. If 401 → clear token, show login. If ok → show dashboard with filtered nav.

---

## API Auth Middleware

New `get_current_admin` dependency in `app/api/deps.py`:
- Reads `X-Admin-Session` header
- Looks up `web_admin_sessions` (not expired, admin is ACTIVE)
- Updates `last_used_at`
- Returns `(AdminUser, set[str] role_keys)`
- 401 if invalid/expired/disabled

**Old** `_check_admin` password guard is removed from `app/api/v1/admin.py`.

### Per-endpoint permissions
| Endpoint | Permission required |
|---|---|
| `GET /admin/requests` | `view_product_requests` |
| `GET /admin/orders` | `view_all_orders` OR `view_customer_orders` |
| `GET /admin/customers` | `view_customers` |
| `GET /admin/products` | `view_all_products` OR `edit_pricing` |
| `PATCH /admin/products/:id` | `edit_pricing` |

System Owner wildcard (`*`) passes all checks (except `approve_prescription` per existing safety rule).

---

## Frontend

### New: `web/lib/admin-auth.ts`
- `getToken() / setToken() / clearToken()` — sessionStorage wrapper
- `adminFetch<T>(path, options)` — sends `X-Admin-Session` header, clears session + redirects to login on 401
- `hasPermission(permissions, key)` — checks a permission key

### Updated: `web/app/admin/page.tsx`
- `LoginGate` replaced with 2-step `TelegramOtpGate`:
  - Step 1: Telegram ID input + "Send Code" button
  - Step 2: 6-digit code input + "Verify" button + "Resend" link
- After login, `GET /admin/me` fetches roles/permissions
- `NAV` filtered by permissions before render
- All `adminFetch` calls use the new session-token wrapper (no `pwd` prop)

### Role → Tab visibility
| Tab | Permission(s) |
|---|---|
| Overview | *(any authenticated admin)* |
| Inventory | `edit_pricing` OR `view_all_products` |
| Requests | `view_product_requests` |
| Orders | `view_all_orders` OR `view_customer_orders` |
| Customers | `view_customers` |
| Payments | `review_payment_proof` OR `view_payment_history` OR `view_payment_status` |

---

## Migration
Single Alembic migration creating `web_admin_otps` and `web_admin_sessions`.  
`ADMIN_WEB_PASSWORD` env var is no longer used (can be removed from Railway).

## Out of scope
- Web-side admin registration (owner still adds staff via Telegram bot)
- Rate limiting on OTP requests (can add later)
- Remember-me / persistent sessions (8h is sufficient for a shift)
