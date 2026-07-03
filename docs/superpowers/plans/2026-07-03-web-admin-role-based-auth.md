# Web Admin Role-Based Auth Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the single shared admin password on the web panel with Telegram-bridge OTP auth, where each staff member logs in by proving they control their Telegram account, and sees only the tabs their role permits.

**Architecture:** Admin enters their Telegram ID → backend generates a 6-digit OTP, sends it via the Telegram bot to their chat → admin pastes the code → backend verifies, creates a `web_admin_sessions` DB row (8h TTL), returns the UUID token. Frontend stores the token in `sessionStorage`, sends it as `X-Admin-Session` on every request. `GET /admin/me` returns the admin's roles/permissions and drives tab visibility.

**Tech Stack:** Python/FastAPI/SQLAlchemy (backend), aiogram (Telegram bot), Next.js/TypeScript (frontend), PostgreSQL (prod), SQLite in-memory (tests), Alembic (migrations).

---

## File Map

| Action | Path | Responsibility |
|---|---|---|
| Modify | `app/models/admin.py` | Add `WebAdminOtp` + `WebAdminSession` ORM models |
| Modify | `app/models/__init__.py` | Export new models so `Base.metadata` picks them up |
| Create | `alembic/versions/<rev>_add_web_admin_auth_tables.py` | DB migration |
| Create | `app/services/admin_web_auth.py` | OTP lifecycle + session create/validate/delete |
| Modify | `app/api/deps.py` | Add `get_current_admin` dep + `AdminSessionDep` type alias |
| Modify | `app/api/v1/admin.py` | Remove password guard; add 4 new auth endpoints; add per-route permission checks |
| Create | `web/lib/admin-auth.ts` | Token storage, `adminFetch` wrapper, `hasPermission` helpers |
| Modify | `web/app/admin/page.tsx` | Replace `LoginGate` with Telegram OTP flow; role-filter nav |
| Create | `tests/test_admin_web_auth.py` | Unit tests for OTP + session service |

---

## Task 1: ORM Models

**Files:**
- Modify: `app/models/admin.py`
- Modify: `app/models/__init__.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_admin_web_auth.py
"""Web admin OTP + session service tests."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest
import pytest_asyncio

from app.models.admin import AdminStatus, AdminUser, AdminRoleAssignment, WebAdminOtp, WebAdminSession


@pytest.mark.asyncio
async def test_web_admin_otp_model_exists(session):
    """WebAdminOtp can be created and queried."""
    from uuid import uuid4
    from datetime import timedelta

    otp = WebAdminOtp(
        telegram_id=123456789,
        code_hash="abc123",
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
        used=False,
    )
    session.add(otp)
    await session.flush()
    assert otp.id is not None


@pytest.mark.asyncio
async def test_web_admin_session_model_exists(session):
    """WebAdminSession can be linked to an AdminUser."""
    from uuid import uuid4
    from datetime import timedelta

    admin = AdminUser(telegram_id=111222333, status=AdminStatus.ACTIVE, is_active=True)
    session.add(admin)
    await session.flush()

    web_session = WebAdminSession(
        admin_id=admin.id,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=8),
    )
    session.add(web_session)
    await session.flush()
    assert web_session.id is not None
```

- [ ] **Step 2: Run test — expect ImportError**

```
pytest tests/test_admin_web_auth.py -v
```
Expected: `ImportError: cannot import name 'WebAdminOtp'`

- [ ] **Step 3: Add models to `app/models/admin.py`**

Append after the existing `AdminActivityLog` class (end of file):

```python
class WebAdminOtp(Base, TimestampMixin):
    """Short-lived OTP for Telegram-bridge web login."""
    __tablename__ = "web_admin_otps"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    telegram_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    code_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class WebAdminSession(Base):
    """Active web admin session — UUID token sent to client."""
    __tablename__ = "web_admin_sessions"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    admin_id: Mapped[UUID] = mapped_column(
        ForeignKey("admin_users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    admin: Mapped["AdminUser"] = relationship(lazy="selectin")
```

The file already imports `BigInteger`, `Boolean`, `DateTime`, `ForeignKey`, `String`, `UUID`, `uuid4`, `datetime`, `func` — add `func` to the SQLAlchemy import if not present. Check the top of the file:

```python
# Existing import — add func if missing:
from sqlalchemy import BigInteger, Boolean, DateTime
from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
```

`func` comes from `sqlalchemy` — add it:
```python
from sqlalchemy import BigInteger, Boolean, DateTime, func
```

- [ ] **Step 4: Export new models from `app/models/__init__.py`**

Add to the imports block at the top (after existing `AdminUser` import line):
```python
from app.models.admin import (
    AdminActivityLog,
    AdminRoleAssignment,
    AdminUser,
    Permission,
    Role,
    RolePermission,
    WebAdminOtp,
    WebAdminSession,
)
```

Add to the `__all__` list:
```python
    "WebAdminOtp",
    "WebAdminSession",
```

- [ ] **Step 5: Run test — expect pass**

```
pytest tests/test_admin_web_auth.py::test_web_admin_otp_model_exists tests/test_admin_web_auth.py::test_web_admin_session_model_exists -v
```
Expected: both PASS

- [ ] **Step 6: Commit**

```bash
git add app/models/admin.py app/models/__init__.py tests/test_admin_web_auth.py
git commit -m "feat: add WebAdminOtp and WebAdminSession ORM models"
```

---

## Task 2: Alembic Migration

**Files:**
- Create: `alembic/versions/<rev>_add_web_admin_auth_tables.py`

- [ ] **Step 1: Generate the migration file**

```bash
cd C:/Projects/peaceway-online
alembic revision --autogenerate -m "add web admin auth tables"
```

This creates a new file in `alembic/versions/`. Open it and verify the `upgrade()` body. It should contain `op.create_table` calls for both `web_admin_otps` and `web_admin_sessions`. If autogenerate missed anything, replace `upgrade()` / `downgrade()` with the explicit version below.

Expected `upgrade()`:
```python
def upgrade() -> None:
    op.create_table(
        "web_admin_otps",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("code_hash", sa.String(64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_web_admin_otps_telegram_id", "web_admin_otps", ["telegram_id"])

    op.create_table(
        "web_admin_sessions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("admin_id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["admin_id"], ["admin_users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_web_admin_sessions_admin_id", "web_admin_sessions", ["admin_id"])


def downgrade() -> None:
    op.drop_index("ix_web_admin_sessions_admin_id", "web_admin_sessions")
    op.drop_table("web_admin_sessions")
    op.drop_index("ix_web_admin_otps_telegram_id", "web_admin_otps")
    op.drop_table("web_admin_otps")
```

- [ ] **Step 2: Apply migration locally (if running Railway DB locally skip this)**

If you have a local Postgres or are connected to Railway:
```bash
alembic upgrade head
```
Expected: `Running upgrade <prev> -> <new>, add web admin auth tables`

- [ ] **Step 3: Commit**

```bash
git add alembic/versions/
git commit -m "feat: migration — add web_admin_otps and web_admin_sessions tables"
```

---

## Task 3: Auth Service

**Files:**
- Create: `app/services/admin_web_auth.py`
- Modify: `tests/test_admin_web_auth.py`

- [ ] **Step 1: Write failing tests**

Append to `tests/test_admin_web_auth.py`:

