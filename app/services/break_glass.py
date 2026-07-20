"""Break-glass: time-boxed emergency clinical read for the System Owner.

Writes a break_glass_access row (which the clinical RLS policies honour until it
expires) AND an audit_log row recording who, why, and for how long. The grant is
keyed on admin_users.id, so the System Owner must be a registered admin (not only an
env-bootstrap owner) for break-glass to function.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AuditLog, BreakGlassAccess

DEFAULT_MINUTES = 15


async def grant_break_glass(
    session: AsyncSession,
    *,
    user_id: UUID,
    reason: str,
    resource: str = "clinical",
    minutes: int = DEFAULT_MINUTES,
) -> BreakGlassAccess:
    """Grant `user_id` break-glass read of `resource` for `minutes`, audited."""
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=minutes)
    row = BreakGlassAccess(user_id=user_id, resource=resource, reason=reason, expires_at=expires_at)
    session.add(row)
    session.add(
        AuditLog(
            actor_id=user_id,
            action="break_glass_granted",
            entity=resource,
            reason=reason,
            detail={"expires_at": expires_at.isoformat(), "minutes": minutes},
        )
    )
    await session.flush()
    return row
