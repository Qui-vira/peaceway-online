"""Unit test for the break-glass service (SQLite)."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select

from app.models import AdminUser, AuditLog, BreakGlassAccess
from app.models.admin import AdminStatus
from app.services.break_glass import grant_break_glass


async def test_grant_break_glass_writes_grant_and_audit(db_session):
    admin = AdminUser(telegram_id=7, full_name="Owner", is_active=True, status=AdminStatus.ACTIVE)
    db_session.add(admin)
    await db_session.flush()

    row = await grant_break_glass(db_session, user_id=admin.id, reason="patient emergency")

    assert row.resource == "clinical"
    assert row.expires_at > datetime.now(timezone.utc)  # future expiry

    audit = (
        await db_session.execute(select(AuditLog).where(AuditLog.action == "break_glass_granted"))
    ).scalar_one()
    assert audit.actor_id == admin.id
    assert audit.reason == "patient emergency"
    assert audit.entity == "clinical"

    bg = (
        await db_session.execute(select(BreakGlassAccess).where(BreakGlassAccess.user_id == admin.id))
    ).scalar_one()
    assert bg.reason == "patient emergency"