```python
from app.services.admin_web_auth import (
    create_web_otp,
    verify_web_otp_and_create_session,
    get_session_admin,
    delete_session,
)


async def _make_active_admin(session, telegram_id: int = 999888777) -> AdminUser:
    admin = AdminUser(telegram_id=telegram_id, status=AdminStatus.ACTIVE, is_active=True)
    session.add(admin)
    await session.flush()
    return admin


@pytest.mark.asyncio
async def test_create_web_otp_returns_code_for_active_admin(session):
    admin = await _make_active_admin(session)
    result = await create_web_otp(session, admin.telegram_id)
    assert result is not None
    code, tid = result
    assert len(code) == 6 and code.isdigit()
    assert tid == admin.telegram_id


@pytest.mark.asyncio
async def test_create_web_otp_returns_none_for_unknown_id(session):
    result = await create_web_otp(session, 0)
    assert result is None


@pytest.mark.asyncio
async def test_create_web_otp_returns_none_for_pending_admin(session):
    admin = AdminUser(telegram_id=555444333, status=AdminStatus.PENDING, is_active=False)
    session.add(admin)
    await session.flush()
    result = await create_web_otp(session, admin.telegram_id)
    assert result is None


@pytest.mark.asyncio
async def test_verify_otp_creates_session(session):
    admin = await _make_active_admin(session)
    result = await create_web_otp(session, admin.telegram_id)
    assert result is not None
    code, _ = result
    await session.flush()

    token = await verify_web_otp_and_create_session(session, admin.telegram_id, code)
    assert token is not None
    assert len(token) == 36  # UUID string


@pytest.mark.asyncio
async def test_verify_otp_wrong_code_returns_none(session):
    admin = await _make_active_admin(session, telegram_id=111000111)
    await create_web_otp(session, admin.telegram_id)
    await session.flush()

    token = await verify_web_otp_and_create_session(session, admin.telegram_id, "000000")
    assert token is None


@pytest.mark.asyncio
async def test_get_session_admin_returns_admin_and_roles(session):
    from app.models.admin import AdminRoleAssignment
    admin = await _make_active_admin(session, telegram_id=222333444)
    session.add(AdminRoleAssignment(admin_id=admin.id, role_key="packaging"))
    result = await create_web_otp(session, admin.telegram_id)
    assert result is not None
    code, _ = result
    await session.flush()

    token = await verify_web_otp_and_create_session(session, admin.telegram_id, code)
    assert token is not None
    await session.flush()

    auth = await get_session_admin(session, token)
    assert auth is not None
    fetched_admin, role_keys = auth
    assert fetched_admin.telegram_id == admin.telegram_id
    assert "packaging" in role_keys


@pytest.mark.asyncio
async def test_get_session_admin_invalid_token_returns_none(session):
    result = await get_session_admin(session, "not-a-uuid")
    assert result is None


@pytest.mark.asyncio
async def test_delete_session_invalidates_token(session):
    admin = await _make_active_admin(session, telegram_id=777666555)
    result = await create_web_otp(session, admin.telegram_id)
    assert result is not None
    code, _ = result
    await session.flush()

    token = await verify_web_otp_and_create_session(session, admin.telegram_id, code)
    assert token is not None
    await session.flush()

    await delete_session(session, token)
    await session.flush()

    auth = await get_session_admin(session, token)
    assert auth is None
```

- [ ] **Step 2: Run tests — expect ImportError**

```
pytest tests/test_admin_web_auth.py -v -k "not model_exists"
```
Expected: `ImportError: cannot import name 'create_web_otp'`

- [ ] **Step 3: Create `app/services/admin_web_auth.py`**

```python
"""Web admin authentication: Telegram-bridge OTP + DB sessions."""
from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.admin import AdminStatus, AdminUser, WebAdminOtp, WebAdminSession

OTP_TTL_MINUTES = 5
SESSION_TTL_HOURS = 8


def _hash_code(code: str) -> str:
    return hashlib.sha256(code.encode()).hexdigest()


async def create_web_otp(
    db: AsyncSession, telegram_id: int
) -> tuple[str, int] | None:
    """Generate a login OTP for an ACTIVE admin.

    Returns (plaintext_code, telegram_id) so the caller can send the code via bot.
    Returns None if the telegram_id is not an active admin (caller returns 200 either way).
    """
    admin = (
        await db.execute(
            select(AdminUser).where(AdminUser.telegram_id == telegram_id)
        )
    ).scalar_one_or_none()

    if admin is None or admin.status != AdminStatus.ACTIVE:
        return None

    # Invalidate any existing unused OTPs for this telegram_id
    await db.execute(
        update(WebAdminOtp)
        .where(WebAdminOtp.telegram_id == telegram_id, WebAdminOtp.used.is_(False))
        .values(used=True)
    )

    code = f"{secrets.randbelow(1_000_000):06d}"
    db.add(
        WebAdminOtp(
            telegram_id=telegram_id,
            code_hash=_hash_code(code),
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=OTP_TTL_MINUTES),
            used=False,
        )
    )

    return code, telegram_id


async def verify_web_otp_and_create_session(
    db: AsyncSession, telegram_id: int, code: str
) -> str | None:
    """Verify OTP, create a session row, return the session token (UUID string).

    Returns None on any failure (invalid code, expired, admin not active).
    Marks the OTP as used before checking the hash — prevents brute-force.
    """
    now = datetime.now(timezone.utc)

    otp = (
        await db.execute(
            select(WebAdminOtp)
            .where(
                WebAdminOtp.telegram_id == telegram_id,
                WebAdminOtp.used.is_(False),
                WebAdminOtp.expires_at > now,
            )
            .order_by(WebAdminOtp.created_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()

    if otp is None:
        return None

    otp.used = True  # mark before hash check — prevents brute-force

    if _hash_code(code) != otp.code_hash:
        return None

    admin = (
        await db.execute(
            select(AdminUser).where(AdminUser.telegram_id == telegram_id)
        )
    ).scalar_one_or_none()

    if admin is None or admin.status != AdminStatus.ACTIVE:
        return None

    session = WebAdminSession(
        id=uuid4(),
        admin_id=admin.id,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=SESSION_TTL_HOURS),
    )
    db.add(session)

    return str(session.id)


async def get_session_admin(
    db: AsyncSession, token: str
) -> tuple[AdminUser, set[str]] | None:
    """Validate a web session token.

    Returns (AdminUser, role_keys) if valid, None otherwise.
    Updates last_used_at on each successful call.
    """
    try:
        session_id = UUID(token)
    except ValueError:
        return None

    now = datetime.now(timezone.utc)

    web_session = (
        await db.execute(
            select(WebAdminSession).where(
                WebAdminSession.id == session_id,
                WebAdminSession.expires_at > now,
            )
        )
    ).scalar_one_or_none()

    if web_session is None:
        return None

    admin = web_session.admin
    if admin is None or admin.status != AdminStatus.ACTIVE:
        return None

    web_session.last_used_at = now
    role_keys = {a.role_key for a in admin.assignments}
    return admin, role_keys


async def delete_session(db: AsyncSession, token: str) -> None:
    """Delete a web session by token (logout)."""
    try:
        session_id = UUID(token)
    except ValueError:
        return

    web_session = (
        await db.execute(
            select(WebAdminSession).where(WebAdminSession.id == session_id)
        )
    ).scalar_one_or_none()

    if web_session:
        await db.delete(web_session)
```

