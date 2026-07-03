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
