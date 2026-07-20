"""Prescription-verification write-path — the single place that records a
pharmacist's decision on an order's prescription lines.

This is the row Gate 1 (`trg_pom_verification_before_dispatch`) checks before it
lets a prescription order dispatch. ANY approval path (bot today, web later) MUST
call `record_verification` so the order carries a current verification; otherwise
dispatch is rejected at the database level.

The verifier must be a real pharmacist admin id (`admin_users.id`) — the DB trigger
independently requires that id to hold a lead_pharmacist/pharmacist_admin role.
"""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import PrescriptionVerification

# decision values (mirrors the SUPERSEDED value the order_items trigger writes)
APPROVED = "APPROVED"
REJECTED = "REJECTED"
SUPERSEDED = "SUPERSEDED"


async def record_verification(
    session: AsyncSession,
    *,
    order_id: UUID,
    pharmacist_admin_id: UUID,
    decision: str,
    note: str | None = None,
) -> PrescriptionVerification:
    """Append a verification row for an order. Latest row wins in the Gate-1 check.

    `decision` is APPROVED or REJECTED. `verified_at` is stamped so an APPROVED row
    satisfies the trigger (which requires a non-null verified_at + pharmacist id).
    """
    row = PrescriptionVerification(
        order_id=order_id,
        pharmacist_user_id=pharmacist_admin_id,
        decision=decision,
        verified_at=datetime.now(timezone.utc),
        note=note,
    )
    session.add(row)
    await session.flush()
    return row