- [ ] **Step 4: Run tests — expect all pass**

```
pytest tests/test_admin_web_auth.py -v
```
Expected: all 10 tests PASS

- [ ] **Step 5: Commit**

```bash
git add app/services/admin_web_auth.py tests/test_admin_web_auth.py
git commit -m "feat: add web admin OTP + session auth service"
```

---

## Task 4: API Dependency

**Files:**
- Modify: `app/api/deps.py`

- [ ] **Step 1: Add `get_current_admin` to `app/api/deps.py`**

Add these imports at the top of the file (after existing imports):

```python
from typing import Annotated

from fastapi import Header
```

`Annotated` is already imported — just add `Header` if it's not there. The existing imports are:
```python
from fastapi import Cookie, Depends, HTTPException, status
```
Change to:
```python
from fastapi import Cookie, Depends, Header, HTTPException, status
```

Then append at the end of `app/api/deps.py`:

```python
async def _get_current_admin(
    db: DbSession,
    x_admin_session: Annotated[str, Header()] = "",
) -> "tuple[AdminUser, set[str]]":
    from app.models.admin import AdminUser  # noqa: F401 — for type hint
    from app.services.admin_web_auth import get_session_admin

    result = await get_session_admin(db, x_admin_session)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session.",
        )
    return result


AdminSessionDep = Annotated[
    "tuple[AdminUser, set[str]]",
    Depends(_get_current_admin),
]
```

- [ ] **Step 2: Run existing test suite to make sure nothing broke**

```
pytest tests/ -v --ignore=tests/test_admin_web_auth.py -x
```
Expected: all existing tests PASS (no changes to existing behaviour yet)

- [ ] **Step 3: Commit**

```bash
git add app/api/deps.py
git commit -m "feat: add get_current_admin dependency for web admin session auth"
```

---

## Task 5: Backend Admin Endpoints

**Files:**
- Modify: `app/api/v1/admin.py`

This task rewrites the auth layer and adds four new endpoints. Read the full current file before editing.

- [ ] **Step 1: Replace the file header + auth section**

The top of `app/api/v1/admin.py` currently has:
```python
ADMIN_PASSWORD = os.getenv("ADMIN_WEB_PASSWORD", "")

class AuthBody(BaseModel):
    password: str

def _check_admin(x_admin_password: str = Header(default="")) -> None:
    if not ADMIN_PASSWORD or x_admin_password != ADMIN_PASSWORD:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized.")

AdminGuard = Depends(_check_admin)
```

Replace the entire imports + constants + auth section at the top of the file with:

```python
"""Admin web API — Telegram-bridge OTP auth + role-gated staff endpoints."""
from __future__ import annotations

from decimal import Decimal
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy import func, or_, select

from app.api.deps import AdminSessionDep, DbSession
from app.core import rbac
from app.models.admin import AdminUser
from app.models.catalog import Product, ProductPricing
from app.models.ops import ProductRequest
from app.models.orders import Customer, Order
from app.services.products_admin import apply_change, parse_int, parse_money

router = APIRouter(tags=["admin"])
```

(Remove the `import os` line and all password-related code.)

- [ ] **Step 2: Add the four new auth endpoints**

Insert this block directly after the `router = APIRouter(...)` line, before the existing `_money_out` helper:

```python
# ── Auth endpoints ────────────────────────────────────────────────────────────

class RequestOtpBody(BaseModel):
    telegram_id: int


class VerifyOtpBody(BaseModel):
    telegram_id: int
    code: str


class AdminMeResponse(BaseModel):
    telegram_id: int
    full_name: str | None
    roles: list[str]
    permissions: list[str]


@router.post("/admin/request-otp")
async def admin_request_otp(body: RequestOtpBody, request: Request, db: DbSession) -> dict:
    """Send a 6-digit OTP to the admin's Telegram chat.

    Always returns {ok: true} — never reveals whether the telegram_id exists.
    """
    from app.services.admin_web_auth import create_web_otp

    result = await create_web_otp(db, body.telegram_id)
    if result is not None:
        code, telegram_id = result
        bot = request.app.state.bot
        try:
            await bot.send_message(
                chat_id=telegram_id,
                text=(
                    f"🔐 <b>Peaceway web login code:</b> <code>{code}</code>\n\n"
                    f"Expires in 5 minutes. Do not share this code."
                ),
                parse_mode="HTML",
            )
        except Exception:
            pass  # Silently fail — don't reveal anything to the caller
    return {"ok": True}


@router.post("/admin/verify-otp")
async def admin_verify_otp(body: VerifyOtpBody, db: DbSession) -> dict:
    """Verify OTP and return a session token."""
    from app.services.admin_web_auth import verify_web_otp_and_create_session

    token = await verify_web_otp_and_create_session(db, body.telegram_id, body.code)
    if token is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired code.")
    return {"token": token}


@router.get("/admin/me")
async def admin_me(auth: AdminSessionDep) -> AdminMeResponse:
    """Return the current admin's profile and permissions."""
    admin, role_keys = auth
    permissions: set[str] = set()
    for rk in role_keys:
        perms = rbac.ROLE_PERMISSIONS.get(rk, set())
        if rbac.WILDCARD in perms:
            permissions.add("*")
        else:
            permissions.update(perms)
    # Remove wildcard-excluded permissions
    permissions -= rbac.WILDCARD_EXCLUDES
    return AdminMeResponse(
        telegram_id=admin.telegram_id,
        full_name=admin.full_name,
        roles=sorted(role_keys),
        permissions=sorted(permissions),
    )


@router.delete("/admin/session", status_code=204)
async def admin_logout(auth: AdminSessionDep, db: DbSession) -> None:
    """Delete all active sessions for the current admin (logout)."""
    from datetime import datetime, timezone
    from app.models.admin import WebAdminSession

    admin, _ = auth
    now = datetime.now(timezone.utc)
    sessions = (
        await db.execute(
            select(WebAdminSession).where(
                WebAdminSession.admin_id == admin.id,
                WebAdminSession.expires_at > now,
            )
        )
    ).scalars().all()
    for s in sessions:
        await db.delete(s)

- [ ] **Step 3: Update existing endpoints to use `AdminSessionDep` + permission checks**

Replace each existing endpoint signature and guard. The pattern is: remove `dependencies=[AdminGuard]` and add `auth: AdminSessionDep` as a parameter, then check the required permission.

**`admin_list_requests`:**
```python
@router.get("/admin/requests")
async def admin_list_requests(db: DbSession, auth: AdminSessionDep) -> list[dict]:
    _, role_keys = auth
    if not rbac.has_permission(role_keys, "view_product_requests"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden.")
    rows = (
        await db.execute(
            select(ProductRequest).order_by(ProductRequest.created_at.desc()).limit(200)
        )
    ).scalars().all()
    return [
        {
            "id": str(r.id),
            "product_name": r.product_name,
            "status": r.status,
            "customer_phone": r.customer_phone,
            "urgency": r.urgency,
            "created_at": r.created_at.isoformat(),
        }
        for r in rows
    ]
```

**`admin_list_orders`:**
```python
@router.get("/admin/orders")
async def admin_list_orders(db: DbSession, auth: AdminSessionDep) -> list[dict]:
    _, role_keys = auth
    if not (rbac.has_permission(role_keys, "view_all_orders") or rbac.has_permission(role_keys, "view_customer_orders")):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden.")
    rows = (
        await db.execute(
            select(Order).order_by(Order.created_at.desc()).limit(200)
        )
    ).scalars().all()
    return [
        {
            "id": str(o.id),
            "code": o.code,
            "status": o.status.value,
            "total": str(o.total),
            "created_at": o.created_at.isoformat(),
        }
        for o in rows
    ]
```

**`admin_list_customers`:**
```python
@router.get("/admin/customers")
async def admin_list_customers(db: DbSession, auth: AdminSessionDep) -> list[dict]:
    _, role_keys = auth
    if not rbac.has_permission(role_keys, "view_customers"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden.")
    rows = (
        await db.execute(
            select(Customer).order_by(Customer.created_at.desc()).limit(200)
        )
    ).scalars().all()
    return [
        {
            "id": str(c.id),
            "full_name": c.full_name,
            "phone": c.phone,
            "email": c.email,
            "created_at": c.created_at.isoformat(),
        }
        for c in rows
    ]
```

**`admin_list_products`:**
```python
@router.get("/admin/products")
async def admin_list_products(
    db: DbSession,
    auth: AdminSessionDep,
    q: str | None = None,
    status_filter: Literal["all", "listed", "unlisted", "in_stock", "out_of_stock", "unpriced"] = "all",
    limit: int = 100,
    offset: int = 0,
) -> dict:
    _, role_keys = auth
    if not (rbac.has_permission(role_keys, "view_all_products") or rbac.has_permission(role_keys, "edit_pricing")):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden.")
    # ... rest of the existing function body unchanged ...
```

**`admin_update_product`:**
```python
@router.patch("/admin/products/{product_id}")
async def admin_update_product(
    product_id: UUID, body: AdminProductPatch, db: DbSession, auth: AdminSessionDep
) -> dict:
    _, role_keys = auth
    if not rbac.has_permission(role_keys, "edit_pricing"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden.")
    # ... rest of the existing function body unchanged ...
```

Also remove the now-unused `admin_auth` endpoint (the old `POST /admin/auth` password endpoint).

- [ ] **Step 4: Run the full test suite**

```
pytest tests/ -v -x
```
Expected: all tests PASS (the admin endpoint tests don't hit the real DB; the service tests pass via SQLite)

- [ ] **Step 5: Commit**

```bash
git add app/api/v1/admin.py
git commit -m "feat: replace admin password guard with Telegram-bridge OTP session auth"
```

---

## Task 6: Frontend Auth Library

**Files:**
- Create: `web/lib/admin-auth.ts`

- [ ] **Step 1: Create `web/lib/admin-auth.ts`**

```typescript
/**
 * Web admin auth helpers.
 *
 * Session token is stored in sessionStorage (cleared when tab closes).
 * Every admin API call goes through adminFetch — it injects the session
 * header and redirects to login on 401.
 */
import { getApiBase } from "./api";

const TOKEN_KEY = "pw_admin_session_token";

export function getAdminToken(): string | null {
  if (typeof window === "undefined") return null;
  return sessionStorage.getItem(TOKEN_KEY);
}

export function setAdminToken(token: string): void {
  sessionStorage.setItem(TOKEN_KEY, token);
}

export function clearAdminToken(): void {
  sessionStorage.removeItem(TOKEN_KEY);
}

export function adminFetch<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getAdminToken();
  const API_BASE = getApiBase();
  return fetch(`${API_BASE}${path}`, {
    ...options,
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { "X-Admin-Session": token } : {}),
      ...(options.headers ?? {}),
    },
  }).then(async (res) => {
    if (res.status === 401) {
      clearAdminToken();
      window.location.reload();
      throw new Error("Session expired.");
    }
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      throw new Error((body as { detail?: string })?.detail ?? res.statusText);
    }
    if (res.status === 204) return undefined as unknown as T;
    return res.json() as Promise<T>;
  });
}

/** True if the admin has the given permission (or holds the wildcard). */
export function hasPermission(permissions: string[], key: string): boolean {
  return permissions.includes("*") || permissions.includes(key);
}

/** True if the admin has ANY of the given permissions. */
export function anyPermission(permissions: string[], keys: string[]): boolean {
  return keys.some((k) => hasPermission(permissions, k));
}
```

- [ ] **Step 2: Commit**

```bash
git add web/lib/admin-auth.ts
git commit -m "feat: add admin-auth.ts — session token storage, adminFetch, permission helpers"
```

---

## Task 7: Frontend Page Update

**Files:**
- Modify: `web/app/admin/page.tsx`

This is the largest frontend change. Replace the entire file content.

- [ ] **Step 1: Rewrite `web/app/admin/page.tsx`**

The new file keeps all existing tab components (`CatalogTab`, `OverviewTab`, `RequestsTab`, `OrdersTab`) intact but replaces the auth layer and nav.

Replace the file with:

```tsx
"use client";

import { useCallback, useEffect, useState } from "react";
import {
  LayoutGrid, ClipboardList, Package, Users, DollarSign, ShoppingBag,
  LogOut, Search, Save, RefreshCcw,
} from "lucide-react";
import {
  adminFetch, setAdminToken, clearAdminToken, getAdminToken, anyPermission,
} from "@/lib/admin-auth";

// ── Types ─────────────────────────────────────────────────────────────────────
interface AdminMe {
  telegram_id: number;
  full_name: string | null;
  roles: string[];
  permissions: string[];
}

interface AdminRequest {
  id: string;
  product_name: string;
  status: string;
  customer_phone: string | null;
  created_at: string;
}

interface AdminOrder {
  id: string;
  code: string;
  status: string;
  total: string;
  created_at: string;
}

interface AdminProduct {
  id: string;
  name: string;
  generic_name: string;
  brand_name: string | null;
  dosage_form: string | null;
  strength: string | null;
  category: string | null;
  requires_prescription: boolean;
  requires_review: boolean;
  is_listed: boolean;
  cost_price: string | null;
  selling_price: string | null;
  stock_qty: number;
  is_in_stock: boolean;
  updated_at: string;
}

interface AdminProductsResponse {
  items: AdminProduct[];
  total: number;
  limit: number;
  offset: number;
  metrics: {
    total: number;
    listed: number;
    in_stock: number;
    unpriced: number;
  };
}

type ProductDraft = {
  selling_price: string;
  cost_price: string;
  stock_qty: string;
  is_listed: boolean;
  requires_prescription: boolean;
};

// ── Nav definition (permission-gated) ────────────────────────────────────────
const ALL_NAV = [
  { key: "overview",  icon: LayoutGrid,    label: "Overview",   permissions: [] as string[] },
  { key: "catalog",   icon: ShoppingBag,   label: "Inventory",  permissions: ["edit_pricing", "view_all_products"] },
  { key: "requests",  icon: ClipboardList, label: "Requests",   permissions: ["view_product_requests"] },
  { key: "orders",    icon: Package,       label: "Orders",     permissions: ["view_all_orders", "view_customer_orders"] },
  { key: "customers", icon: Users,         label: "Customers",  permissions: ["view_customers"] },
  { key: "payments",  icon: DollarSign,    label: "Payments",   permissions: ["review_payment_proof", "view_payment_history", "view_payment_status"] },
];

function visibleNav(permissions: string[]) {
  return ALL_NAV.filter(
    (item) => item.permissions.length === 0 || anyPermission(permissions, item.permissions)
  );
}

// ── Status labels / colors ────────────────────────────────────────────────────
const REQ_STATUS_COLOR: Record<string, string> = {
  NEW: "bg-white/8 text-white/50 border-white/12",
  CHECKING_AVAILABILITY: "bg-amber-500/15 text-amber-400 border-amber-500/25",
  AVAILABLE: "bg-emerald-500/15 text-emerald-400 border-emerald-500/25",
  NOT_AVAILABLE: "bg-red-500/15 text-red-400 border-red-500/25",
  FULFILLED: "bg-emerald-500/15 text-emerald-400 border-emerald-500/25",
};
const REQ_STATUS_LABEL: Record<string, string> = {
  NEW: "New",
  CHECKING_AVAILABILITY: "Checking",
  AVAILABLE: "Available",
  NOT_AVAILABLE: "Not avail.",
  READY_TO_ORDER: "Ready",
  FULFILLED: "Fulfilled",
  CLOSED: "Closed",
};

// ── Telegram OTP login gate ───────────────────────────────────────────────────
function TelegramOtpGate({ onLogin }: { onLogin: (admin: AdminMe) => void }) {
  const [step, setStep] = useState<"id" | "code">("id");
  const [telegramId, setTelegramId] = useState("");
  const [code, setCode] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSendCode() {
    const tid = telegramId.trim();
    if (!tid || !/^\d+$/.test(tid)) {
      setError("Enter your numeric Telegram ID.");
      return;
    }
    setLoading(true);
    setError("");
    try {
      await adminFetch<{ ok: boolean }>("/admin/request-otp", {
        method: "POST",
        body: JSON.stringify({ telegram_id: Number(tid) }),
      });
      setStep("code");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not send code.");
    } finally {
      setLoading(false);
    }
  }

  async function handleVerify() {
    const c = code.trim();
    if (!c || c.length !== 6) {
      setError("Enter the 6-digit code from Telegram.");
      return;
    }
    setLoading(true);
    setError("");
    try {
      const { token } = await adminFetch<{ token: string }>("/admin/verify-otp", {
        method: "POST",
        body: JSON.stringify({ telegram_id: Number(telegramId.trim()), code: c }),
      });
      setAdminToken(token);
      const me = await adminFetch<AdminMe>("/admin/me");
      onLogin(me);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Invalid code.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center px-5">
      <div className="w-full max-w-sm space-y-6">
        <div className="text-center">
          <p className="font-syne text-[20px] font-bold text-white">Peaceway Admin</p>
          <p className="mt-1 text-[13px] text-white/40">Staff access only</p>
        </div>
        <div className="rounded-2xl border border-white/8 bg-white/4 p-6 space-y-4">
          {step === "id" ? (
            <>
              <div className="space-y-1.5">
                <label className="text-[11px] font-medium text-white/50">Your Telegram ID</label>
                <input
                  type="text"
                  inputMode="numeric"
                  value={telegramId}
                  onChange={(e) => setTelegramId(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && handleSendCode()}
                  placeholder="e.g. 123456789"
                  className="w-full rounded-xl border border-white/10 bg-white/5 px-4 py-3 text-sm text-white placeholder-white/30 outline-none focus:border-emerald-500/50"
                />
                <p className="text-[11px] text-white/30">
                  Send <code>/myid</code> to the Peaceway bot to find your ID.
                </p>
              </div>
              {error && <p className="text-[13px] text-red-400">{error}</p>}
              <button
                onClick={handleSendCode}
                disabled={loading || !telegramId.trim()}
                className="w-full rounded-xl bg-emerald-500 py-3.5 text-sm font-semibold text-black disabled:opacity-50"
              >
                {loading ? "Sending…" : "Send Code via Telegram"}
              </button>
            </>
          ) : (
            <>
              <div className="space-y-1.5">
                <label className="text-[11px] font-medium text-white/50">6-digit code</label>
                <input
                  type="text"
                  inputMode="numeric"
                  maxLength={6}
                  value={code}
                  onChange={(e) => setCode(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && handleVerify()}
                  placeholder="000000"
                  className="w-full rounded-xl border border-white/10 bg-white/5 px-4 py-3 text-sm text-white placeholder-white/30 outline-none focus:border-emerald-500/50 tracking-[0.3em]"
                  autoFocus
                />
                <p className="text-[11px] text-white/30">Check your Telegram — the code expires in 5 minutes.</p>
              </div>
              {error && <p className="text-[13px] text-red-400">{error}</p>}
              <button
                onClick={handleVerify}
                disabled={loading || code.trim().length !== 6}
                className="w-full rounded-xl bg-emerald-500 py-3.5 text-sm font-semibold text-black disabled:opacity-50"
              >
                {loading ? "Verifying…" : "Verify & Sign In"}
              </button>
              <button
                onClick={() => { setStep("id"); setCode(""); setError(""); }}
                className="w-full text-center text-[12px] text-white/30 hover:text-white/60"
              >
                ← Resend / use different ID
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

// ── Dashboard ─────────────────────────────────────────────────────────────────
function Dashboard({ admin }: { admin: AdminMe }) {
  const nav = visibleNav(admin.permissions);
  const [tab, setTab] = useState(nav[0]?.key ?? "overview");
  const [requests, setRequests] = useState<AdminRequest[]>([]);
  const [orders, setOrders] = useState<AdminOrder[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setLoading(true);
    Promise.allSettled([
      adminFetch<AdminRequest[]>("/admin/requests"),
      adminFetch<AdminOrder[]>("/admin/orders"),
    ]).then(([reqRes, ordRes]) => {
      if (reqRes.status === "fulfilled") setRequests(reqRes.value);
      if (ordRes.status === "fulfilled") setOrders(ordRes.value);
      setLoading(false);
    });
  }, []);

  async function signOut() {
    try {
      await adminFetch("/admin/session", { method: "DELETE" });
    } catch {
      // ignore
    }
    clearAdminToken();
    window.location.reload();
  }

  return (
    <div className="flex min-h-screen">
      {/* Sidebar */}
      <aside className="hidden w-[200px] shrink-0 flex-col gap-2 border-r border-white/8 bg-[#0a0b08] px-3 py-6 lg:flex">
        <div className="mb-4 px-3">
          <p className="font-syne text-[13px] font-bold text-white">Peaceway</p>
          <p className="text-[10px] text-white/30">{admin.full_name ?? "Admin panel"}</p>
        </div>
        {nav.map((item) => (
          <button
            key={item.key}
            onClick={() => setTab(item.key)}
            className={`flex items-center gap-3 rounded-xl px-3 py-2.5 text-[13px] font-medium transition ${
              tab === item.key
                ? "bg-emerald-500/12 text-emerald-400"
                : "text-white/40 hover:text-white/70"
            }`}
          >
            <item.icon className="h-4 w-4" />
            {item.label}
          </button>
        ))}
        <div className="mt-auto">
          <button
            onClick={signOut}
            className="flex items-center gap-3 rounded-xl px-3 py-2.5 text-[13px] text-white/30 hover:text-white/60"
          >
            <LogOut className="h-4 w-4" />
            Sign out
          </button>
        </div>
      </aside>

      {/* Mobile top nav */}
      <div className="fixed top-0 left-0 right-0 z-10 flex gap-1 overflow-x-auto border-b border-white/8 bg-[#0a0b08] px-3 py-2 lg:hidden">
        {nav.map((item) => (
          <button
            key={item.key}
            onClick={() => setTab(item.key)}
            className={`shrink-0 flex items-center gap-1.5 rounded-lg px-3 py-2 text-[11px] font-medium transition ${
              tab === item.key
                ? "bg-emerald-500/15 text-emerald-400"
                : "text-white/40"
            }`}
          >
            <item.icon className="h-3.5 w-3.5" />
            {item.label}
          </button>
        ))}
      </div>

      {/* Content */}
      <main className="flex-1 overflow-auto p-5 pt-16 lg:pt-6">
        {tab === "overview" && (
          <OverviewTab requests={requests} orders={orders} loading={loading} onTab={setTab} />
        )}
        {tab === "requests" && (
          <RequestsTab requests={requests} loading={loading} />
        )}
        {tab === "orders" && (
          <OrdersTab orders={orders} loading={loading} />
        )}
        {tab === "customers" && (
          <div className="py-10 text-center text-white/40">Customer list — coming soon</div>
        )}
        {tab === "payments" && (
          <div className="py-10 text-center text-white/40">Payment records — coming soon</div>
        )}
        {tab === "catalog" && (
          <CatalogTab />
        )}
      </main>
    </div>
  );
}

function productToDraft(product: AdminProduct): ProductDraft {
  return {
    selling_price: product.selling_price ? String(Number(product.selling_price)) : "",
    cost_price: product.cost_price ? String(Number(product.cost_price)) : "",
    stock_qty: String(product.stock_qty ?? 0),
    is_listed: product.is_listed,
    requires_prescription: product.requires_prescription,
  };
}

function formatMoney(value: string | null): string {
  if (!value || Number(value) <= 0) return "No price";
  return `₦${Number(value).toLocaleString("en-NG")}`;
}

// ── CatalogTab — no longer receives pwd ──────────────────────────────────────
function CatalogTab() {
  const [q, setQ] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [data, setData] = useState<AdminProductsResponse | null>(null);
  const [drafts, setDrafts] = useState<Record<string, ProductDraft>>({});
  const [loading, setLoading] = useState(false);
  const [savingId, setSavingId] = useState<string | null>(null);
  const [message, setMessage] = useState("");

  const loadProducts = useCallback(async () => {
    setLoading(true);
    setMessage("");
    try {
      const params = new URLSearchParams();
      if (q.trim()) params.set("q", q.trim());
      params.set("status_filter", statusFilter);
      params.set("limit", "100");
      const result = await adminFetch<AdminProductsResponse>(`/admin/products?${params.toString()}`);
      setData(result);
      setDrafts((current) => {
        const next = { ...current };
        result.items.forEach((product) => {
          next[product.id] = next[product.id] ?? productToDraft(product);
        });
        return next;
      });
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Could not load products.");
    } finally {
      setLoading(false);
    }
  }, [q, statusFilter]);

  useEffect(() => {
    const timeout = window.setTimeout(loadProducts, 300);
    return () => window.clearTimeout(timeout);
  }, [loadProducts]);

  function updateDraft(id: string, patch: Partial<ProductDraft>) {
    setDrafts((current) => ({
      ...current,
      [id]: {
        ...(current[id] ?? {
          selling_price: "",
          cost_price: "",
          stock_qty: "0",
          is_listed: false,
          requires_prescription: false,
        }),
        ...patch,
      },
    }));
  }

  async function saveProduct(product: AdminProduct, patch?: Partial<ProductDraft>) {
    const draft = { ...(drafts[product.id] ?? productToDraft(product)), ...(patch ?? {}) };
    const stockQty = Number.parseInt(draft.stock_qty || "0", 10);
    if (Number.isNaN(stockQty) || stockQty < 0) {
      setMessage("Stock must be a whole number.");
      return;
    }

    setSavingId(product.id);
    setMessage("");
    try {
      const payload: Record<string, string | number | boolean> = {};
      const sellingPrice = draft.selling_price.trim();
      const costPrice = draft.cost_price.trim();
      if (sellingPrice !== (product.selling_price ? String(Number(product.selling_price)) : "")) {
        payload.selling_price = sellingPrice;
      }
      if (costPrice !== (product.cost_price ? String(Number(product.cost_price)) : "")) {
        payload.cost_price = costPrice;
      }
      if (stockQty !== product.stock_qty) {
        payload.stock_qty = stockQty;
      }
      if (draft.is_listed !== product.is_listed) {
        payload.is_listed = draft.is_listed;
      }
      if (draft.requires_prescription !== product.requires_prescription) {
        payload.requires_prescription = draft.requires_prescription;
      }
      if (Object.keys(payload).length === 0) {
        setMessage("No product changes to save.");
        return;
      }
      const updated = await adminFetch<AdminProduct>(`/admin/products/${product.id}`, {
        method: "PATCH",
        body: JSON.stringify(payload),
      });
      setData((current) => {
        if (!current) return current;
        return {
          ...current,
          items: current.items.map((item) => (item.id === updated.id ? updated : item)),
        };
      });
      setDrafts((current) => ({ ...current, [updated.id]: productToDraft(updated) }));
      setMessage(`Saved ${updated.name}`);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Could not save product.");
    } finally {
      setSavingId(null);
    }
  }

  const metrics = data?.metrics;

  return (
    <div className="space-y-5">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <h2 className="font-syne text-[18px] font-bold text-white">Catalog Inventory</h2>
          <p className="mt-1 text-[12px] text-white/40">
            Search all imported products. Price, stock, and listing changes update the shop immediately.
          </p>
        </div>
        <button
          onClick={loadProducts}
          className="inline-flex h-10 items-center justify-center gap-2 rounded-xl border border-white/10 bg-white/5 px-4 text-[12px] font-semibold text-white/70 hover:border-emerald-500/40 hover:text-white"
        >
          <RefreshCcw className="h-4 w-4" />
          Refresh
        </button>
      </div>

      {metrics && (
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
          {[
            ["Total products", metrics.total.toLocaleString("en-NG")],
            ["Listed in shop", metrics.listed.toLocaleString("en-NG")],
            ["In stock", metrics.in_stock.toLocaleString("en-NG")],
            ["Need price", metrics.unpriced.toLocaleString("en-NG")],
          ].map(([label, value]) => (
            <div key={label} className="rounded-2xl border border-white/8 bg-white/4 p-4">
              <p className="text-[20px] font-bold text-white">{value}</p>
              <p className="mt-0.5 text-[11px] text-white/40">{label}</p>
            </div>
          ))}
        </div>
      )}

      <div className="grid gap-3 lg:grid-cols-[1fr_190px]">
        <div className="flex items-center gap-3 rounded-xl border border-white/10 bg-white/4 px-4 py-3">
          <Search className="h-4 w-4 shrink-0 text-white/30" />
          <input
            value={q}
            onChange={(event) => setQ(event.target.value)}
            placeholder="Search medicine, brand, generic name, NAFDAC..."
            className="flex-1 bg-transparent text-sm text-white placeholder-white/30 outline-none"
          />
        </div>
        <select
          value={statusFilter}
          onChange={(event) => setStatusFilter(event.target.value)}
          className="h-[46px] rounded-xl border border-white/10 bg-[#10110e] px-3 text-sm text-white outline-none"
        >
          <option value="all">All products</option>
          <option value="listed">Listed</option>
          <option value="unlisted">Unlisted</option>
          <option value="in_stock">In stock</option>
          <option value="out_of_stock">Out of stock</option>
          <option value="unpriced">Unpriced</option>
        </select>
      </div>

      {message && (
        <div className="rounded-xl border border-white/10 bg-white/5 px-4 py-3 text-[12px] text-white/70">
          {message}
        </div>
      )}

      <div className="overflow-hidden rounded-2xl border border-white/8 bg-white/4">
        <div className="flex items-center justify-between border-b border-white/6 px-4 py-3">
          <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-white/40">
            {loading ? "Loading products" : `${data?.total.toLocaleString("en-NG") ?? 0} matching products`}
          </p>
          <p className="text-[11px] text-white/30">Showing first 100</p>
        </div>

        {loading && (
          <div className="px-4 py-10 text-center text-[13px] text-white/30">Loading catalog…</div>
        )}
        {!loading && data?.items.length === 0 && (
          <div className="px-4 py-10 text-center text-[13px] text-white/30">No products found</div>
        )}
        {!loading && data && data.items.length > 0 && (
          <div className="divide-y divide-white/6">
            {data.items.map((product) => {
              const draft = drafts[product.id] ?? productToDraft(product);
              const saving = savingId === product.id;
              return (
                <div key={product.id} className="grid gap-4 px-4 py-4 xl:grid-cols-[minmax(260px,1fr)_140px_120px_190px_160px]">
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <p className="truncate text-[14px] font-semibold text-white">{product.name}</p>
                      {product.is_listed ? (
                        <span className="rounded-full border border-emerald-500/25 bg-emerald-500/12 px-2 py-0.5 text-[10px] font-semibold text-emerald-400">Listed</span>
                      ) : (
                        <span className="rounded-full border border-white/10 bg-white/5 px-2 py-0.5 text-[10px] font-semibold text-white/35">Hidden</span>
                      )}
                      {!product.is_in_stock && (
                        <span className="rounded-full border border-red-500/25 bg-red-500/12 px-2 py-0.5 text-[10px] font-semibold text-red-300">Out</span>
                      )}
                    </div>
                    <p className="mt-1 line-clamp-2 text-[11px] text-white/40">
                      {product.generic_name}
                      {product.strength ? ` · ${product.strength}` : ""}
                      {product.category ? ` · ${product.category}` : ""}
                    </p>
                    <p className="mt-1 text-[11px] text-emerald-400/80">{formatMoney(product.selling_price)}</p>
                  </div>

                  <label className="space-y-1">
                    <span className="text-[10px] uppercase tracking-[0.12em] text-white/35">Price</span>
                    <input
                      inputMode="decimal"
                      value={draft.selling_price}
                      onChange={(event) => updateDraft(product.id, { selling_price: event.target.value })}
                      placeholder="0"
                      className="h-10 w-full rounded-xl border border-white/10 bg-black/20 px-3 text-sm text-white outline-none focus:border-emerald-500/50"
                    />
                  </label>

                  <label className="space-y-1">
                    <span className="text-[10px] uppercase tracking-[0.12em] text-white/35">Stock</span>
                    <input
                      inputMode="numeric"
                      value={draft.stock_qty}
                      onChange={(event) => updateDraft(product.id, { stock_qty: event.target.value })}
                      placeholder="0"
                      className="h-10 w-full rounded-xl border border-white/10 bg-black/20 px-3 text-sm text-white outline-none focus:border-emerald-500/50"
                    />
                  </label>

                  <div className="grid grid-cols-2 gap-2 xl:grid-cols-1">
                    <button
                      onClick={() => updateDraft(product.id, { is_listed: !draft.is_listed })}
                      className={`h-10 rounded-xl border px-3 text-[12px] font-semibold ${
                        draft.is_listed
                          ? "border-emerald-500/30 bg-emerald-500/12 text-emerald-400"
                          : "border-white/10 bg-white/5 text-white/45"
                      }`}
                    >
                      {draft.is_listed ? "Listed in shop" : "Hidden from shop"}
                    </button>
                    <button
                      onClick={() => updateDraft(product.id, { requires_prescription: !draft.requires_prescription })}
                      className={`h-10 rounded-xl border px-3 text-[12px] font-semibold ${
                        draft.requires_prescription
                          ? "border-amber-500/30 bg-amber-500/12 text-amber-300"
                          : "border-white/10 bg-white/5 text-white/45"
                      }`}
                    >
                      {draft.requires_prescription ? "Rx required" : "OTC"}
                    </button>
                  </div>

                  <div className="flex gap-2 xl:flex-col">
                    <button
                      onClick={() => saveProduct(product)}
                      disabled={saving}
                      className="inline-flex h-10 flex-1 items-center justify-center gap-2 rounded-xl bg-emerald-500 px-3 text-[12px] font-bold text-black disabled:opacity-50"
                    >
                      <Save className="h-3.5 w-3.5" />
                      {saving ? "Saving…" : "Save"}
                    </button>
                    <button
                      onClick={() => {
                        updateDraft(product.id, { stock_qty: "0" });
                        void saveProduct(product, { stock_qty: "0" });
                      }}
                      disabled={saving}
                      className="h-10 flex-1 rounded-xl border border-red-500/25 bg-red-500/10 px-3 text-[12px] font-semibold text-red-300 disabled:opacity-50"
                    >
                      Mark out
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}

// ── Overview tab ──────────────────────────────────────────────────────────────
function OverviewTab({
  requests, orders, loading, onTab,
}: {
  requests: AdminRequest[];
  orders: AdminOrder[];
  loading: boolean;
  onTab: (t: string) => void;
}) {
  const pending = requests.filter((r) => r.status === "NEW" || r.status === "CHECKING_AVAILABILITY").length;
  const todayOrders = orders.filter((o) => {
    const d = new Date(o.created_at);
    const now = new Date();
    return d.getDate() === now.getDate() && d.getMonth() === now.getMonth();
  });
  const todayRevenue = todayOrders.reduce((s, o) => s + Number(o.total), 0);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-syne text-[20px] font-bold text-white">Overview</h1>
        <p className="text-[12px] text-white/40 mt-0.5">
          {new Date().toLocaleDateString("en-NG", { weekday: "long", day: "numeric", month: "long" })}
        </p>
      </div>
      <div className="grid grid-cols-2 gap-3">
        {[
          { label: "Pending requests", value: String(pending), note: "Need attention" },
          { label: "Today's orders", value: String(todayOrders.length), note: "New orders" },
          { label: "Today's revenue", value: `₦${todayRevenue.toLocaleString()}`, note: "From orders" },
          { label: "Total requests", value: String(requests.length), note: "All time" },
        ].map((s) => (
          <div key={s.label} className="rounded-2xl border border-white/8 bg-white/4 p-4">
            <p className="text-[22px] font-bold text-white">{s.value}</p>
            <p className="text-[11px] text-white/40 mt-0.5">{s.label}</p>
            <p className={`text-[10px] mt-1 ${s.note === "Need attention" && pending > 0 ? "text-amber-400" : "text-emerald-400"}`}>
              {s.note}
            </p>
          </div>
        ))}
      </div>
      <button
        onClick={() => onTab("catalog")}
        className="flex w-full items-center justify-between rounded-2xl border border-emerald-500/20 bg-emerald-500/10 p-4 text-left transition hover:border-emerald-500/40"
      >
        <div>
          <p className="font-syne text-[15px] font-bold text-white">Open Inventory</p>
          <p className="mt-1 text-[12px] text-white/50">
            Search all products, set price, update stock, and mark items out of stock.
          </p>
        </div>
        <ShoppingBag className="h-5 w-5 shrink-0 text-emerald-400" />
      </button>
      <div>
        <div className="flex items-center justify-between mb-3">
          <p className="text-[10px] font-semibold uppercase tracking-[0.14em] text-white/40">Recent Requests</p>
          <button onClick={() => onTab("requests")} className="text-[12px] text-emerald-400 hover:underline">View all</button>
        </div>
        <div className="rounded-2xl border border-white/8 bg-white/4 divide-y divide-white/6">
          {loading ? (
            <div className="px-4 py-6 text-center text-[13px] text-white/30">Loading…</div>
          ) : requests.slice(0, 5).length === 0 ? (
            <div className="px-4 py-6 text-center text-[13px] text-white/30">No requests yet</div>
          ) : (
            requests.slice(0, 5).map((r) => (
              <div key={r.id} className="flex items-center justify-between px-4 py-3">
                <div>
                  <p className="text-[13px] font-medium text-white">{r.product_name}</p>
                  <p className="text-[11px] text-white/40">
                    {r.customer_phone} · {new Date(r.created_at).toLocaleTimeString("en-NG", { hour: "2-digit", minute: "2-digit" })}
                  </p>
                </div>
                <span className={`inline-flex items-center rounded-full border px-2 py-0.5 text-[10px] font-semibold ${REQ_STATUS_COLOR[r.status] ?? "bg-white/8 text-white/50 border-white/12"}`}>
                  {REQ_STATUS_LABEL[r.status] ?? r.status}
                </span>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}

// ── Requests tab ──────────────────────────────────────────────────────────────
function RequestsTab({ requests, loading }: { requests: AdminRequest[]; loading: boolean }) {
  return (
    <div className="space-y-4">
      <h2 className="font-syne text-[18px] font-bold text-white">All Requests</h2>
      <div className="rounded-2xl border border-white/8 bg-white/4 divide-y divide-white/6">
        {loading ? (
          <div className="px-4 py-8 text-center text-[13px] text-white/30">Loading…</div>
        ) : requests.length === 0 ? (
          <div className="px-4 py-8 text-center text-[13px] text-white/30">No requests</div>
        ) : (
          requests.map((r) => (
            <div key={r.id} className="flex items-center justify-between px-4 py-4">
              <div className="min-w-0 flex-1 mr-3">
                <p className="text-[14px] font-semibold text-white truncate">{r.product_name}</p>
                <p className="text-[11px] text-white/40 mt-0.5">
                  {r.customer_phone} · {new Date(r.created_at).toLocaleDateString("en-NG")}
                </p>
              </div>
              <span className={`shrink-0 inline-flex items-center rounded-full border px-2.5 py-0.5 text-[10px] font-semibold ${REQ_STATUS_COLOR[r.status] ?? "bg-white/8 text-white/50 border-white/12"}`}>
                {REQ_STATUS_LABEL[r.status] ?? r.status}
              </span>
            </div>
          ))
        )}
      </div>
    </div>
  );
}

// ── Orders tab ────────────────────────────────────────────────────────────────
function OrdersTab({ orders, loading }: { orders: AdminOrder[]; loading: boolean }) {
  const ORDER_STATUS_COLOR: Record<string, string> = {
    DELIVERED: "bg-emerald-500/15 text-emerald-400 border-emerald-500/25",
    PROCESSING: "bg-emerald-500/15 text-emerald-400 border-emerald-500/25",
    AWAITING_PAYMENT: "bg-amber-500/15 text-amber-400 border-amber-500/25",
    CANCELLED: "bg-red-500/15 text-red-400 border-red-500/25",
    NEW: "bg-white/8 text-white/50 border-white/12",
  };
  return (
    <div className="space-y-4">
      <h2 className="font-syne text-[18px] font-bold text-white">All Orders</h2>
      <div className="rounded-2xl border border-white/8 bg-white/4 divide-y divide-white/6">
        {loading ? (
          <div className="px-4 py-8 text-center text-[13px] text-white/30">Loading…</div>
        ) : orders.length === 0 ? (
          <div className="px-4 py-8 text-center text-[13px] text-white/30">No orders yet</div>
        ) : (
          orders.map((o) => (
            <div key={o.id} className="flex items-center justify-between px-4 py-4">
              <div>
                <p className="text-[14px] font-semibold text-white">{o.code}</p>
                <p className="text-[11px] text-white/40 mt-0.5">
                  ₦{Number(o.total).toLocaleString()} · {new Date(o.created_at).toLocaleDateString("en-NG")}
                </p>
              </div>
              <span className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-[10px] font-semibold ${ORDER_STATUS_COLOR[o.status] ?? "bg-white/8 text-white/50 border-white/12"}`}>
                {o.status}
              </span>
            </div>
          ))
        )}
      </div>
    </div>
  );
}

// ── Root component ────────────────────────────────────────────────────────────
export default function AdminPage() {
  const [admin, setAdmin] = useState<AdminMe | null>(null);
  const [checked, setChecked] = useState(false);

  useEffect(() => {
    const token = getAdminToken();
    if (token) {
      adminFetch<AdminMe>("/admin/me")
        .then((me) => setAdmin(me))
        .catch(() => clearAdminToken())
        .finally(() => setChecked(true));
    } else {
      setChecked(true);
    }
  }, []);

  if (!checked) return null;
  if (admin) return <Dashboard admin={admin} />;
  return <TelegramOtpGate onLogin={(me) => setAdmin(me)} />;
}
```

- [ ] **Step 2: Run TypeScript check**

```bash
cd web && npx tsc --noEmit
```
Expected: no errors

- [ ] **Step 3: Commit**

```bash
git add web/app/admin/page.tsx web/lib/admin-auth.ts
git commit -m "feat: replace password LoginGate with Telegram OTP auth on web admin panel"
```

---

## Task 8: End-to-End Verification

- [ ] **Step 1: Run all backend tests**

```
pytest tests/ -v
```
Expected: all tests PASS

- [ ] **Step 2: Apply migration to Railway (production)**

```bash
railway run alembic upgrade head
```
Expected: `Running upgrade <prev> -> <new>, add web admin auth tables`

- [ ] **Step 3: Remove `ADMIN_WEB_PASSWORD` from Railway env vars**

In Railway dashboard, delete the `ADMIN_WEB_PASSWORD` environment variable from the service. It is no longer used.

- [ ] **Step 4: Deploy**

```bash
git push origin main
```
Wait for Railway deployment to complete.

- [ ] **Step 5: Smoke test**

1. Open the deployed `/admin` — confirm the password form is gone, you see "Enter your Telegram ID"
2. Send `/myid` to the Peaceway bot — note the number
3. Enter your Telegram ID on the web, click "Send Code via Telegram"
4. Check your Telegram — confirm you received a 6-digit code
5. Paste the code, click "Verify & Sign In"
6. Confirm you see the dashboard with only the tabs matching your role
7. Click "Sign out" — confirm you're returned to the login screen

- [ ] **Step 6: Final commit**

```bash
git add .
git commit -m "chore: web admin Telegram OTP auth — complete"
```
